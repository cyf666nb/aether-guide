# SCORE-IMPACT: Safety workflows for lost-tourist and emergency demos.
from fastapi import APIRouter, Depends

from aether_api.auth.dependencies import require_role
from aether_api.dependencies import RepositoryDep
from aether_api.schemas.common import BaseResponse
from aether_api.schemas.safety import EmergencyPointDTO, LostRequest, LostResponseDTO
from aether_api.services.safety.lost import LostTouristService
from aether_api.tracing import current_trace_id

router = APIRouter(
    prefix="/safety",
    tags=["safety"],
    dependencies=[Depends(require_role("tourist"))],
)


@router.post("/lost", response_model=BaseResponse[LostResponseDTO])
async def report_lost(
    payload: LostRequest,
    repository: RepositoryDep,
) -> BaseResponse[LostResponseDTO]:
    response = await LostTouristService(repository).handle_lost(payload.scenic_id)
    return BaseResponse(data=response, trace_id=current_trace_id())


@router.get("/emergency-points", response_model=BaseResponse[list[EmergencyPointDTO]])
async def emergency_points(
    scenic_id: str,
    repository: RepositoryDep,
) -> BaseResponse[list[EmergencyPointDTO]]:
    points = await LostTouristService(repository).find_emergency_points(scenic_id)
    return BaseResponse(data=points, trace_id=current_trace_id())

