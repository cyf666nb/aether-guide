# SCORE-IMPACT: Safety workflow and emergency-point response.
from aether_api.repository import Repository
from aether_api.schemas.safety import EmergencyPointDTO, LostResponseDTO


class LostTouristService:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    async def find_emergency_points(self, scenic_id: str) -> list[EmergencyPointDTO]:
        """Return the nearest emergency points for the scenic area.

        Pure read — no alerting, no side-effects. Safe for GET.
        """
        landmarks = await self._repository.nearest_emergency_points(scenic_id)
        return [
            EmergencyPointDTO(
                id=f"emergency-{item.id}",
                name=f"{item.name} service point",
                phone="400-000-2026",
                geo_point=item.geo_point,
                walk_minutes=5 + index * 3,
            )
            for index, item in enumerate(landmarks[:3])
        ]

    async def handle_lost(self, scenic_id: str) -> LostResponseDTO:
        """POST-side: the lost-tourist workflow composes the same points."""
        points = await self.find_emergency_points(scenic_id)
        return LostResponseDTO(
            message="Stay where you are if safe. The nearest help points are below.",
            nearest_points=points,
            call_hint="Tap to call the scenic-area emergency desk.",
        )
