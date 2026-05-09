# SCORE-IMPACT: RAG grounding, recommendation utility, and offline demo data.
from pydantic import Field

from aether_api.schemas.common import BaseDTO, GeoPoint


class LandmarkDTO(BaseDTO):
    id: str
    scenic_id: str
    name: str
    summary: str
    geo_point: GeoPoint
    tags: list[str]
    avg_duration_min: int = Field(ge=1)
    audio_cache_uri: str | None = None
    emergency_nearby: list[str]


class LandmarkListDTO(BaseDTO):
    scenic_id: str
    landmarks: list[LandmarkDTO]

