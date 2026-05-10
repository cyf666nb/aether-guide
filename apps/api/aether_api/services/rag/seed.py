# SCORE-IMPACT: Demo knowledge seeding with deterministic RAG chunks.
from __future__ import annotations

from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from aether_api.schemas.admin import DocumentDTO, DocumentStatus
from aether_api.schemas.rag import KnowledgeChunkDTO
from aether_api.services.rag.text import chunk_text, hashed_embedding, sparse_vector


def seed_document_to_dto(
    item: dict[str, object],
    scenic_id: str,
    *,
    indexed_at: datetime,
) -> DocumentDTO:
    document_id = _string(item, "id")
    return DocumentDTO(
        id=document_id,
        scenic_id=scenic_id,
        title=_string(item, "title"),
        source_uri=_string(item, "source_uri", f"seed://sanfangqixiang/{document_id}"),
        version=_string(item, "version", "seed-v1"),
        status=DocumentStatus.ready,
        indexed_at=indexed_at,
    )


def build_seed_chunks(document: DocumentDTO, text: str) -> list[KnowledgeChunkDTO]:
    chunks = chunk_text(text, max_chars=260, overlap=40)
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
                "kind": "seed_knowledge",
            },
        )
        for index, chunk in enumerate(chunks)
    ]


def _string(item: dict[str, object], key: str, default: str | None = None) -> str:
    value = item.get(key, default)
    if not isinstance(value, str) or not value.strip():
        if default is not None:
            return default
        raise ValueError(f"Seed knowledge document is missing string field: {key}")
    return value
