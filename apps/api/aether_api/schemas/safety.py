# SCORE-IMPACT: Lost-tourist protection and emergency readiness.
from pydantic import Field

from aether_api.schemas.common import BaseDTO, GeoPoint, IdempotentRequest


class LostRequest(IdempotentRequest):
    scenic_id: str
    user_id: str | None = None
    current_location: GeoPoint | None = None


class EmergencyPointDTO(BaseDTO):
    id: str
    name: str
    phone: str
    geo_point: GeoPoint
    walk_minutes: int = Field(ge=0)


class LostResponseDTO(BaseDTO):
    message: str
    nearest_points: list[EmergencyPointDTO]
    call_hint: str

