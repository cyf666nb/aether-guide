# SCORE-IMPACT: Runnable FastAPI gateway with traceable demo loop.
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from aether_api.auth.seed import seed_admins
from aether_api.config import Settings, get_settings
from aether_api.errors import ErrorCode, error_response, register_exception_handlers
from aether_api.middleware.audit import AuditMiddleware
from aether_api.middleware.rate_limit_redis import RedisSlidingWindowRateLimit
from aether_api.middleware.trace import TraceMiddleware
from aether_api.repository import Repository, create_repository
from aether_api.routers import (
    admin,
    audit,
    auth,
    avatar,
    location,
    offline,
    recommendations,
    safety,
    tourist,
)
from aether_api.services.ai.client import AIClient
from aether_api.services.rag.embedding import BGEEmbedding
from aether_api.services.rag.vectorstore import QdrantVectorStore

_MAX_BODY_BYTES = 1 * 1024 * 1024  # 1 MB


class RequestBodyLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds _MAX_BODY_BYTES (413)."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                length = 0
            if length > _MAX_BODY_BYTES:
                return error_response(
                    ErrorCode.bad_request,
                    "Request body is too large.",
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    repository = await create_repository(settings)
    await seed_admins(settings, repository)

    vectorstore: QdrantVectorStore | None = None
    embedding: BGEEmbedding | None = None
    if settings.qdrant_url:
        vectorstore = QdrantVectorStore(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None,
        )
        embedding = BGEEmbedding(
            model_name=settings.embedding_model_name,
            use_gpu=settings.embedding_use_gpu,
        )
        if vectorstore.is_available():
            # Load the model up-front (2–5s for bge-m3) so the first user query
            # doesn't pay the cold-start cost. Runs in a thread to keep the
            # event loop responsive while other init tasks continue.
            import asyncio as _asyncio

            await _asyncio.to_thread(embedding.warm)
            await _seed_qdrant(repository, vectorstore, embedding, settings)
        else:
            import logging

            logging.getLogger(__name__).warning(
                "Qdrant configured but unavailable at %s, falling back to full-scan",
                settings.qdrant_url,
            )
            vectorstore = None
            embedding = None

    app.state.settings = settings
    app.state.repository = repository
    app.state.ai_client = AIClient(settings)
    app.state.vectorstore = vectorstore
    app.state.embedding = embedding
    try:
        yield
    finally:
        await app.state.ai_client.aclose()
        from aether_api.services.location.vps import (
            aclose_shared_client as _aclose_vlm,
        )
        from aether_api.services.tts.client import aclose_shared_client as _aclose_tts

        await _aclose_vlm()
        await _aclose_tts()
        if vectorstore is not None:
            vectorstore.close()
        aclose = getattr(repository, "aclose", None)
        if callable(aclose):
            await aclose()


async def _seed_qdrant(
    repository: Repository,
    vectorstore: QdrantVectorStore,
    embedding: BGEEmbedding,
    settings: Settings,
) -> None:
    import logging

    logger = logging.getLogger(__name__)
    try:
        landmarks = await repository.list_landmarks("demo-scenic")
        chunks = await repository.list_knowledge_chunks("demo-scenic")
        if not chunks and not landmarks:
            return

        dimensions = embedding.dimensions
        vectorstore.ensure_collection("demo-scenic", dimensions=dimensions)

        from aether_api.services.rag.retriever import _landmark_to_chunk

        all_chunks = list(chunks)
        for lm in landmarks:
            all_chunks.append(_landmark_to_chunk(0, lm))

        if not all_chunks:
            return

        # Skip the (expensive) re-encode + upsert if Qdrant is already populated
        # with the expected number of points. The collection is rewritten by the
        # admin indexer whenever documents change, so this is safe.
        existing = vectorstore.collection_point_count("demo-scenic")
        if existing is not None and existing >= len(all_chunks):
            logger.info(
                "Qdrant demo-scenic already has %d points (expected %d); skipping seed",
                existing,
                len(all_chunks),
            )
            return

        import asyncio as _asyncio

        texts = [chunk.text for chunk in all_chunks]
        # encode_texts is heavy CPU (numpy) work — keep it off the event loop.
        embeddings = await _asyncio.to_thread(embedding.encode_texts, texts)
        chunk_ids = [chunk.id for chunk in all_chunks]
        payloads = [
            {
                "source_id": chunk.source_id,
                "document_id": chunk.document_id or "",
                "text": chunk.text[:500],
                "scenic_id": chunk.scenic_id,
                **chunk.metadata,
            }
            for chunk in all_chunks
        ]
        await _asyncio.to_thread(
            vectorstore.upsert_chunks,
            "demo-scenic",
            chunk_ids,
            embeddings,
            payloads,
        )
        logger.info("Seeded %d chunks into Qdrant for demo-scenic", len(all_chunks))
    except Exception:
        logger.exception("Failed to seed Qdrant")


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        openapi_version="3.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(TraceMiddleware, settings=resolved_settings)
    app.add_middleware(RedisSlidingWindowRateLimit, settings=resolved_settings)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RequestBodyLimitMiddleware)
    # CORS: origins come from settings (env-driven). Production config guards
    # against wildcard in aether_api.config.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(auth.tourist_router, prefix=resolved_settings.api_prefix)
    app.include_router(auth.admin_router, prefix=resolved_settings.admin_prefix)
    app.include_router(tourist.router, prefix=resolved_settings.api_prefix)
    app.include_router(location.router, prefix=resolved_settings.api_prefix)
    app.include_router(recommendations.router, prefix=resolved_settings.api_prefix)
    app.include_router(safety.router, prefix=resolved_settings.api_prefix)
    app.include_router(avatar.router, prefix=resolved_settings.api_prefix)
    app.include_router(offline.router, prefix=resolved_settings.api_prefix)
    app.include_router(admin.router, prefix=resolved_settings.admin_prefix)
    app.include_router(audit.router, prefix=resolved_settings.admin_prefix)

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/healthz", tags=["system"])
    async def healthz() -> dict[str, str]:
        runtime_settings = app.state.settings
        repo = app.state.repository
        backend_name = getattr(repo, "backend_name", "unknown")
        fallback_reason = getattr(repo, "backend_fallback_reason", None)
        body: dict[str, str] = {
            # If we requested `database` but ended up on inmemory-fallback we
            # advertise "degraded" so monitoring can alert without making the
            # endpoint return 5xx (which would also fail liveness probes).
            "status": "degraded" if backend_name == "inmemory-fallback" else "ok",
            "storage_backend": backend_name,
            "ai_provider": runtime_settings.ai_provider,
            "ai_model": runtime_settings.anthropic_model
            if runtime_settings.ai_provider == "anthropic"
            else "",
            "llm_thinking_type": runtime_settings.llm_thinking_type,
        }
        if fallback_reason:
            body["storage_backend_fallback_reason"] = fallback_reason
        return body

    @app.get("/readyz", tags=["system"])
    async def readyz() -> Response:
        import json as _json

        import redis.asyncio as redis_asyncio

        checks: dict[str, str] = {}
        overall_ok = True

        # DB / repository check.
        repo = app.state.repository
        try:
            sql_sessions = getattr(repo, "_sessions", None)
            if sql_sessions is not None:
                from sqlalchemy import text as _text

                async with sql_sessions() as session:
                    await session.execute(_text("SELECT 1"))
                checks["db"] = "ok"
            else:
                # In-memory: seed presence is the best proxy for readiness.
                seed_ok = bool(getattr(repo, "_seed", None))
                checks["db"] = "ok" if seed_ok else "degraded"
                overall_ok = overall_ok and seed_ok
        except Exception as exc:  # noqa: BLE001 - readyz is a diagnostic endpoint
            checks["db"] = f"error: {exc}"
            overall_ok = False

        # Redis check (optional — if configured).
        if app.state.settings.redis_url:
            try:
                client = redis_asyncio.from_url(  # type: ignore[no-untyped-call]
                    app.state.settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                try:
                    await client.ping()
                    checks["redis"] = "ok"
                finally:
                    await client.close()
            except Exception as exc:  # noqa: BLE001 - readyz is a diagnostic endpoint
                checks["redis"] = f"error: {exc}"
                overall_ok = False

        body = _json.dumps(
            {"status": "ready" if overall_ok else "degraded", "checks": checks}
        )
        return Response(
            content=body,
            media_type="application/json",
            status_code=200 if overall_ok else 503,
        )

    return app


app = create_app()
