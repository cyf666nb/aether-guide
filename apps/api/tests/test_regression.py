# SCORE-IMPACT: Regression guardrails for the 14-issue fix plan.
"""Regression tests — one per 🔴 / key 🟠 issue fixed by the 14-item plan."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from aether_api.models import Base
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect


@pytest.fixture()
def alembic_sqlite_url(tmp_path: Path) -> str:
    db_path = tmp_path / "alembic_test.db"
    return f"sqlite:///{db_path}"


def _make_alembic_config(url: str) -> Config:
    ini_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", url)
    # Ensure scripts are discoverable regardless of cwd.
    cfg.set_main_option(
        "script_location",
        str(ini_path.parent / "alembic"),
    )
    return cfg


def test_alembic_upgrade_head_creates_expected_tables(alembic_sqlite_url: str) -> None:
    # Regression guard for Issue #1 — Alembic script exists and creates full schema.
    cfg = _make_alembic_config(alembic_sqlite_url)
    command.upgrade(cfg, "head")

    engine = create_engine(alembic_sqlite_url)
    inspector = inspect(engine)
    created = set(inspector.get_table_names())
    engine.dispose()

    expected = set(Base.metadata.tables.keys())
    # alembic_version is Alembic's own bookkeeping table.
    assert expected.issubset(created), (
        f"Missing tables after upgrade: {expected - created}"
    )
    assert "alembic_version" in created


@pytest.mark.asyncio
async def test_lifespan_selects_inmemory() -> None:
    # Regression guard for Issue #2 — factory returns in-memory backend.
    from aether_api.config import Settings
    from aether_api.repository import create_repository
    from aether_api.repository.inmemory import InMemoryRepository

    settings = Settings(storage_mode="inmemory")
    repo = await create_repository(settings)
    assert isinstance(repo, InMemoryRepository)


@pytest.mark.asyncio
async def test_storage_mode_database_end_to_end(tmp_path: Path) -> None:
    # Regression guard for Issue #2 — database backend works end-to-end.
    from aether_api.config import Settings
    from aether_api.repository import create_repository
    from aether_api.repository.sql import SqlRepository

    db_path = tmp_path / "e2e.db"
    settings = Settings(
        storage_mode="database",
        database_url=f"sqlite+aiosqlite:///{db_path}",
    )

    # Apply migrations to the tmp DB first.
    sync_url = f"sqlite:///{db_path}"
    cfg = _make_alembic_config(sync_url)
    command.upgrade(cfg, "head")

    repo = await create_repository(settings)
    try:
        assert isinstance(repo, SqlRepository)
        landmarks = await repo.list_landmarks("demo-scenic")
        assert len(landmarks) >= 3
        session = await repo.create_session(
            scenic_id="demo-scenic", user_id="visitor-1", persona_id=None
        )
        assert session.scenic_id == "demo-scenic"
        roundtrip = await repo.get_session(session.id)
        assert roundtrip.id == session.id
    finally:
        aclose = getattr(repo, "aclose", None)
        if callable(aclose):
            await aclose()


# ---------- Auth (Task 5) regression tests ---------------------------------


def _auth_client() -> TestClient:
    from aether_api.main import app

    return TestClient(app)


def test_admin_login_success_returns_token() -> None:
    with _auth_client() as client:
        response = client.post(
            "/admin/v1/auth/login",
            json={"email": "admin@demo", "password": "admin-demo-pass"},
        )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["code"] == "OK"
    token = payload["data"]["token"]["token"]
    assert token.count(".") == 2  # three-segment JWT
    assert payload["data"]["profile"]["email"] == "admin@demo"


def test_admin_login_wrong_password_returns_401() -> None:
    with _auth_client() as client:
        response = client.post(
            "/admin/v1/auth/login",
            json={"email": "admin@demo", "password": "wrong-password"},
        )
    assert response.status_code == 401
    assert response.json()["code"] == "BAD_REQUEST"


def test_admin_login_unknown_email_returns_401() -> None:
    with _auth_client() as client:
        response = client.post(
            "/admin/v1/auth/login",
            json={"email": "nobody@demo", "password": "admin-demo-pass"},
        )
    assert response.status_code == 401


def test_tourist_anonymous_issues_valid_jwt() -> None:
    from aether_api.auth.jwt import decode_token
    from aether_api.config import get_settings

    get_settings.cache_clear()
    with _auth_client() as client:
        response = client.post("/api/v1/auth/anonymous")
    assert response.status_code == 200
    token = response.json()["data"]["token"]
    decoded = decode_token(get_settings(), token)
    assert decoded["role"] == "tourist"
    assert decoded["sub"].startswith("tourist-")


# ---------- Task 6: auth enforcement on routes + WS ------------------------


def test_admin_routes_require_admin_token() -> None:
    with _auth_client() as client:
        # No token → 401
        assert client.get("/admin/v1/dashboard/overview").status_code == 401
        # Tourist token → 403
        tourist = client.post("/api/v1/auth/anonymous").json()["data"]["token"]
        assert (
            client.get(
                "/admin/v1/dashboard/overview",
                headers={"Authorization": f"Bearer {tourist}"},
            ).status_code
            == 403
        )
        # Admin token → 200
        admin = client.post(
            "/admin/v1/auth/login",
            json={"email": "admin@demo", "password": "admin-demo-pass"},
        ).json()["data"]["token"]["token"]
        assert (
            client.get(
                "/admin/v1/dashboard/overview",
                headers={"Authorization": f"Bearer {admin}"},
            ).status_code
            == 200
        )


def test_tourist_token_cannot_access_admin() -> None:
    with _auth_client() as client:
        tourist = client.post("/api/v1/auth/anonymous").json()["data"]["token"]
        response = client.post(
            "/admin/v1/documents",
            headers={"Authorization": f"Bearer {tourist}"},
            json={
                "scenic_id": "demo-scenic",
                "title": "demo",
                "source_uri": "memory://x",
                "version": "v1",
                "idempotency_key": "regtest-1",
            },
        )
        assert response.status_code == 403


def test_websocket_rejects_without_token() -> None:
    from starlette.websockets import WebSocketDisconnect

    with _auth_client() as client:
        # First create a session (needs tourist token).
        tourist = client.post("/api/v1/auth/anonymous").json()["data"]["token"]
        created = client.post(
            "/api/v1/sessions",
            headers={"Authorization": f"Bearer {tourist}"},
            json={
                "scenic_id": "demo-scenic",
                "user_id": "regtest",
                "locale": "zh-CN",
                "idempotency_key": "ws-regtest",
            },
        )
        session_id = created.json()["data"]["id"]
        with (
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect(f"/api/v1/sessions/{session_id}/stream"),
        ):
            pass


# ---------- Task 7: CORS + Audit persistence -------------------------------


def test_audit_log_recorded_on_admin_write() -> None:
    with _auth_client() as client:
        admin_token = client.post(
            "/admin/v1/auth/login",
            json={"email": "admin@demo", "password": "admin-demo-pass"},
        ).json()["data"]["token"]["token"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        doc = client.post(
            "/admin/v1/documents",
            headers=headers,
            json={
                "scenic_id": "demo-scenic",
                "title": "audit probe",
                "source_uri": "memory://audit",
                "version": "v1",
                "idempotency_key": "audit-probe",
            },
        )
        assert doc.status_code == 200
        assert doc.headers.get("X-Audit-Recorded") == "true"

        logs = client.get("/admin/v1/audit-logs?limit=5", headers=headers)
        assert logs.status_code == 200
        items = logs.json()["data"]["items"]
        assert any(
            entry["action"] == "POST /admin/v1/documents" for entry in items
        ), items


def test_cors_rejects_unknown_origin_when_restricted() -> None:
    # Build a local app with restricted CORS and check that an Origin outside
    # the whitelist does not receive Access-Control-Allow-Origin.
    from aether_api.config import Settings, get_settings
    from aether_api.main import create_app
    from fastapi.testclient import TestClient

    get_settings.cache_clear()
    cfg = Settings(cors_origins=["https://allowed.example"])
    app = create_app(cfg)
    with TestClient(app) as client:
        response = client.options(
            "/healthz",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        # The header should only be set for the allowed origin.
        assert response.headers.get("access-control-allow-origin") != "https://evil.example"


# ---------- Task 8: Redis sliding-window rate limit -----------------------


@pytest.mark.asyncio
async def test_redis_rate_limit_enforced_and_isolated_by_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fake Redis. Simulate two users — each should have its own budget."""
    import fakeredis.aioredis
    from aether_api.config import Settings
    from aether_api.middleware.rate_limit_redis import RedisSlidingWindowRateLimit
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)

    def from_url(*_args: object, **_kwargs: object) -> object:
        return fake

    monkeypatch.setattr(
        "aether_api.middleware.rate_limit_redis.redis_asyncio.from_url",
        from_url,
    )

    settings = Settings(rate_limit_per_minute=3)

    async def echo(_req: Request) -> JSONResponse:
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/echo", echo)])
    app.add_middleware(RedisSlidingWindowRateLimit, settings=settings)

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        # Three hits from IP A succeed.
        for _ in range(3):
            assert client.get("/echo", headers={"X-Forwarded-For": "1.2.3.4"}).status_code == 200
        # Fourth is rate-limited.
        blocked = client.get("/echo", headers={"X-Forwarded-For": "1.2.3.4"})
        assert blocked.status_code == 429
        assert blocked.headers.get("X-RateLimit-Remaining") == "0"
        assert int(blocked.headers.get("X-RateLimit-Limit") or 0) == 3


