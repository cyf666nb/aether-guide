# SCORE-IMPACT: Closed-loop evaluation and NPS instrumentation.
from pydantic import Field

from aether_api.schemas.common import BaseDTO, IdempotentRequest


class FeedbackRequest(IdempotentRequest):
    session_id: str
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackDTO(BaseDTO):
    id: str
    session_id: str
    accepted: bool

