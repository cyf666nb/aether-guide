# SCORE-IMPACT: Guarantee dev/test boots even with a misconfigured database.
"""Unit tests for the create_repository fallback policy.

The factory should:
- never fall back in `production` (data loss risk),
- transparently degrade to inmemory in dev/test if SQL setup fails,
- record the active backend on the returned object so /healthz can surface
  the degradation.
"""
from __future__ import annotations

import pytest

from aether_api.config import Settings
from aether_api.repository import create_repository


@pytest.mark.asyncio
async def test_inmemory_mode_is_unaffected_by_fallback_policy() -> None:
    settings = Settings(storage_mode="inmemory")
    repo = await create_repository(settings)

    assert getattr(repo, "backend_name", None) == "inmemory"
    assert not hasattr(repo, "backend_fallback_reason") or getattr(
        repo, "backend_fallback_reason", None
    ) is None


@pytest.mark.asyncio
async def test_database_mode_falls_back_in_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        storage_mode="database",
        # Driver that doesn't exist anywhere — make_sql_repository will
        # raise on engine creation, exercising the fallback path.
        database_url="postgresql+asyncpg://nope:nope@unreachable.invalid:9999/x",
        environment="development",
    )

    # Force make_sql_repository to fail synchronously so we don't actually
    # hit the network during a unit test. The import inside create_repository
    # is `from aether_api.repository.sql import make_sql_repository`, so the
    # patch target is the source module.
    def _boom(_settings: Settings) -> None:
        raise RuntimeError("simulated driver failure")

    import aether_api.repository.sql as sql_module

    monkeypatch.setattr(sql_module, "make_sql_repository", _boom, raising=True)

    repo = await create_repository(settings)

    assert getattr(repo, "backend_name", None) == "inmemory-fallback"
    reason = getattr(repo, "backend_fallback_reason", None)
    assert reason is not None
    assert "simulated driver failure" in reason


@pytest.mark.asyncio
async def test_database_mode_does_not_fall_back_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pydantic import SecretStr

    # Production guard in Settings rejects wildcard CORS / dev secrets, so
    # provide both explicitly.
    settings = Settings(
        storage_mode="database",
        database_url="postgresql+asyncpg://nope:nope@unreachable.invalid:9999/x",
        environment="production",
        cors_origins=["https://example.com"],
        jwt_secret=SecretStr("not-the-default-secret-please"),
    )

    def _boom(_settings: Settings) -> None:
        raise RuntimeError("simulated driver failure")

    import aether_api.repository.sql as sql_module

    monkeypatch.setattr(sql_module, "make_sql_repository", _boom, raising=True)

    with pytest.raises(RuntimeError, match="simulated driver failure"):
        await create_repository(settings)
