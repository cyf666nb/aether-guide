# SCORE-IMPACT: Pin Repository contract so refactors can't quietly break demo.
"""Unit tests for InMemoryRepository — the demo backend.

We test through the public Repository protocol so the same suite can later
be parametrized over the SQL backend (see ``tests/unit/test_sql_repository.py``
once that lands).
"""
from __future__ import annotations

from datetime import datetime

import pytest
from aether_api.config import Settings
from aether_api.errors import AppError, ErrorCode
from aether_api.repository.inmemory import InMemoryRepository
from aether_api.schemas.feedback import FeedbackRequest


async def _seeded_repo() -> InMemoryRepository:
    repo = InMemoryRepository(Settings())
    await repo.load_seed()
    return repo


# --- sessions ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_session_returns_active_session_with_default_persona() -> None:
    repo = await _seeded_repo()

    session = await repo.create_session(
        scenic_id="demo-scenic", user_id=None, persona_id=None
    )

    assert session.scenic_id == "demo-scenic"
    # Default persona comes from seed.
    assert session.persona_id == "persona-demo"
    assert session.user_id is None
    assert session.status.value == "active"
    assert isinstance(session.started_at, datetime)


@pytest.mark.asyncio
async def test_create_session_unknown_scenic_id_raises_404() -> None:
    repo = await _seeded_repo()

    with pytest.raises(AppError) as exc:
        await repo.create_session(
            scenic_id="nonexistent", user_id=None, persona_id=None
        )

    assert exc.value.status_code == 404
    assert exc.value.code == ErrorCode.not_found


@pytest.mark.asyncio
async def test_get_session_round_trips_created_id() -> None:
    repo = await _seeded_repo()
    created = await repo.create_session(
        scenic_id="demo-scenic", user_id="u-1", persona_id=None
    )

    fetched = await repo.get_session(created.id)

    assert fetched.id == created.id
    assert fetched.user_id == "u-1"


@pytest.mark.asyncio
async def test_get_session_unknown_id_raises_404() -> None:
    repo = await _seeded_repo()

    with pytest.raises(AppError) as exc:
        await repo.get_session("does-not-exist")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_session_with_explicit_persona_overrides_default() -> None:
    repo = await _seeded_repo()

    session = await repo.create_session(
        scenic_id="demo-scenic", user_id=None, persona_id="persona-custom"
    )

    assert session.persona_id == "persona-custom"


# --- landmarks --------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_landmarks_returns_seed_data() -> None:
    repo = await _seeded_repo()

    landmarks = await repo.list_landmarks("demo-scenic")

    assert len(landmarks) > 0
    # Seeded landmarks all live in the demo scenic area.
    assert all(lm.scenic_id == "demo-scenic" for lm in landmarks)


@pytest.mark.asyncio
async def test_list_landmarks_unknown_scenic_raises_404() -> None:
    repo = await _seeded_repo()

    with pytest.raises(AppError) as exc:
        await repo.list_landmarks("nonexistent")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_nearest_emergency_points_caps_at_three() -> None:
    repo = await _seeded_repo()

    points = await repo.nearest_emergency_points("demo-scenic")

    # Always returns ≤3 entries (and falls back to first 3 landmarks if no
    # explicit emergency_nearby flags exist in the seed).
    assert 0 < len(points) <= 3


# --- feedback ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_feedback_requires_existing_session() -> None:
    repo = await _seeded_repo()

    request = FeedbackRequest(session_id="ghost-session", rating=5, comment="nice")
    with pytest.raises(AppError) as exc:
        await repo.save_feedback(request)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_save_feedback_marks_accepted() -> None:
    repo = await _seeded_repo()
    session = await repo.create_session(
        scenic_id="demo-scenic", user_id=None, persona_id=None
    )

    feedback = await repo.save_feedback(
        FeedbackRequest(session_id=session.id, rating=4, comment="ok")
    )

    assert feedback.session_id == session.id
    assert feedback.accepted is True
    assert feedback.id  # uuid hex


# --- admins -----------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_lookup_is_case_insensitive() -> None:
    repo = await _seeded_repo()

    await repo.upsert_admin(
        admin_id="a-1",
        name="Ops",
        email="Ops@Example.COM",
        password_hash="hash",
        role="admin",
    )

    record = await repo.find_admin_by_email("ops@example.com")
    assert record is not None
    assert record.id == "a-1"
    assert record.email == "ops@example.com"  # stored normalized


@pytest.mark.asyncio
async def test_upsert_admin_overwrites_existing_email() -> None:
    repo = await _seeded_repo()
    await repo.upsert_admin(
        admin_id="a-1", name="A", email="x@y.com", password_hash="h1", role="admin"
    )
    await repo.upsert_admin(
        admin_id="a-2", name="B", email="x@y.com", password_hash="h2", role="ops"
    )

    record = await repo.find_admin_by_email("x@y.com")
    assert record is not None
    assert record.id == "a-2"
    assert record.role == "ops"


# --- audit log pagination ---------------------------------------------------

@pytest.mark.asyncio
async def test_list_audit_logs_paginates_with_cursor() -> None:
    repo = await _seeded_repo()
    for i in range(5):
        await repo.insert_audit_log(
            admin_id="a-1",
            action=f"act-{i}",
            target=f"t-{i}",
            before=None,
            after={"i": i},
        )

    page1 = await repo.list_audit_logs(limit=2, cursor=None)
    assert len(page1.items) == 2
    assert page1.next_cursor is not None

    page2 = await repo.list_audit_logs(limit=2, cursor=page1.next_cursor)
    assert len(page2.items) == 2
    # Pages must not overlap.
    page1_ids = {entry.id for entry in page1.items}
    page2_ids = {entry.id for entry in page2.items}
    assert page1_ids.isdisjoint(page2_ids)

    page3 = await repo.list_audit_logs(limit=2, cursor=page2.next_cursor)
    # Last page either fits in one and stops, or has the trailing item with
    # no further cursor.
    assert page3.next_cursor is None


@pytest.mark.asyncio
async def test_list_audit_logs_empty_returns_no_cursor() -> None:
    repo = await _seeded_repo()

    page = await repo.list_audit_logs(limit=10, cursor=None)

    assert page.items == []
    assert page.next_cursor is None
