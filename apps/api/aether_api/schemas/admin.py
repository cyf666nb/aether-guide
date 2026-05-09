# SCORE-IMPACT: Knowledge operations, prompt governance, and analytics demos.
from datetime import datetime
from enum import StrEnum

from pydantic import Field

from aether_api.schemas.common import BaseDTO, IdempotentRequest, TimedMetric


class DocumentStatus(StrEnum):
    queued = "queued"
    indexing = "indexing"
    ready = "ready"
    failed = "failed"


class UploadDocumentRequest(IdempotentRequest):
    scenic_id: str
    title: str = Field(min_length=1, max_length=200)
    source_uri: str = Field(min_length=1)
    version: str = "v1"


class DocumentDTO(BaseDTO):
    id: str
    scenic_id: str
    title: str
    source_uri: str
    version: str
    status: DocumentStatus
    indexed_at: datetime | None = None


class IndexProgressDTO(BaseDTO):
    document_id: str
    status: DocumentStatus
    percent: int = Field(ge=0, le=100)
    message: str


class PersonaRequest(IdempotentRequest):
    scenic_id: str
    name: str = Field(min_length=1, max_length=100)
    voice_id: str
    avatar_id: str
    system_prompt: str = Field(min_length=10, max_length=8000)
    version: str = "v1"
    status: str = "draft"


class PersonaDTO(BaseDTO):
    id: str
    scenic_id: str
    name: str
    voice_id: str
    avatar_id: str
    system_prompt: str
    version: str
    status: str


class PromptExperimentRequest(IdempotentRequest):
    name: str = Field(min_length=1, max_length=120)
    variant_a: str
    variant_b: str
    traffic_split: float = Field(default=0.5, ge=0, le=1)
    metric: str = "satisfaction"


class PromptExperimentDTO(BaseDTO):
    id: str
    name: str
    traffic_split: float
    metric: str
    status: str
    winner: str | None = None


class DashboardOverviewDTO(BaseDTO):
    active_sessions: int
    token_cost_usd_today: float
    cache_hit_rate: float
    nps: float
    latency: list[TimedMetric]


class SessionReplayDTO(BaseDTO):
    session_id: str
    user_waveform_uri: str | None
    tts_waveform_uri: str | None
    events: list[dict[str, str]]
    retrieved_chunks: list[str]


class TurnLabelRequest(IdempotentRequest):
    label: str = Field(min_length=1, max_length=80)
    notes: str | None = Field(default=None, max_length=1000)


class TurnLabelDTO(BaseDTO):
    turn_id: str
    accepted: bool


class AuditLogDTO(BaseDTO):
    id: str
    admin_id: str | None
    action: str
    target: str
    at: datetime
    before: dict[str, object] | None = None
    after: dict[str, object] | None = None


class AuditLogPage(BaseDTO):
    items: list[AuditLogDTO]
    next_cursor: str | None = None

