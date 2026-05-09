# SCORE-IMPACT: Regression guardrails for the 14-issue fix plan.
"""Regression tests — one per 🔴 / key 🟠 issue fixed by the 14-item plan."""

from __future__ import annotations

from pathlib import Path

import pytest
from aether_api.models import Base
from alembic import command
from alembic.config import Config
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
