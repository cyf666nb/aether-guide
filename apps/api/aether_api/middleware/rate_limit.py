# SCORE-IMPACT: Stability, LLM cost guardrails, and abuse resistance.
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from time import monotonic

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from aether_api.config import Settings
from aether_api.errors import ErrorCode, error_response


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        super().__init__(app)
        self._limit = settings.rate_limit_per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path in {"/healthz", "/readyz"}:
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        key = f"{client}:{request.url.path}"
        now = monotonic()
        window = self._hits[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self._limit:
            return error_response(
                ErrorCode.rate_limited,
                "Too many requests. Please slow down and retry shortly.",
                status.HTTP_429_TOO_MANY_REQUESTS,
            )
        window.append(now)
        return await call_next(request)
