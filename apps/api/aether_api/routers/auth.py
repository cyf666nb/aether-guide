# SCORE-IMPACT: Stateless admin login + anonymous tourist bootstrap.
from uuid import uuid4

from fastapi import APIRouter, Request

from aether_api.auth.jwt import create_token
from aether_api.auth.password import verify_password
from aether_api.config import Settings
from aether_api.dependencies import RepositoryDep
from aether_api.errors import AppError, ErrorCode
from aether_api.schemas.auth import (
    AdminLoginRequest,
    AdminLoginResponseDTO,
    AdminProfileDTO,
    TokenDTO,
)
from aether_api.schemas.common import BaseResponse
from aether_api.tracing import current_trace_id

admin_router = APIRouter(prefix="/auth", tags=["auth"])
tourist_router = APIRouter(prefix="/auth", tags=["auth"])


def _settings(request: Request) -> Settings:
    settings = request.app.state.settings
    assert isinstance(settings, Settings)
    return settings


@admin_router.post("/login", response_model=BaseResponse[AdminLoginResponseDTO])
async def admin_login(
    request: Request,
    payload: AdminLoginRequest,
    repository: RepositoryDep,
) -> BaseResponse[AdminLoginResponseDTO]:
    settings = _settings(request)
    admin = await repository.find_admin_by_email(payload.email)
    if admin is None or not verify_password(payload.password, admin.password_hash):
        raise AppError(
            ErrorCode.bad_request,
            "Email or password is incorrect.",
            status_code=401,
        )

    token, expires_at = create_token(
        settings,
        subject=admin.id,
        role=admin.role,
        ttl_minutes=settings.admin_token_ttl_minutes,
        extra={"email": admin.email, "name": admin.name},
    )
    response = AdminLoginResponseDTO(
        token=TokenDTO(
            token=token,
            role=admin.role,
            subject=admin.id,
            expires_at=expires_at,
        ),
        profile=AdminProfileDTO(
            admin_id=admin.id,
            name=admin.name,
            email=admin.email,
            role=admin.role,
        ),
    )
    return BaseResponse(data=response, trace_id=current_trace_id())


@tourist_router.post("/anonymous", response_model=BaseResponse[TokenDTO])
async def tourist_anonymous(request: Request) -> BaseResponse[TokenDTO]:
    settings = _settings(request)
    uid = f"tourist-{uuid4().hex[:12]}"
    token, expires_at = create_token(
        settings,
        subject=uid,
        role="tourist",
        ttl_minutes=settings.tourist_token_ttl_minutes,
    )
    return BaseResponse(
        data=TokenDTO(
            token=token,
            role="tourist",
            subject=uid,
            expires_at=expires_at,
        ),
        trace_id=current_trace_id(),
    )
