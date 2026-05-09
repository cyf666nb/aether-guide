# SCORE-IMPACT: End-to-end trace propagation for every demo request.
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from aether_api.config import Settings
from aether_api.tracing import new_trace_id, set_trace_id


class TraceMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        super().__init__(app)
        self._header_name = settings.trace_header_name

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        trace_id = request.headers.get(self._header_name, new_trace_id())
        set_trace_id(trace_id)
        response = await call_next(request)
        response.headers[self._header_name] = trace_id
        return response
