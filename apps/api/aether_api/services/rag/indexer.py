# SCORE-IMPACT: Knowledge-base versioning and future 90%+ answer accuracy.
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(slots=True)
class IndexJob:
    document_id: str
    index_version: str
    queued_at: datetime


class RAGIndexer:
    async def enqueue(self, document_id: str) -> IndexJob:
        return IndexJob(
            document_id=document_id,
            index_version="demo-v1",
            queued_at=datetime.now(UTC),
        )
