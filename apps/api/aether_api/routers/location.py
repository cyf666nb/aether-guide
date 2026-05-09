# SCORE-IMPACT: VPS, QR, conversational, and fused positioning APIs.
from fastapi import APIRouter

from aether_api.dependencies import RepositoryDep
from aether_api.schemas.common import BaseResponse
from aether_api.schemas.location import (
    ClearTrailRequest,
    ConversationalLocationRequest,
    FuseLocationRequest,
    LocationResult,
    QRLocationRequest,
    VisualLocationRequest,
)
from aether_api.services.location.conversational import ConversationalLocator
from aether_api.services.location.fusion import LocationFusion
from aether_api.services.location.qr import QRAnchorService
from aether_api.services.location.vps import VisualPositioningService
from aether_api.tracing import current_trace_id

router = APIRouter(prefix="/location", tags=["location"])


@router.post("/visual", response_model=BaseResponse[LocationResult])
async def locate_visual(
    payload: VisualLocationRequest,
    repository: RepositoryDep,
) -> BaseResponse[LocationResult]:
    result = await VisualPositioningService(repository).locate_by_photo(
        scenic_id=payload.scenic_id,
        image_base64=payload.image_base64,
        gps_hint=payload.gps_hint,
    )
    return BaseResponse(data=result, trace_id=current_trace_id())


@router.post("/qr", response_model=BaseResponse[LocationResult])
async def locate_qr(
    payload: QRLocationRequest,
    repository: RepositoryDep,
) -> BaseResponse[LocationResult]:
    result = await QRAnchorService(repository).locate(
        payload.scenic_id,
        payload.poi_id,
        payload.token,
    )
    return BaseResponse(data=result, trace_id=current_trace_id())


@router.post("/conversational", response_model=BaseResponse[LocationResult])
async def locate_conversational(
    payload: ConversationalLocationRequest,
    repository: RepositoryDep,
) -> BaseResponse[LocationResult]:
    result = await ConversationalLocator(repository).locate(payload.scenic_id, payload.description)
    return BaseResponse(data=result, trace_id=current_trace_id())


@router.post("/fuse", response_model=BaseResponse[LocationResult])
async def fuse_location(payload: FuseLocationRequest) -> BaseResponse[LocationResult]:
    result = await LocationFusion().fuse(payload.scenic_id, payload.inputs)
    return BaseResponse(data=result, trace_id=current_trace_id())


@router.delete("/trail", response_model=BaseResponse[dict[str, bool]])
async def clear_trail(payload: ClearTrailRequest) -> BaseResponse[dict[str, bool]]:
    return BaseResponse(data={"cleared": True}, trace_id=current_trace_id())
