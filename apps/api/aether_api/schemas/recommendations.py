# SCORE-IMPACT: Personalized route planning and practical demo value.
from pydantic import Field

from aether_api.schemas.common import BaseDTO


class RouteStopDTO(BaseDTO):
    landmark_id: str
    name: str
    walk_minutes_from_previous: int = Field(ge=0)
    reason: str


class RouteRecommendationDTO(BaseDTO):
    scenic_id: str
    total_walk_minutes: int
    stops: list[RouteStopDTO]

