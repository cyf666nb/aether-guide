from typing import Any, cast

from aether_api.schemas.common import GeoPoint
from aether_api.schemas.landmarks import LandmarkDTO
from aether_api.services.location.vps import VisualPositioningService


def _landmark(landmark_id: str, name: str) -> LandmarkDTO:
    return LandmarkDTO(
        id=landmark_id,
        scenic_id="demo-scenic",
        name=name,
        summary=f"{name} summary",
        geo_point=GeoPoint(lat=26.0835, lng=119.2967, accuracy_m=10),
        tags=[],
        avg_duration_min=10,
        emergency_nearby=[],
    )


def test_vlm_payload_can_return_catalog_place_outside_curated_landmarks() -> None:
    service = VisualPositioningService(cast(Any, None))
    landmarks = [_landmark("nanhou-street", "南后街")]

    result = service._location_from_vlm_payload(
        {
            "place_name": "塔巷",
            "landmark_id": "ta-alley",
            "confidence": 0.87,
            "description": "画面中有塔巷巷名牌",
        },
        "demo-scenic",
        landmarks,
    )

    assert result.status == "located"
    assert result.landmark_id is None
    assert result.landmark_name == "塔巷"
    assert result.confidence == 0.87


def test_vlm_payload_maps_alias_to_curated_landmark_id() -> None:
    service = VisualPositioningService(cast(Any, None))
    landmarks = [_landmark("linjuemin-bingxin", "林觉民·冰心故居")]

    result = service._location_from_vlm_payload(
        {
            "place_name": "林觉民冰心故居",
            "landmark_id": None,
            "confidence": 0.92,
            "description": "看到故居门牌",
        },
        "demo-scenic",
        landmarks,
    )

    assert result.status == "located"
    assert result.landmark_id == "linjuemin-bingxin"
    assert result.landmark_name == "林觉民·冰心故居"
