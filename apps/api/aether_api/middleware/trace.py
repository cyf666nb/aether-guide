# SCORE-IMPACT: End-to-end trace propagation with header sanitization.
import logging
import re
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from aether_api.config import Settings
from aether_api.tracing import new_trace_id, set_trace_id

log = logging.getLogger(__name__)

# Tokens with only safe chars, length 8..128.
_TRACE_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{8,128}$")


class TraceMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        super().__init__(app)
        self._header_name = settings.trace_header_name

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        raw = request.headers.get(self._header_name)
        if raw is None or not _TRACE_ID_RE.match(raw):
            if raw is not None:
                log.info("trace-id sanitized; original dropped (len=%d)", len(raw))
            trace_id = new_trace_id()
        else:
            trace_id = raw
        set_trace_id(trace_id)
        response = await call_next(request)
        response.headers[self._header_name] = trace_id
        return response
