# SCORE-IMPACT: Personalized route endpoint for W1/W3 demo continuity.
from fastapi import APIRouter

from aether_api.dependencies import RepositoryDep
from aether_api.schemas.common import BaseResponse
from aether_api.schemas.recommendations import RouteRecommendationDTO
from aether_api.services.recommend.routes import RoutePlanner
from aether_api.tracing import current_trace_id

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/route", response_model=BaseResponse[RouteRecommendationDTO])
async def recommend_route(
    scenic_id: str,
    repository: RepositoryDep,
) -> BaseResponse[RouteRecommendationDTO]:
    route = await RoutePlanner(repository).recommend(scenic_id)
    return BaseResponse(data=route, trace_id=current_trace_id())

