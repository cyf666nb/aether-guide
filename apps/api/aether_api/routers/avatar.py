# SCORE-IMPACT: Surfaces the digital-human contract so the frontend can render.
"""Avatar manifest router.

Exposes the Live2D model + lipsync config so the tourist web app doesn't
have to hardcode model paths. Public (no auth required) — the manifest
contains zero user-scoped data; CDNs and offline mode benefit from being
able to cache it anonymously.
"""
from __future__ import annotations

from fastapi import APIRouter

from aether_api.schemas.avatar import AvatarManifestDTO, LipSyncConfigDTO
from aether_api.schemas.common import BaseResponse
from aether_api.services.digital_human.client import DigitalHumanClient
from aether_api.tracing import current_trace_id

router = APIRouter(tags=["avatar"])

# A single client is enough — the manifest is constant for the life of
# the process. No state, no I/O, no need to spin one up per request.
_client = DigitalHumanClient()


@router.get(
    "/avatar/manifest",
    response_model=BaseResponse[AvatarManifestDTO],
    summary="Live2D digital-human manifest",
)
async def get_avatar_manifest() -> BaseResponse[AvatarManifestDTO]:
    manifest = _client.manifest()
    dto = AvatarManifestDTO(
        engine=manifest.engine,
        enabled=manifest.enabled,
        model_url=manifest.model_url,
        name=manifest.name,
        locale=manifest.locale,
        default_expression=manifest.default_expression,
        idle_motion_group=manifest.idle_motion_group,
        lipsync=LipSyncConfigDTO(
            parameter_id=manifest.lipsync.parameter_id,
            smoothing=manifest.lipsync.smoothing,
            gain=manifest.lipsync.gain,
        ),
        fallback=manifest.fallback,
        license_url=manifest.license_url,
    )
    return BaseResponse(data=dto, trace_id=current_trace_id())
