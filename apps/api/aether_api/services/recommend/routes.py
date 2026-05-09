# SCORE-IMPACT: Personalized route planning demo loop.
from aether_api.repository import InMemoryRepository
from aether_api.schemas.recommendations import RouteRecommendationDTO, RouteStopDTO


class RoutePlanner:
    def __init__(self, repository: InMemoryRepository) -> None:
        self._repository = repository

    async def recommend(self, scenic_id: str) -> RouteRecommendationDTO:
        landmarks = await self._repository.list_landmarks(scenic_id)
        stops = [
            RouteStopDTO(
                landmark_id=item.id,
                name=item.name,
                walk_minutes_from_previous=0 if index == 0 else 8,
                reason="Seed route balances popular spots with low walking time.",
            )
            for index, item in enumerate(landmarks[:3])
        ]
        return RouteRecommendationDTO(
            scenic_id=scenic_id,
            total_walk_minutes=sum(stop.walk_minutes_from_previous for stop in stops),
            stops=stops,
        )

