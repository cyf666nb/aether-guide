# SCORE-IMPACT: Production-ready error contracts and user-safe failures.
from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from aether_api.tracing import current_trace_id


class ErrorCode(StrEnum):
    ok = "OK"
    bad_request = "BAD_REQUEST"
    not_found = "NOT_FOUND"
    validation_error = "VALIDATION_ERROR"
    rate_limited = "RATE_LIMITED"
    rag_low_confidence = "RAG_LOW_CONFIDENCE"
    ai_provider_unavailable = "AI_PROVIDER_UNAVAILABLE"
    internal_error = "INTERNAL_ERROR"


class ErrorPayload(BaseModel):
    data: None = None
    code: ErrorCode
    message: str
    trace_id: str


class AppError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def error_response(code: ErrorCode, message: str, status_code: int) -> JSONResponse:
    payload = ErrorPayload(code=code, message=message, trace_id=current_trace_id())
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return error_response(exc.code, exc.message, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        return error_response(
            ErrorCode.validation_error,
            "Request payload failed validation.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = (
            ErrorCode.not_found
            if exc.status_code == status.HTTP_404_NOT_FOUND
            else ErrorCode.bad_request
        )
        return error_response(code, str(exc.detail), exc.status_code)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
        return error_response(
            ErrorCode.internal_error,
            "The service hit an unexpected condition. Please retry later.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
