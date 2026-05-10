from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class QdrantSearchResult:
    chunk_id: str
    score: float
    payload: dict[str, object]


class QdrantVectorStore:
    def __init__(self, url: str, api_key: str | None = None) -> None:
        self._url = url
        self._api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(url=self._url, api_key=self._api_key)
            return self._client
        except ImportError:
            logger.warning("qdrant-client not installed. Install with: pip install qdrant-client")
            return None
        except Exception:
            logger.exception("Failed to connect to Qdrant at %s", self._url)
            return None

    def is_available(self) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            client.get_collections()
            return True
        except Exception:
            return False

    def _collection_name(self, scenic_id: str) -> str:
        return f"aether_{scenic_id.replace('-', '_')}"

    def ensure_collection(self, scenic_id: str, dimensions: int = 1024) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            from qdrant_client.models import Distance, VectorParams

            name = self._collection_name(scenic_id)
            existing = client.get_collections().collections
            if any(c.name == name for c in existing):
                return True
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE),
            )
            logger.info("Created Qdrant collection: %s (dim=%d)", name, dimensions)
            return True
        except Exception:
            logger.exception("Failed to ensure Qdrant collection for %s", scenic_id)
            return False

    def collection_point_count(self, scenic_id: str) -> int | None:
        """Return the number of points in the collection, or None if unknown."""
        client = self._get_client()
        if client is None:
            return None
        try:
            name = self._collection_name(scenic_id)
            existing = client.get_collections().collections
            if not any(c.name == name for c in existing):
                return 0
            info = client.get_collection(collection_name=name)
            count = getattr(info, "points_count", None)
            return int(count) if count is not None else None
        except Exception:
            return None

    def upsert_chunks(
        self,
        scenic_id: str,
        chunk_ids: list[str],
        embeddings: list[list[float]],
        payloads: list[dict[str, object]],
    ) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            from qdrant_client.models import PointStruct

            name = self._collection_name(scenic_id)
            points = [
                PointStruct(id=i, vector=embedding, payload=payload)
                for i, (embedding, payload) in enumerate(
                    zip(embeddings, payloads, strict=True)
                )
            ]
            client.upsert(collection_name=name, points=points)
            logger.info("Upserted %d chunks to Qdrant collection %s", len(points), name)
            return True
        except Exception:
            logger.exception("Failed to upsert chunks to Qdrant")
            return False

    def search(
        self,
        scenic_id: str,
        query_embedding: list[float],
        top_k: int = 20,
        score_threshold: float = 0.0,
    ) -> list[QdrantSearchResult]:
        client = self._get_client()
        if client is None:
            return []
        try:
            name = self._collection_name(scenic_id)
            results = client.query_points(
                collection_name=name,
                query=query_embedding,
                limit=top_k,
                score_threshold=score_threshold,
                with_payload=True,
            )
            return [
                QdrantSearchResult(
                    chunk_id=str(point.id),
                    score=point.score,
                    payload=point.payload or {},
                )
                for point in results.points
            ]
        except Exception:
            logger.exception("Qdrant search failed for collection %s", scenic_id)
            return []

    def delete_by_document(self, scenic_id: str, document_id: str) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            name = self._collection_name(scenic_id)
            client.delete(
                collection_name=name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id", match=MatchValue(value=document_id)
                        )
                    ]
                ),
            )
            return True
        except Exception:
            logger.exception("Failed to delete document %s from Qdrant", document_id)
            return False

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
