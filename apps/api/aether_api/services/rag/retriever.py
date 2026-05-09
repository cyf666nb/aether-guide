# SCORE-IMPACT: Citation-ready retrieval interface for RAG replacement.
from dataclasses import dataclass


@dataclass(slots=True)
class RetrievedChunk:
    source_id: str
    text: str
    score: float


class RAGRetriever:
    async def retrieve(self, query: str, scenic_id: str) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                source_id="seed:intro",
                text=f"Demo retrieval context for {scenic_id}: {query}",
                score=0.99,
            )
        ]

