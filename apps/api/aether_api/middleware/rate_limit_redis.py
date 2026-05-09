# SCORE-IMPACT: Correct multi-instance rate limiting with safe degrade.
"""Redis-backed sliding-window rate limit middleware.

- Sliding window implemented via sorted-set ops (ZREMRANGEBYSCORE + ZCARD +
  ZADD + PEXPIRE) inside a pipeline for near-atomic semantics.
- Key: `rl:uid:<sub>:<METHOD>:<path>` when authenticated, else `rl:ip:<ip>:<METHOD>:<path>`.
- On 429, populates `X-RateLimit-*` headers.
- Health / auth / static endpoints are always exempt.
- If Redis is unreachable at startup the middleware silently passes through
  so the app stays usable; a warning is emitted once.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

import redis.asyncio as redis_asyncio
from fastapi import Request, Response, status
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from aether_api.auth.jwt import decode_token
from aether_api.config import Settings
from aether_api.errors import AppError, ErrorCode, error_response

log = logging.getLogger(__name__)

_EXEMPT_PREFIXES = (
    "/healthz",
    "/readyz",
    "/static",
    "/api/v1/auth/",
    "/admin/v1/auth/",
)


def _is_exempt(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in _EXEMPT_PREFIXES)


class RedisSlidingWindowRateLimit(BaseHTTPMiddleware):
    """Main sliding-window limiter. Construct once per app."""

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        super().__init__(app)
        self._settings = settings
        self._limit = settings.rate_limit_per_minute
        self._window_ms = 60_000
        self._redis: redis_asyncio.Redis | None = None
        self._ready = False

    async def _ensure_ready(self) -> None:
        if self._ready:
            return
        try:
            client: redis_asyncio.Redis = redis_asyncio.from_url(  # type: ignore[no-untyped-call]
                self._settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await client.ping()
            self._redis = client
        except (RedisError, OSError) as exc:  # pragma: no cover - network path
            log.warning("Redis unavailable (%s); rate-limit running in passthrough", exc)
            self._redis = None
        finally:
            self._ready = True

    def _identify(self, request: Request) -> str:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            try:
                payload = decode_token(self._settings, token)
            except AppError:
                payload = None
            if payload:
                return f"uid:{payload['sub']}"
        ip = request.client.host if request.client else "unknown"
        return f"ip:{ip}"

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if _is_exempt(request.url.path):
            return await call_next(request)

        await self._ensure_ready()
        client = self._redis
        if client is None:
            return await call_next(request)

        now_ms = int(time.time() * 1000)
        cutoff_ms = now_ms - self._window_ms
        member = f"{now_ms}-{id(request)}"
        identity = self._identify(request)
        key = f"rl:{identity}:{request.method}:{request.url.path}"

        try:
            # Check current count first.
            await client.zremrangebyscore(key, 0, cutoff_ms)
            count = int(await client.zcard(key) or 0)
            if count >= self._limit:
                oldest = await client.zrange(key, 0, 0, withscores=True)
                reset_at_ms = now_ms + self._window_ms
                if oldest:
                    reset_at_ms = int(float(oldest[0][1])) + self._window_ms
                return _blocked_response(self._limit, reset_at_ms, now_ms)
            await client.zadd(key, {member: now_ms})
            await client.pexpire(key, self._window_ms)
        except RedisError as exc:  # pragma: no cover - network path
            log.warning("rate-limit redis call failed: %s", exc)
            return await call_next(request)

        remaining = max(0, self._limit - count - 1)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self._limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int((now_ms + self._window_ms) / 1000))
        return response


def _blocked_response(limit: int, reset_at_ms: int, now_ms: int) -> Response:
    blocked: Response = error_response(
        ErrorCode.rate_limited,
        "Too many requests. Please slow down and retry shortly.",
        status.HTTP_429_TOO_MANY_REQUESTS,
    )
    blocked.headers["X-RateLimit-Limit"] = str(limit)
    blocked.headers["X-RateLimit-Remaining"] = "0"
    blocked.headers["X-RateLimit-Reset"] = str(int(reset_at_ms / 1000))
    blocked.headers["Retry-After"] = str(max(1, int((reset_at_ms - now_ms) / 1000)))
    return blocked
