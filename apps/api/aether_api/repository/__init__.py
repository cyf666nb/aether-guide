# SCORE-IMPACT: Clean storage abstraction for swappable inmemory/SQL backends.
"""Repository Protocol and factory.

Two implementations satisfy the same interface:
- InMemoryRepository: demo path, zero-dep, loaded from seed JSON at startup.
- SqlRepository: production path, backed by SQLAlchemy async.

The active implementation is chosen by settings.storage_mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from aether_api.config import Settings
from aether_api.schemas.admin import (
    AuditLogDTO,
    AuditLogPage,
    DashboardOverviewDTO,
    DocumentDTO,
    IndexProgressDTO,
    PersonaDTO,
    PromptExperimentDTO,
    SessionReplayDTO,
    TurnLabelDTO,
)
from aether_api.schemas.feedback import FeedbackDTO, FeedbackRequest
from aether_api.schemas.landmarks import LandmarkDTO
from aether_api.schemas.sessions import SessionDTO


@dataclass(slots=True, frozen=True)
class AdminRecord:
    """Internal admin row — not exposed through the public API."""

    id: str
    name: str
    email: str
    role: str
    password_hash: str


class Repository(Protocol):
    """Storage-agnostic interface. Both backends must implement every method."""

    async def load_seed(self) -> None:
        """Populate the repository from the seed JSON / tables on startup."""
        ...

    async def create_session(
        self,
        *,
        scenic_id: str,
        user_id: str | None,
        persona_id: str | None,
    ) -> SessionDTO: ...

    async def get_session(self, session_id: str) -> SessionDTO: ...

    async def list_landmarks(self, scenic_id: str) -> list[LandmarkDTO]: ...

    async def nearest_emergency_points(self, scenic_id: str) -> list[LandmarkDTO]: ...

    async def save_feedback(self, request: FeedbackRequest) -> FeedbackDTO: ...

    async def create_document(
        self,
        *,
        scenic_id: str,
        title: str,
        source_uri: str,
        version: str,
    ) -> DocumentDTO: ...

    async def document_progress(self, document_id: str) -> IndexProgressDTO: ...

    async def upsert_persona(
        self,
        *,
        scenic_id: str,
        name: str,
        voice_id: str,
        avatar_id: str,
        system_prompt: str,
        version: str,
        status: str,
    ) -> PersonaDTO: ...

    async def create_prompt_experiment(
        self,
        *,
        name: str,
        variant_a: str,
        variant_b: str,
        traffic_split: float,
        metric: str,
    ) -> PromptExperimentDTO: ...

    async def dashboard_overview(self) -> DashboardOverviewDTO: ...

    async def session_replay(self, session_id: str) -> SessionReplayDTO: ...

    async def label_turn(self, turn_id: str) -> TurnLabelDTO: ...

    async def seed_path(self) -> Path: ...

    # -- auth --
    async def find_admin_by_email(self, email: str) -> AdminRecord | None: ...

    async def upsert_admin(
        self,
        *,
        admin_id: str,
        name: str,
        email: str,
        password_hash: str,
        role: str,
    ) -> AdminRecord: ...

    # -- trail --
    async def clear_user_trail(self, *, user_id: str, scenic_id: str) -> int: ...

    # -- audit --
    async def insert_audit_log(
        self,
        *,
        admin_id: str | None,
        action: str,
        target: str,
        before: dict[str, object] | None,
        after: dict[str, object] | None,
    ) -> AuditLogDTO: ...

    async def list_audit_logs(
        self,
        *,
        limit: int,
        cursor: str | None,
    ) -> AuditLogPage: ...


async def create_repository(settings: Settings) -> Repository:
    """Factory: pick the backend implementation by settings.storage_mode.

    - inmemory: instantiate InMemoryRepository, load seed, return.
    - database: build async engine + session factory, instantiate SqlRepository,
      idempotently seed, and return.
    """
    if settings.storage_mode == "inmemory":
        from aether_api.repository.inmemory import InMemoryRepository

        repo: Repository = InMemoryRepository(settings)
        await repo.load_seed()
        return repo

    if settings.storage_mode == "database":
        from aether_api.repository.sql import make_sql_repository

        sql_repo = make_sql_repository(settings)
        await sql_repo.load_seed()
        return sql_repo

    raise ValueError(f"Unknown storage_mode: {settings.storage_mode}")


__all__ = ["AdminRecord", "Repository", "create_repository"]
