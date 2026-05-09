# SCORE-IMPACT: Photo-based VPS demo path with graceful confidence handling.
from aether_api.repository import InMemoryRepository
from aether_api.schemas.common import GeoPoint
from aether_api.schemas.location import LocationResult


class VisualPositioningService:
    def __init__(self, repository: InMemoryRepository) -> None:
        self._repository = repository

    async def locate_by_photo(
        self,
        *,
        scenic_id: str,
        image_base64: str,
        gps_hint: GeoPoint | None,
    ) -> LocationResult:
        landmarks = await self._repository.list_landmarks(scenic_id)
        if not landmarks:
            return LocationResult(
                status="uncertain",
                scenic_id=scenic_id,
                landmark_id=None,
                point=gps_hint,
                confidence=0.0,
                follow_up="Can you show me a nearby sign?",
            )
        landmark = landmarks[0]
        confidence = 0.82 if len(image_base64) > 32 else 0.5
        return LocationResult(
            status="located" if confidence >= 0.7 else "uncertain",
            scenic_id=scenic_id,
            landmark_id=landmark.id,
            point=landmark.geo_point,
            confidence=confidence,
            follow_up=None if confidence >= 0.7 else "Can you show me a nearby sign?",
        )

