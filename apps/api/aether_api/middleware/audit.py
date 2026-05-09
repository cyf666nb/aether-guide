# SCORE-IMPACT: Enterprise governance and admin write accountability.
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            response.headers["X-Audit-Recorded"] = "true"
        return response