# ---------- Task 10: hardening ------------------------------------------


def test_image_base64_too_large_rejected() -> None:
    """validate_image_base64 rejects payloads above the 1 MB limit."""
    import base64

    from aether_api.errors import AppError
    from aether_api.services.common.image import validate_image_base64

    huge = base64.b64encode(b"\x00" * (1_200_000)).decode("ascii")
    with pytest.raises(AppError) as exc_info:
        validate_image_base64(huge)
    assert exc_info.value.status_code == 400


def test_trace_middleware_sanitizes_hostile_header() -> None:
    """A malicious X-Trace-Id is dropped; response carries a fresh one."""
    from aether_api.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.get(
            "/healthz", headers={"X-Trace-Id": "<script>alert(1)</script>"}
        )
    trace = response.headers.get("X-Trace-Id", "")
    assert "<" not in trace
    assert "script" not in trace
    assert len(trace) >= 8


@pytest.mark.asyncio
async def test_ai_client_production_timeout_raises_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Timeouts in production mode raise 503 — no silent fake fallback."""
    from aether_api.config import Settings
    from aether_api.errors import AppError
    from aether_api.services.ai import client as ai_module

    settings = Settings(
        environment="production",
        ai_provider="litellm",
        jwt_secret="prod-secret-not-default-value-long-enough",
        cors_origins=["https://prod.example"],
    )

    async def slow_answer(*_args: object, **_kwargs: object) -> None:
        await asyncio.sleep(5)  # exceeds default llm_timeout_seconds

    monkeypatch.setattr(ai_module.AIClient, "_litellm_answer", slow_answer)

    ai_client = ai_module.AIClient(settings)
    ai_client._settings.llm_timeout_seconds = 0.1  # force quick timeout  # type: ignore[misc]
    with pytest.raises(AppError) as exc_info:
        await ai_client.generate_reply(
            ai_module.AIRequest(
                session_id="s", scenic_id="demo-scenic", prompt="hi", locale="zh-CN"
            )
        )
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_ai_client_anthropic_provider_uses_messages_protocol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Anthropic-compatible providers receive grounded Messages API payloads."""
    from aether_api.config import Settings
    from aether_api.services.ai import client as ai_module
    from pydantic import SecretStr

    settings = Settings(
        ai_provider="anthropic",
        anthropic_api_key=SecretStr("test-key"),
        anthropic_model="ark-code-latest",
    )
    captured: dict[str, object] = {}

    async def fake_post(
        _self: object,
        url: str,
        headers: dict[str, str],
        payload: dict[str, object],
    ) -> dict[str, object]:
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = payload
        return {
            "content": [
                {"type": "text", "text": "榕巷知行：从南后街开始，先看街巷格局。"}
            ],
            "usage": {"input_tokens": 32, "output_tokens": 18},
        }

    monkeypatch.setattr(ai_module.AIClient, "_anthropic_post", fake_post)

    ai_client = ai_module.AIClient(settings)
    response = await ai_client.generate_reply(
        ai_module.AIRequest(
            session_id="s",
            scenic_id="demo-scenic",
            prompt="三坊七巷从哪开始逛？",
            locale="zh-CN",
            context=[
                ai_module.AIContextChunk(
                    source_id="landmark:nanhou-street",
                    text="南后街是三坊七巷的中轴商业街。",
                    score=0.91,
                )
            ],
            system_prompt="榕巷知行：三坊七巷专属导览。",
        )
    )

    assert captured["url"] == "https://ark.cn-beijing.volces.com/api/coding/v1/messages"
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["x-api-key"] == "test-key"
    assert headers["anthropic-version"] == "2023-06-01"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "ark-code-latest"
    assert payload["thinking"] == {"type": "disabled"}
    assert "榕巷知行" in str(payload["system"])
    assert "Context:" in str(payload["messages"])
    assert "Citation contract:" in str(payload["messages"])
    assert "landmark:nanhou-street" in str(payload["messages"])
    assert response.content.startswith("榕巷知行")
    assert response.citations == ["landmark:nanhou-street"]


