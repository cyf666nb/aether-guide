# SCORE-IMPACT: Citation-ready retrieval interface for grounded guide answers.
from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from aether_api.repository import Repository
from aether_api.schemas.landmarks import LandmarkDTO
from aether_api.schemas.rag import KnowledgeChunkDTO
from aether_api.services.rag.text import (
    cosine,
    hashed_embedding,
    lexical_score,
    parse_sparse_vector,
    sparse_vector,
    tokenize,
)

if TYPE_CHECKING:
    from aether_api.services.rag.embedding import BGEEmbedding
    from aether_api.services.rag.vectorstore import QdrantVectorStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Candidate-chunk cache.
#
# The hot path previously ran two full-table scans per user message just to
# look up a handful of source ids that Qdrant had already matched. We cache
# the (source_id -> chunk) map per scenic_id with a short TTL, and invalidate
# explicitly whenever documents or landmarks are rewritten.
# ---------------------------------------------------------------------------

_CACHE_TTL_SECONDS = 60.0
_CACHE_MAX_SCENIC_AREAS = 128
_candidate_cache: dict[str, tuple[float, dict[str, KnowledgeChunkDTO]]] = {}
_candidate_cache_lock = asyncio.Lock()


def invalidate_candidate_cache(scenic_id: str | None = None) -> None:
    """Drop cached chunks. Call from write paths (document reindex, etc.).

    Passing ``None`` clears every scenic area.
    """
    if scenic_id is None:
        _candidate_cache.clear()
        return
    _candidate_cache.pop(scenic_id, None)


def _prune_candidate_cache(now: float) -> None:
    expired = [
        scenic_id
        for scenic_id, (created_at, _) in _candidate_cache.items()
        if now - created_at >= _CACHE_TTL_SECONDS
    ]
    for scenic_id in expired:
        _candidate_cache.pop(scenic_id, None)
    overflow = len(_candidate_cache) - _CACHE_MAX_SCENIC_AREAS
    if overflow <= 0:
        return
    oldest = sorted(_candidate_cache.items(), key=lambda item: item[1][0])
    for scenic_id, _ in oldest[:overflow]:
        _candidate_cache.pop(scenic_id, None)


async def _get_chunk_map(
    repository: Repository, scenic_id: str
) -> dict[str, KnowledgeChunkDTO]:
    now = time.monotonic()
    cached = _candidate_cache.get(scenic_id)
    if cached is not None and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]
    async with _candidate_cache_lock:
        cached = _candidate_cache.get(scenic_id)
        if cached is not None and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1]
        _prune_candidate_cache(time.monotonic())
        chunks = await repository.list_knowledge_chunks(scenic_id)
        landmarks = await repository.list_landmarks(scenic_id)
        landmark_chunks = [
            _landmark_to_chunk(index, landmark)
            for index, landmark in enumerate(landmarks)
        ]
        chunk_map: dict[str, KnowledgeChunkDTO] = {}
        for chunk in chunks:
            chunk_map[chunk.source_id] = chunk
        for chunk in landmark_chunks:
            chunk_map.setdefault(chunk.source_id, chunk)
        _candidate_cache[scenic_id] = (time.monotonic(), chunk_map)
        return chunk_map


_QUERY_STOP_TOKENS = {
    "从",
    "先",
    "来",
    "哪",
    "里",
    "哪儿",
    "哪里",
    "开",
    "始",
    "开始",
    "逛",
    "附",
    "近",
    "附近",
    "有",
    "什",
    "么",
    "什么",
    "你",
    "我",
    "他",
    "她",
    "它",
    "是",
    "的",
    "了",
    "吗",
    "呢",
    "谁",
    "啥",
    "多",
    "少",
    "多少",
    "你是",
    "是谁",
    "几",
    "what",
    "who",
    "are",
    "you",
    "is",
    "the",
    "a",
    "an",
}

_FOOD_QUERY_TOKENS = {
    "饭",
    "店",
    "饭店",
    "餐",
    "馆",
    "餐馆",
    "餐厅",
    "吃饭",
    "小吃",
    "美食",
    "吃",
    "food",
    "restaurant",
    "restaurants",
    "meal",
}

_FOOD_EXPANSION_TOKENS = {
    "南后街",
    "小吃",
    "老字号",
    "餐饮",
    "鱼丸",
    "肉燕",
    "芋泥",
    "鼎边糊",
    "food",
}

_FOOD_BOOST_TERMS = {
    "小吃",
    "餐饮",
    "老字号",
    "鱼丸",
    "肉燕",
    "芋泥",
    "鼎边糊",
    "食铺",
    "美食",
}

_ROUTE_QUERY_TERMS = {
    "第一次",
    "首次",
    "初次",
    "新手",
    "开始",
    "从哪里",
    "路线",
    "入口",
    "怎么逛",
    "先去哪",
    "先从",
}

_ROUTE_BOOST_TERMS = {
    "中轴",
    "入口",
    "方位感",
    "西三坊",
    "东七巷",
}

_SAFETY_QUERY_TERMS = {
    "雨天",
    "下雨",
    "雨",
    "湿滑",
    "安全",
    "老人",
    "台阶",
    "拥挤",
}

