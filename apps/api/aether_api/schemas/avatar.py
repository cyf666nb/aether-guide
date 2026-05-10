# SCORE-IMPACT: Stable avatar manifest contract between API and tourist app.
"""DTOs for the digital-human avatar manifest endpoint.

Mirrors the dataclasses in
``aether_api.services.digital_human.client`` but as Pydantic models so
FastAPI can serialize them and OpenAPI documents the shape.
"""
from __future__ import annotations

from aether_api.schemas.common import BaseDTO


class LipSyncConfigDTO(BaseDTO):
    parameter_id: str
    smoothing: float
    gain: float


class AvatarManifestDTO(BaseDTO):
    engine: str
    enabled: bool
    model_url: str
    name: str
    locale: str
    default_expression: str | None
    idle_motion_group: str
    lipsync: LipSyncConfigDTO
    fallback: str
    license_url: str
