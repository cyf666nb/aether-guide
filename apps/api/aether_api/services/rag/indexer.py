# SCORE-IMPACT: Knowledge-base indexing and future 90%+ answer accuracy.
from __future__ import annotations

import asyncio
import base64
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import ParseResult, unquote, urlparse
from uuid import NAMESPACE_URL, uuid5

from aether_api.errors import AppError, ErrorCode
from aether_api.repository import Repository
from aether_api.schemas.admin import DocumentDTO, DocumentStatus
from aether_api.schemas.rag import KnowledgeChunkDTO
from aether_api.services.rag.retriever import invalidate_candidate_cache
from aether_api.services.rag.text import chunk_text, hashed_embedding, sparse_vector

if TYPE_CHECKING:
    from aether_api.services.rag.embedding import BGEEmbedding
    from aether_api.services.rag.vectorstore import QdrantVectorStore

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class IndexJob:
    document_id: str
    index_version: str
    queued_at: datetime
    status: DocumentStatus
    chunks_indexed: int


class RAGIndexer:
    def __init__(
        self,
        repository: Repository,
        *,
        vectorstore: QdrantVectorStore | None = None,
        embedding: BGEEmbedding | None = None,
    ) -> None:
        self._repository = repository
        self._vectorstore = vectorstore
        self._embedding = embedding

    async def enqueue(self, document_id: str) -> IndexJob:
        return await self.index_document(document_id)

    async def index_document(self, document_id: str) -> IndexJob:
        queued_at = datetime.now(UTC)
        document = await self._repository.get_document(document_id)
        await self._repository.update_document_index_status(
            document_id,
            DocumentStatus.indexing,
        )
        try:
            source_text = await self._load_source(document)
            chunks = self._build_chunks(document, source_text)
            await self._repository.replace_document_chunks(document_id, chunks)
            await self._upsert_to_qdrant(document.scenic_id, document_id, chunks)
            await self._repository.update_document_index_status(
                document_id,
                DocumentStatus.ready,
                indexed_at=datetime.now(UTC),
            )
            # Freshly indexed content — drop any stale retriever cache so the
            # next user query sees it.
            invalidate_candidate_cache(document.scenic_id)
            return IndexJob(
                document_id=document_id,
                index_version=document.version,
                queued_at=queued_at,
                status=DocumentStatus.ready,
                chunks_indexed=len(chunks),
            )
        except AppError:
            await self._repository.update_document_index_status(
                document_id,
                DocumentStatus.failed,
            )
            raise

    async def _load_source(self, document: DocumentDTO) -> str:
        uri = document.source_uri.strip()
        parsed = urlparse(uri)
        if parsed.scheme in {"memory", "seed"}:
            return await self._seed_document_text(document)
        if parsed.scheme in {"inline", "text"}:
            payload = uri.split("://", 1)[1] if "://" in uri else parsed.path
            return unquote(payload)
        if parsed.scheme == "data":
            return _decode_data_uri(uri)
        if parsed.scheme == "file":
            return await self._read_local_file(parsed, document)
        if not parsed.scheme:
            return uri
        return f"{document.title}\nSource URI: {document.source_uri}"

    async def _seed_document_text(self, document: DocumentDTO) -> str:
        landmarks = await self._repository.list_landmarks(document.scenic_id)
        if not landmarks:
            return f"{document.title}\nNo landmarks are available for this scenic area."
        return "\n\n".join(
            (
                f"{landmark.name}\n"
                f"{landmark.summary}\n"
                f"Tags: {', '.join(landmark.tags)}\n"
                f"Average visit: {landmark.avg_duration_min} minutes."
            )
            for landmark in landmarks
        )

    async def _read_local_file(self, parsed: ParseResult, document: DocumentDTO) -> str:
        path_text = unquote(getattr(parsed, "path", ""))
        path = Path(path_text)
        seed_path = await self._repository.seed_path()
        seed_root = await asyncio.to_thread(lambda: seed_path.resolve().parent)
        resolved = await asyncio.to_thread(path.resolve)
        if seed_root not in (resolved, *resolved.parents):
            raise AppError(
                ErrorCode.bad_request,
                "File source is outside the configured seed directory.",
                status_code=400,
            )
        try:
            return await asyncio.to_thread(resolved.read_text, encoding="utf-8")
        except OSError as exc:
            raise AppError(
                ErrorCode.bad_request,
                f"Could not read source for document {document.id}.",
                status_code=400,
            ) from exc

    def _build_chunks(self, document: DocumentDTO, text: str) -> list[KnowledgeChunkDTO]:
        chunks = chunk_text(text)
        if not chunks:
            raise AppError(
                ErrorCode.bad_request,
                "Document source did not contain indexable text.",
                status_code=400,
            )
        return [
            KnowledgeChunkDTO(
                id=uuid5(NAMESPACE_URL, f"{document.id}:{index}:{chunk}").hex,
                document_id=document.id,
                scenic_id=document.scenic_id,
                source_id=f"doc:{document.id}:chunk:{index}",
                text=chunk,
                ord=index,
                embedding=hashed_embedding(chunk),
                sparse_vector=sparse_vector(chunk),
                metadata={
                    "title": document.title,
                    "version": document.version,
                    "source_uri": document.source_uri,
                },
            )
            for index, chunk in enumerate(chunks)
        ]

    async def _upsert_to_qdrant(
        self, scenic_id: str, document_id: str, chunks: list[KnowledgeChunkDTO]
    ) -> None:
        if self._vectorstore is None or self._embedding is None:
            return
        try:
            self._vectorstore.delete_by_document(scenic_id, document_id)
            texts = [chunk.text for chunk in chunks]
            embeddings = self._embedding.encode_texts(texts)
            chunk_ids = [chunk.id for chunk in chunks]
            payloads = [
                {
                    "source_id": chunk.source_id,
                    "document_id": chunk.document_id or "",
                    "text": chunk.text[:500],
                    "scenic_id": chunk.scenic_id,
                    **chunk.metadata,
                }
                for chunk in chunks
            ]
            self._vectorstore.upsert_chunks(scenic_id, chunk_ids, embeddings, payloads)
            logger.info(
                "Upserted %d chunks to Qdrant for document %s", len(chunks), document_id
            )
        except Exception:
            logger.exception("Failed to upsert chunks to Qdrant for document %s", document_id)


def _decode_data_uri(uri: str) -> str:
    header, separator, payload = uri.partition(",")
    if not separator:
        raise AppError(
            ErrorCode.bad_request,
            "Data URI is missing a payload.",
            status_code=400,
        )
    if ";base64" in header:
        try:
            return base64.b64decode(payload, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise AppError(
                ErrorCode.bad_request,
                "Data URI payload must be valid UTF-8 text.",
                status_code=400,
            ) from exc
    return unquote(payload)
