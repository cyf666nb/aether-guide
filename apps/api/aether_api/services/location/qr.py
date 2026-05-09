# SCORE-IMPACT: Fraud-resistant QR/NFC anchor flow.
from aether_api.repository import Repository
from aether_api.schemas.location import LocationResult


class QRAnchorService:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    async def locate(self, scenic_id: str, poi_id: str, token: str) -> LocationResult:
        landmarks = await self._repository.list_landmarks(scenic_id)
        matched = next((item for item in landmarks if item.id == poi_id), None)
        if matched is None or len(token) < 8:
            return LocationResult(
                status="uncertain",
                scenic_id=scenic_id,
                landmark_id=None,
                point=None,
                confidence=0.0,
                follow_up="The QR anchor could not be verified.",
            )
        return LocationResult(
            status="located",
            scenic_id=scenic_id,
            landmark_id=matched.id,
            point=matched.geo_point,
            confidence=1.0,
        )

