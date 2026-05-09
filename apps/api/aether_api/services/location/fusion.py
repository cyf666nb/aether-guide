# SCORE-IMPACT: Real-world robustness with multi-source positioning.
from aether_api.schemas.common import GeoPoint
from aether_api.schemas.location import LocationInput, LocationResult


class LocationFusion:
    async def fuse(self, scenic_id: str, inputs: list[LocationInput]) -> LocationResult:
        total_weight = sum(item.confidence for item in inputs)
        if total_weight <= 0:
            return LocationResult(
                status="uncertain",
                scenic_id=scenic_id,
                landmark_id=None,
                point=None,
                confidence=0,
                follow_up="Please share a clearer location hint.",
            )
        lat = sum(item.point.lat * item.confidence for item in inputs) / total_weight
        lng = sum(item.point.lng * item.confidence for item in inputs) / total_weight
        confidence = min(1.0, total_weight / len(inputs))
        return LocationResult(
            status="located" if confidence >= 0.7 else "uncertain",
            scenic_id=scenic_id,
            landmark_id=None,
            point=GeoPoint(lat=lat, lng=lng),
            confidence=confidence,
            follow_up=None if confidence >= 0.7 else "Can you scan a nearby QR sign?",
        )

