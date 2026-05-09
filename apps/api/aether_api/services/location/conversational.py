# SCORE-IMPACT: GPS-free wayfinding and lost-tourist recovery.
from aether_api.repository import Repository
from aether_api.schemas.location import LocationResult


class ConversationalLocator:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    async def locate(self, scenic_id: str, description: str) -> LocationResult:
        landmarks = await self._repository.list_landmarks(scenic_id)
        normalized = description.lower()
        for landmark in landmarks:
            haystack = " ".join([landmark.name, landmark.summary, *landmark.tags]).lower()
            if any(token in haystack for token in normalized.split()):
                return LocationResult(
                    status="located",
                    scenic_id=scenic_id,
                    landmark_id=landmark.id,
                    point=landmark.geo_point,
                    confidence=0.76,
                )
        return LocationResult(
            status="uncertain",
            scenic_id=scenic_id,
            landmark_id=None,
            point=None,
            confidence=0.4,
            follow_up="Can you describe a sign, water, bridge, or nearby building?",
        )