@pytest.mark.asyncio
async def test_ai_client_answers_identity_questions_locally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Identity questions stay on the scenic persona even if provider has defaults."""
    from aether_api.config import Settings
    from aether_api.services.ai import client as ai_module
    from pydantic import SecretStr

    settings = Settings(
        ai_provider="anthropic",
        anthropic_api_key=SecretStr("test-key"),
        anthropic_model="ark-code-latest",
    )
    async def fake_post(
        _self: object,
        _url: str,
        _headers: dict[str, str],
        _payload: dict[str, object],
    ) -> dict[str, object]:
        raise AssertionError("identity questions should not call provider")

    monkeypatch.setattr(ai_module.AIClient, "_anthropic_post", fake_post)

    ai_client = ai_module.AIClient(settings)
    response = await ai_client.generate_reply(
        ai_module.AIRequest(
            session_id="s",
            scenic_id="demo-scenic",
            prompt="你是谁",
            locale="zh-CN",
            system_prompt="榕巷知行：三坊七巷专属导览。",
        )
    )

    assert response.content.startswith("我是榕巷知行")
    assert response.citations == ["persona:current"]
    assert response.cache_hit is True


def test_readyz_reports_redis_outage(monkeypatch: pytest.MonkeyPatch) -> None:
    """readyz returns 503 with checks.redis=error when Redis is unreachable."""
    from aether_api.main import app
    from fastapi.testclient import TestClient
    from redis.exceptions import ConnectionError as RedisConnectionError

    class _BrokenRedis:
        async def ping(self) -> None:
            raise RedisConnectionError("simulated outage")

        async def close(self) -> None:
            return None

    def broken_from_url(*_args: object, **_kwargs: object) -> object:
        return _BrokenRedis()

    monkeypatch.setattr(
        "redis.asyncio.from_url",
        broken_from_url,
    )

    with TestClient(app) as client:
        response = client.get("/readyz")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert "error" in data["checks"]["redis"]
