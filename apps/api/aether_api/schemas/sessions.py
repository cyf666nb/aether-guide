# SCORE-IMPACT: Demo completeness and multimodal session foundation.
from datetime import datetime
from enum import StrEnum

from pydantic import Field

from aether_api.schemas.common import BaseDTO, GeoPoint, IdempotentRequest


class SessionStatus(StrEnum):
    active = "active"
    ended = "ended"


class CreateSessionRequest(IdempotentRequest):
    scenic_id: str = Field(min_length=1)
    user_id: str | None = None
    persona_id: str | None = None
    locale: str = "zh-CN"


class SessionDTO(BaseDTO):
    id: str
    user_id: str | None
    scenic_id: str
    persona_id: str
    status: SessionStatus
    started_at: datetime


class StreamMessage(BaseDTO):
    type: str = Field(default="user_text")
    text: str = Field(min_length=1, max_length=4000)
    locale: str = "zh-CN"


class AssistantMessage(BaseDTO):
    type: str = "assistant_message"
    session_id: str
    content: str
    citations: list[str]
    cost_usd: float
    cache_hit: bool


class PhotoSceneRequest(IdempotentRequest):
    image_base64: str = Field(min_length=16)
    scenic_id: str
    gps_hint: GeoPoint | None = None


class PhotoSceneResponse(BaseDTO):
    status: str
    landmark_id: str | None
    landmark_name: str | None
    confidence: float
    narration: str
    follow_up: str | None = None

