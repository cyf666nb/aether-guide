# SCORE-IMPACT: API consistency and typed DTO validation.
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BaseDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class BaseResponse[T](BaseModel):
    data: T
    code: str = "OK"
    message: str = "ok"
    trace_id: str


class IdempotentRequest(BaseDTO):
    idempotency_key: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="Client-generated idempotency key for safe retries.",
    )


class GeoPoint(BaseDTO):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0)


class TimedMetric(BaseDTO):
    name: str
    p50_ms: int
    p95_ms: int
    p99_ms: int


class StatusEnvelope(BaseDTO):
    status: str
    at: datetime
