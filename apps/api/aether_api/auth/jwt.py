# SCORE-IMPACT: Stateless auth envelope for admin + anonymous flows.
"""JWT create / decode helpers built on pyjwt.

All tokens carry:
- iss=aether-guide
- sub=<subject>
- role=<admin|tourist>
- jti=<uuid4 hex>    (unique token id)
- exp, iat (integer unix seconds)

decode_token raises AppError with a stable code so callers can turn it into
a 401 in the auth dependency.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt

from aether_api.config import Settings
from aether_api.errors import AppError, ErrorCode

_ISSUER = "aether-guide"


def create_token(
    settings: Settings,
    *,
    subject: str,
    role: str,
    ttl_minutes: int,
    extra: dict[str, Any] | None = None,
) -> tuple[str, datetime]:
    """Return (token, expires_at). ttl_minutes must be >= 1."""
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=ttl_minutes)
    payload: dict[str, Any] = {
        "iss": _ISSUER,
        "sub": subject,
        "role": role,
        "jti": uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_at


def decode_token(settings: Settings, token: str) -> dict[str, Any]:
    """Decode + validate a JWT. Raises AppError(401) on any failure."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            issuer=_ISSUER,
            options={"require": ["exp", "iat", "iss", "sub", "role", "jti"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AppError(
            ErrorCode.bad_request, "Token has expired.", status_code=401
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise AppError(
            ErrorCode.bad_request, "Invalid authentication token.", status_code=401
        ) from exc
    return payload
