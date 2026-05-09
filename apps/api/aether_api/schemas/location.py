# SCORE-IMPACT: Real-world robustness via VPS, QR anchors, and location fusion.
from enum import StrEnum

from pydantic import Field

from aether_api.schemas.common import BaseDTO, GeoPoint, IdempotentRequest


class LocationSource(StrEnum):
    gps = "gps"
    vps = "vps"
    qr = "qr"
    conversational = "conversational"
    pdr = "pdr"


class LocationInput(BaseDTO):
    source: LocationSource
    point: GeoPoint
    confidence: float = Field(ge=0, le=1)


class VisualLocationRequest(IdempotentRequest):
    scenic_id: str
    image_base64: str = Field(min_length=16)
    gps_hint: GeoPoint | None = None


class QRLocationRequest(IdempotentRequest):
    scenic_id: str
    poi_id: str
    token: str = Field(min_length=8)


class ConversationalLocationRequest(IdempotentRequest):
    scenic_id: str
    description: str = Field(min_length=2, max_length=1000)


class FuseLocationRequest(IdempotentRequest):
    scenic_id: str
    user_id: str | None = None
    inputs: list[LocationInput] = Field(min_length=1)


class LocationResult(BaseDTO):
    status: str
    scenic_id: str
    landmark_id: str | None
    point: GeoPoint | None
    confidence: float
    follow_up: str | None = None


class ClearTrailRequest(BaseDTO):
    user_id: str
    scenic_id: str

