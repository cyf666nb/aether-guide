# SCORE-IMPACT: AI-powered personalized route endpoint.
from fastapi import APIRouter, Depends

from aether_api.auth.dependencies import require_role
from aether_api.dependencies import AIClientDep, RepositoryDep
from aether_api.schemas.common import BaseResponse
from aether_api.schemas.recommendations import RouteRecommendationDTO, RouteRequest
from aether_api.services.recommend.routes import RoutePlanner
from aether_api.tracing import current_trace_id

router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"],
    dependencies=[Depends(require_role("tourist"))],
)


@router.post("/route", response_model=BaseResponse[RouteRecommendationDTO])
async def recommend_route(
    payload: RouteRequest,
    repository: RepositoryDep,
    ai_client: AIClientDep,
) -> BaseResponse[RouteRecommendationDTO]:
    route = await RoutePlanner(repository).recommend(payload, ai_client=ai_client)
    return BaseResponse(data=route, trace_id=current_trace_id())