_SAFETY_BOOST_TERMS = {
    "雨天",
    "湿滑",
    "石板路",
    "台阶",
    "安全",
    "拥挤",
    "随身物品",
    "现场公告",
}

_FAMILY_QUERY_TERMS = {
    "带孩子",
    "孩子",
    "小孩",
    "亲子",
    "儿童",
    "带娃",
    "family",
    "kids",
}

_FAMILY_BOOST_TERMS = {
    "亲子",
    "孩子",
    "小孩",
    "观察任务",
    "手作",
    "非遗",
    "冰心",
}


@dataclass(slots=True)
class RetrievedChunk:
    source_id: str
    text: str
    score: float
    chunk_id: str | None = None
    document_id: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class RAGRetriever:
    def __init__(
        self,
        repository: Repository,
        *,
        default_top_k: int = 4,
        min_score: float = 0.05,
        vectorstore: QdrantVectorStore | None = None,
        embedding: BGEEmbedding | None = None,
    ) -> None:
        self._repository = repository
        self._default_top_k = default_top_k
        self._min_score = min_score
        self._vectorstore = vectorstore
        self._embedding = embedding

    async def retrieve(
        self,
        query: str,
        scenic_id: str,
        *,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        limit = top_k or self._default_top_k
        query_counts = _meaningful_query_counts(query)
        if not query_counts:
            return []
        food_intent = _has_food_intent(query_counts)
        route_intent = _has_route_intent(query)
        safety_intent = _has_safety_intent(query)
        family_intent = _has_family_intent(query)

        # Encode once and reuse: Qdrant search + dense cosine scoring share
        # the same query vector.
        query_embedding = await self._encode_query_async(query)
        candidates = await self._get_candidates(
            query, scenic_id, limit, query_embedding=query_embedding
        )
        scored: list[RetrievedChunk] = []
        for candidate in candidates:
            counts = parse_sparse_vector(candidate.sparse_vector, candidate.text)
            lexical = lexical_score(
                query,
                candidate.text,
                counts,
                query_counts=query_counts,
            )
            if lexical == 0.0:
                continue
            dense = cosine(query_embedding, candidate.embedding)
            score = round((lexical * 0.85) + (max(dense, 0.0) * 0.15), 6)
            score = _apply_intent_boost(
                score,
                candidate,
                food_intent=food_intent,
                route_intent=route_intent,
                safety_intent=safety_intent,
                family_intent=family_intent,
            )
            if score < self._min_score:
                continue
            scored.append(
                RetrievedChunk(
                    source_id=candidate.source_id,
                    text=candidate.text,
                    score=score,
                    chunk_id=candidate.id,
                    document_id=candidate.document_id,
                    metadata=candidate.metadata,
                )
            )

        scored.sort(key=lambda chunk: (-chunk.score, chunk.source_id))
        return _dedupe_by_source(scored)[:limit]

    def _encode_query(self, query: str) -> list[float]:
        if self._embedding is not None:
            return self._embedding.encode_query(query)
        return hashed_embedding(query)

    async def _encode_query_async(self, query: str) -> list[float]:
        """Run the heavy numpy-backed encode off the event loop."""
        if self._embedding is not None and self._embedding.is_real_model:
            return await asyncio.to_thread(self._embedding.encode_query, query)
        return self._encode_query(query)

    async def _get_candidates(
        self,
        query: str,
        scenic_id: str,
        limit: int,
        *,
        query_embedding: list[float] | None = None,
    ) -> list[KnowledgeChunkDTO]:
        if self._vectorstore is not None and self._embedding is not None:
            return await self._qdrant_candidates(
                query, scenic_id, limit, query_embedding=query_embedding
            )
        return await self._candidate_chunks(scenic_id)

    async def _qdrant_candidates(
        self,
        query: str,
        scenic_id: str,
        limit: int,
        *,
        query_embedding: list[float] | None = None,
    ) -> list[KnowledgeChunkDTO]:
        query_vec = query_embedding or await self._encode_query_async(query)
        vectorstore = self._vectorstore
        if vectorstore is None:
            return await self._candidate_chunks(scenic_id)
        # qdrant-client uses synchronous HTTP; run it off the event loop so
        # it doesn't block other requests during the search round-trip.
        results = await asyncio.to_thread(
            vectorstore.search,
            scenic_id,
            query_vec,
            max(limit * 5, 20),
        )
        if not results:
            logger.info("Qdrant returned no results, falling back to full scan")
            return await self._candidate_chunks(scenic_id)

        # Qdrant payloads already carry source_id + text; a short-TTL cache
        # keeps the hot path off the DB. Previously this fetched every chunk
        # and every landmark on every user message, and even re-fetched
        # landmarks inside an N-landmark loop.
        chunk_map = await _get_chunk_map(self._repository, scenic_id)

        candidates: list[KnowledgeChunkDTO] = []
        seen: set[str] = set()
        for result in results:
            source_id = result.payload.get("source_id")
            if not isinstance(source_id, str) or source_id in seen:
                continue
            seen.add(source_id)
            chunk = chunk_map.get(source_id)
            if chunk is not None:
                candidates.append(chunk)
                continue
            # Fallback: synthesize a KnowledgeChunkDTO from the Qdrant payload
            # so we can still score the hit even if the repo lookup missed.
            text = result.payload.get("text")
            if not isinstance(text, str) or not text:
                continue
            metadata = {
                key: value
                for key, value in result.payload.items()
                if key not in {"source_id", "text", "scenic_id", "document_id"}
            }
            document_id = result.payload.get("document_id")
            candidates.append(
                KnowledgeChunkDTO(
                    id=result.chunk_id,
                    document_id=document_id
                    if isinstance(document_id, str) and document_id
                    else None,
                    scenic_id=scenic_id,
                    source_id=source_id,
                    text=text,
                    ord=0,
                    embedding=None,
                    sparse_vector=None,
                    metadata=metadata,
                )
            )
        if not candidates:
            logger.info("No matching chunks found in repository, falling back to full scan")
            return await self._candidate_chunks(scenic_id)
        return candidates

    async def _candidate_chunks(self, scenic_id: str) -> list[KnowledgeChunkDTO]:
        chunks = await self._repository.list_knowledge_chunks(scenic_id)
        chunks.extend(await self._landmark_chunks(scenic_id))
        return chunks

    async def _landmark_chunks(self, scenic_id: str) -> list[KnowledgeChunkDTO]:
        landmarks = await self._repository.list_landmarks(scenic_id)
        return [_landmark_to_chunk(index, landmark) for index, landmark in enumerate(landmarks)]


def _landmark_to_chunk(index: int, landmark: LandmarkDTO) -> KnowledgeChunkDTO:
    text = (
        f"{landmark.name}\n"
        f"{landmark.summary}\n"
        f"Tags: {', '.join(landmark.tags)}\n"
        f"Average visit: {landmark.avg_duration_min} minutes."
    )
    return KnowledgeChunkDTO(
        id=f"landmark:{landmark.id}",
        document_id=None,
        scenic_id=landmark.scenic_id,
        source_id=f"landmark:{landmark.id}",
        text=text,
        ord=index,
        embedding=hashed_embedding(text),
        sparse_vector=sparse_vector(text),
        metadata={
            "kind": "landmark",
            "landmark_id": landmark.id,
            "name": landmark.name,
            "tags": landmark.tags,
        },
    )


def _dedupe_by_source(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    seen: set[str] = set()
    deduped: list[RetrievedChunk] = []
    for chunk in chunks:
        if chunk.source_id in seen:
            continue
        seen.add(chunk.source_id)
        deduped.append(chunk)
    return deduped


def _meaningful_query_counts(query: str) -> Counter[str]:
    tokens = [
        token
        for token in tokenize(query)
        if _is_meaningful_query_token(token)
    ]
    if _has_food_intent(Counter(tokens)):
        tokens.extend(_FOOD_EXPANSION_TOKENS)
    return Counter(tokens)


def _is_meaningful_query_token(token: str) -> bool:
    if token.isdigit() or token in _QUERY_STOP_TOKENS:
        return False
    return not all(char in _QUERY_STOP_TOKENS for char in token)


def _has_food_intent(query_counts: Counter[str]) -> bool:
    return any(token in _FOOD_QUERY_TOKENS for token in query_counts)


def _apply_intent_boost(
    score: float,
    candidate: KnowledgeChunkDTO,
    *,
    food_intent: bool,
    route_intent: bool,
    safety_intent: bool,
    family_intent: bool,
) -> float:
    boosted = score
    tags = candidate.metadata.get("tags", [])

    if food_intent:
        if isinstance(tags, list) and "food" in tags:
            boosted += 0.35
        if any(term in candidate.text for term in _FOOD_BOOST_TERMS):
            boosted += 0.2
        if candidate.source_id == "landmark:nanhou-street":
            boosted += 0.25

    if route_intent:
        if candidate.source_id == "landmark:nanhou-street":
            boosted += 0.3
        if any(term in candidate.text for term in _ROUTE_BOOST_TERMS):
            boosted += 0.12

    if safety_intent:
        if candidate.source_id.startswith("doc:sfqx-safety-accessibility"):
            boosted += 0.45
        if any(term in candidate.text for term in _SAFETY_BOOST_TERMS):
            boosted += 0.18

    if family_intent:
        if candidate.source_id.startswith("doc:sfqx-family-elder-photo"):
            boosted += 0.45
        if candidate.source_id.startswith("doc:sfqx-intangible-heritage"):
            boosted += 0.2
        if any(term in candidate.text for term in _FAMILY_BOOST_TERMS):
            boosted += 0.16
    return round(boosted, 6)


def _has_route_intent(query: str) -> bool:
    return any(term in query for term in _ROUTE_QUERY_TERMS)


def _has_safety_intent(query: str) -> bool:
    return any(term in query for term in _SAFETY_QUERY_TERMS)


def _has_family_intent(query: str) -> bool:
    return any(term in query for term in _FAMILY_QUERY_TERMS)
