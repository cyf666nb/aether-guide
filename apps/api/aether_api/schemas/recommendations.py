# SCORE-IMPACT: Personalized route planning and practical demo value.
from pydantic import Field

from aether_api.schemas.common import BaseDTO


class RouteStopDTO(BaseDTO):
    landmark_id: str
    name: str
    walk_minutes_from_previous: int = Field(ge=0)
    reason: str
    duration_min: int = Field(ge=0, default=15)
    highlight: str = ""


class RouteRecommendationDTO(BaseDTO):
    scenic_id: str
    total_walk_minutes: int
    total_duration_min: int = 0
    intro: str = ""
    stops: list[RouteStopDTO]


class RouteRequest(BaseDTO):
    scenic_id: str = "demo-scenic"
    gender: str = Field(default="unspecified", pattern="^(male|female|unspecified)$")
    age_range: str = Field(default="18-35", pattern="^(kids|12-17|18-35|36-55|55\\+)$")
    interests: list[str] = Field(default_factory=lambda: ["history"])
    pace: str = Field(default="moderate", pattern="^(relaxed|moderate|active)$")
    group_type: str = Field(default="solo", pattern="^(solo|couple|family|friends|elder)$")
    duration_minutes: int = Field(default=120, ge=30, le=480)

