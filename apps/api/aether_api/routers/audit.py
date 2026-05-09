# SCORE-IMPACT: Transparent audit surface for admin write operations.
from fastapi import APIRouter, Depends, Query

from aether_api.auth.dependencies import require_role
from aether_api.dependencies import RepositoryDep
from aether_api.schemas.admin import AuditLogPage
from aether_api.schemas.common import BaseResponse
from aether_api.tracing import current_trace_id

router = APIRouter(tags=["admin"], dependencies=[Depends(require_role("admin"))])


@router.get("/audit-logs", response_model=BaseResponse[AuditLogPage])
async def list_audit_logs(
    repository: RepositoryDep,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
) -> BaseResponse[AuditLogPage]:
    page = await repository.list_audit_logs(limit=limit, cursor=cursor)
    return BaseResponse(data=page, trace_id=current_trace_id())
