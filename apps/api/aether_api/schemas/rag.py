# SCORE-IMPACT: Typed knowledge chunks shared by indexer, retriever, and storage.
from pydantic import Field

from aether_api.schemas.common import BaseDTO


class KnowledgeChunkDTO(BaseDTO):
    id: str
    document_id: str | None = None
    scenic_id: str
    source_id: str
    text: str = Field(min_length=1)
    ord: int = Field(ge=0)
    embedding: list[float] | None = None
    sparse_vector: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
