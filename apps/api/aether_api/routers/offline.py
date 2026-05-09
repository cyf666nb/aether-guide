# SCORE-IMPACT: Offline-first scenic package contract.
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response

from aether_api.auth.dependencies import require_role
from aether_api.schemas.common import BaseDTO, BaseResponse
from aether_api.tracing import current_trace_id

router = APIRouter(
    prefix="/scenic",
    tags=["offline"],
    dependencies=[Depends(require_role("tourist"))],
)


class OfflinePackDTO(BaseDTO):
    scenic_id: str
    version: str
    size_mb: int
    assets: list[str]
    generated_at: datetime


@router.get("/{scenic_id}/offline-pack", response_model=BaseResponse[OfflinePackDTO])
async def offline_pack(scenic_id: str, response: Response) -> BaseResponse[OfflinePackDTO]:
    response.headers["ETag"] = f'W/"{scenic_id}-demo-v1"'
    return BaseResponse(
        data=OfflinePackDTO(
            scenic_id=scenic_id,
            version="demo-v1",
            size_mb=12,
            assets=["landmarks.json", "faq-top100.json", "audio-cache/index.json"],
            generated_at=datetime.now(UTC),
        ),
        trace_id=current_trace_id(),
    )
