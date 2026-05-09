# SCORE-IMPACT: Role-aware auth dependencies for HTTP + WebSocket.
"""FastAPI dependencies that resolve and validate the current principal.

Usage:
    - @router.get("/x", dependencies=[Depends(require_role("admin"))])
    - def handler(current: CurrentTourist): ...
    - WebSocket: call `auth_websocket(ws, settings, required_role="tourist")`
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from aether_api.auth.jwt import decode_token
from aether_api.config import Settings
from aether_api.errors import AppError, ErrorCode

_bearer_scheme = HTTPBearer(auto_error=False, bearerFormat="JWT")


@dataclass(slots=True, frozen=True)
class Principal:
    """Authenticated actor extracted from a JWT."""

    subject: str
    role: str
    jti: str
    email: str | None = None
    name: str | None = None


def _settings_from_request(request: Request) -> Settings:
    settings = request.app.state.settings
    assert isinstance(settings, Settings)
    return settings


def _principal_from_payload(payload: dict[str, object]) -> Principal:
    return Principal(
        subject=str(payload["sub"]),
        role=str(payload["role"]),
        jti=str(payload["jti"]),
        email=str(payload.get("email")) if payload.get("email") else None,
        name=str(payload.get("name")) if payload.get("name") else None,
    )


def get_current_principal(
    request: Request,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> Principal:
    """Return the Principal from `Authorization: Bearer <jwt>`. 401 on missing/invalid."""
    if creds is None or not creds.credentials:
        raise AppError(
            ErrorCode.bad_request,
            "Authentication required.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    settings = _settings_from_request(request)
    payload = decode_token(settings, creds.credentials)
    principal = _principal_from_payload(payload)
    request.state.principal = principal
    return principal


def require_role(role: str):  # type: ignore[no-untyped-def]
    """Return a FastAPI dependency that enforces `role`."""

    def _dep(
        request: Request,
        principal: Annotated[Principal, Depends(get_current_principal)],
    ) -> Principal:
        if principal.role != role:
            raise AppError(
                ErrorCode.bad_request,
                f"This endpoint requires role '{role}'.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        request.state.principal = principal
        return principal

    return _dep


CurrentAdmin = Annotated[Principal, Depends(require_role("admin"))]
CurrentTourist = Annotated[Principal, Depends(require_role("tourist"))]
CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]


async def authenticate_websocket(
    websocket: WebSocket,
    *,
    required_role: str,
) -> Principal | None:
    """Validate a token from the `?token=` query param. None means auth failed.

    Caller is responsible for accepting / closing the websocket. On failure this
    helper will close with code 1008 (policy violation) and return None.
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="auth required")
        return None
    settings = websocket.app.state.settings
    assert isinstance(settings, Settings)
    try:
        payload = decode_token(settings, token)
    except AppError:
        await websocket.close(code=1008, reason="invalid token")
        return None
    principal = _principal_from_payload(payload)
    if principal.role != required_role:
        await websocket.close(code=1008, reason="role mismatch")
        return None
    return principal
