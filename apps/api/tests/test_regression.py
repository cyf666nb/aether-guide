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
async def test_lifespan_database_mode_not_yet_wired() -> None:
    # Regression guard for Issue #2 — database path is declared but Task 4 owns impl.
    from aether_api.config import Settings
    from aether_api.repository import create_repository

    settings = Settings(storage_mode="database")
    with pytest.raises(NotImplementedError) as exc_info:
        await create_repository(settings)
    assert "Task 4" in str(exc_info.value)
