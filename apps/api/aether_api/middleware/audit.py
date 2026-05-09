# SCORE-IMPACT: Enterprise governance — real audit-log persistence.
"""After admin writes, persist a row in audit_logs.

Runs as BaseHTTPMiddleware so it sees the authenticated principal placed into
`request.state.principal` by the auth dependency and the final response body.
Failures while recording are logged but do not fail the request.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

log = logging.getLogger(__name__)

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)

        # Only audit admin writes (path starts with /admin/v1 and method is a write)
        if request.method not in _WRITE_METHODS:
            return response
        path = request.url.path
        if not path.startswith("/admin/"):
            return response
        # Skip the auth endpoints themselves to avoid recording the password.
        if path.endswith("/auth/login"):
            return response

        # Try to recover the admin id set by require_role("admin").
        principal = getattr(request.state, "principal", None)
        admin_id = getattr(principal, "subject", None) if principal else None

        repository = request.app.state.repository
        # Read the response body so we can log the after-state. The body must
        # be re-emitted in a new Response or the client sees nothing.
        streaming = cast(StreamingResponse, response)
        body_parts: list[bytes] = []
        async for chunk in streaming.body_iterator:
            if isinstance(chunk, bytes):
                body_parts.append(chunk)
            elif isinstance(chunk, memoryview):
                body_parts.append(bytes(chunk))
            else:
                body_parts.append(chunk.encode("utf-8"))
        body_bytes = b"".join(body_parts)
        try:
            parsed = json.loads(body_bytes.decode("utf-8")) if body_bytes else None
            after = parsed.get("data") if isinstance(parsed, dict) else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            after = None
        target = _derive_target(after)

        response.headers["X-Audit-Recorded"] = "true"
        try:
            await repository.insert_audit_log(
                admin_id=admin_id,
                action=f"{request.method} {path}",
                target=target,
                before=None,
                after=after if isinstance(after, dict) else None,
            )
        except Exception:  # pragma: no cover - we never want auditing to crash prod
            log.exception("audit-log insert failed for %s %s", request.method, path)

        return Response(
            content=body_bytes,
            status_code=response.status_code,
            headers=response.headers,
            media_type=response.media_type,
        )


def _derive_target(after: object) -> str:
    if not isinstance(after, dict):
        return "-"
    for key in ("id", "scenic_id", "email", "name"):
        value = after.get(key)
        if isinstance(value, str) and value:
            return value
    return "-"
