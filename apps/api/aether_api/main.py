# SCORE-IMPACT: Runnable FastAPI gateway with traceable demo loop.
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from aether_api.config import Settings, get_settings
from aether_api.errors import register_exception_handlers
from aether_api.middleware.audit import AuditMiddleware
from aether_api.middleware.rate_limit import InMemoryRateLimitMiddleware
from aether_api.middleware.trace import TraceMiddleware
from aether_api.repository import create_repository
from aether_api.routers import admin, location, offline, recommendations, safety, tourist
from aether_api.services.ai.client import AIClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    repository = await create_repository(settings)
    app.state.settings = settings
    app.state.repository = repository
    app.state.ai_client = AIClient(settings)
    try:
        yield
    finally:
        aclose = getattr(repository, "aclose", None)
        if callable(aclose):
            await aclose()


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        openapi_version="3.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(TraceMiddleware, settings=resolved_settings)
    app.add_middleware(InMemoryRateLimitMiddleware, settings=resolved_settings)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(tourist.router, prefix=resolved_settings.api_prefix)
    app.include_router(location.router, prefix=resolved_settings.api_prefix)
    app.include_router(recommendations.router, prefix=resolved_settings.api_prefix)
    app.include_router(safety.router, prefix=resolved_settings.api_prefix)
    app.include_router(offline.router, prefix=resolved_settings.api_prefix)
    app.include_router(admin.router, prefix=resolved_settings.admin_prefix)

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/healthz", tags=["system"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", tags=["system"])
    async def readyz() -> dict[str, str]:
        return {"status": "ready"}

    return app


app = create_app()

