# SCORE-IMPACT: Demo repeatability, offline operation, and clean data seams.
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from aether_api.config import Settings
from aether_api.errors import AppError, ErrorCode
from aether_api.repository import AdminRecord
from aether_api.schemas.admin import (
    AuditLogDTO,
    AuditLogPage,
    DashboardOverviewDTO,
    DocumentDTO,
    DocumentStatus,
    IndexProgressDTO,
    PersonaDTO,
    PromptExperimentDTO,
    SessionReplayDTO,
    TurnLabelDTO,
)
from aether_api.schemas.common import GeoPoint, TimedMetric
from aether_api.schemas.feedback import FeedbackDTO, FeedbackRequest
from aether_api.schemas.landmarks import LandmarkDTO
from aether_api.schemas.sessions import SessionDTO, SessionStatus


@dataclass(slots=True)
class SeedData:
    scenic_id: str
    default_persona_id: str
    landmarks: list[LandmarkDTO]


class InMemoryRepository:
    """In-process repository used for demos and for tests that need no DB."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._seed: SeedData | None = None
        self._sessions: dict[str, SessionDTO] = {}
        self._documents: dict[str, DocumentDTO] = {}
        self._personas: dict[str, PersonaDTO] = {}
        self._persona_prompts: dict[str, str] = {}
        self._experiments: dict[str, PromptExperimentDTO] = {}
        self._feedback: dict[str, FeedbackDTO] = {}
        self._admins_by_email: dict[str, AdminRecord] = {}
        self._audit_logs: list[AuditLogDTO] = []

    async def load_seed(self) -> None:
        seed_path = self._settings.seed_data_path
        if not seed_path.exists():
            self._seed = SeedData(
                scenic_id="demo-scenic",
                default_persona_id="persona-demo",
                landmarks=[],
            )
            return
        raw_payload = await asyncio.to_thread(seed_path.read_text, encoding="utf-8")
        payload = json.loads(raw_payload)
        landmarks = [
            LandmarkDTO(
                id=item["id"],
                scenic_id=payload["scenic_id"],
                name=item["name"],
                summary=item["summary"],
                geo_point=GeoPoint(**item["geo_point"]),
                tags=item.get("tags", []),
                avg_duration_min=item.get("avg_duration_min", 10),
                audio_cache_uri=item.get("audio_cache_uri"),
                emergency_nearby=item.get("emergency_nearby", []),
            )
            for item in payload.get("landmarks", [])
        ]
        self._seed = SeedData(
            scenic_id=payload["scenic_id"],
            default_persona_id=payload["default_persona_id"],
            landmarks=landmarks,
        )

    def _require_seed(self) -> SeedData:
        if self._seed is None:
            raise AppError(ErrorCode.internal_error, "Seed data was not loaded.", status_code=500)
        return self._seed

    async def create_session(
        self,
        *,
        scenic_id: str,
        user_id: str | None,
        persona_id: str | None,
    ) -> SessionDTO:
        seed = self._require_seed()
        if scenic_id != seed.scenic_id:
            raise AppError(ErrorCode.not_found, "Scenic area was not found.", status_code=404)
        session = SessionDTO(
            id=uuid4().hex,
            user_id=user_id,
            scenic_id=scenic_id,
            persona_id=persona_id or seed.default_persona_id,
            status=SessionStatus.active,
            started_at=datetime.now(UTC),
        )
        self._sessions[session.id] = session
        return session

    async def get_session(self, session_id: str) -> SessionDTO:
        session = self._sessions.get(session_id)
        if session is None:
            raise AppError(ErrorCode.not_found, "Session was not found.", status_code=404)
        return session

    async def list_landmarks(self, scenic_id: str) -> list[LandmarkDTO]:
        seed = self._require_seed()
        if scenic_id != seed.scenic_id:
            raise AppError(ErrorCode.not_found, "Scenic area was not found.", status_code=404)
        return seed.landmarks

    async def nearest_emergency_points(self, scenic_id: str) -> list[LandmarkDTO]:
        landmarks = await self.list_landmarks(scenic_id)
        emergency_landmarks = [landmark for landmark in landmarks if landmark.emergency_nearby]
        return emergency_landmarks[:3] or landmarks[:3]

    async def save_feedback(self, request: FeedbackRequest) -> FeedbackDTO:
        await self.get_session(request.session_id)
        feedback = FeedbackDTO(id=uuid4().hex, session_id=request.session_id, accepted=True)
        self._feedback[feedback.id] = feedback
        return feedback

    async def create_document(
        self,
        *,
        scenic_id: str,
        title: str,
        source_uri: str,
        version: str,
    ) -> DocumentDTO:
        document = DocumentDTO(
            id=uuid4().hex,
            scenic_id=scenic_id,
            title=title,
            source_uri=source_uri,
            version=version,
            status=DocumentStatus.queued,
        )
        self._documents[document.id] = document
        return document

    async def document_progress(self, document_id: str) -> IndexProgressDTO:
        document = self._documents.get(document_id)
        if document is None:
            raise AppError(ErrorCode.not_found, "Document was not found.", status_code=404)
        return IndexProgressDTO(
            document_id=document_id,
            status=document.status,
            percent=10 if document.status == DocumentStatus.queued else 100,
            message="Queued for arq indexing worker.",
        )

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
    ) -> PersonaDTO:
        persona = PersonaDTO(
            id=uuid4().hex,
            scenic_id=scenic_id,
            name=name,
            voice_id=voice_id,
            avatar_id=avatar_id,
            version=version,
            status=status,
        )
        self._personas[persona.id] = persona
        self._persona_prompts[persona.id] = system_prompt
        return persona

    async def create_prompt_experiment(
        self,
        *,
        name: str,
        variant_a: str,
        variant_b: str,
        traffic_split: float,
        metric: str,
    ) -> PromptExperimentDTO:
        experiment = PromptExperimentDTO(
            id=uuid4().hex,
            name=name,
            traffic_split=traffic_split,
            metric=metric,
            status="draft",
        )
        self._experiments[experiment.id] = experiment
        return experiment

    async def dashboard_overview(self) -> DashboardOverviewDTO:
        return DashboardOverviewDTO(
            active_sessions=len(self._sessions),
            token_cost_usd_today=0.0,
            cache_hit_rate=0.0,
            nps=4.6,
            latency=[
                TimedMetric(name="asr", p50_ms=0, p95_ms=0, p99_ms=0),
                TimedMetric(name="llm", p50_ms=42, p95_ms=120, p99_ms=180),
                TimedMetric(name="tts", p50_ms=0, p95_ms=0, p99_ms=0),
            ],
        )

    async def session_replay(self, session_id: str) -> SessionReplayDTO:
        await self.get_session(session_id)
        return SessionReplayDTO(
            session_id=session_id,
            user_waveform_uri=None,
            tts_waveform_uri=None,
            events=[{"at": datetime.now(UTC).isoformat(), "type": "session_created"}],
            retrieved_chunks=["seed:intro"],
        )

    async def label_turn(self, turn_id: str) -> TurnLabelDTO:
        return TurnLabelDTO(turn_id=turn_id, accepted=True)

    async def seed_path(self) -> Path:
        return self._settings.seed_data_path

    # -- auth ----------------------------------------------------------------

    async def find_admin_by_email(self, email: str) -> AdminRecord | None:
        return self._admins_by_email.get(email.lower())

    async def upsert_admin(
        self,
        *,
        admin_id: str,
        name: str,
        email: str,
        password_hash: str,
        role: str,
    ) -> AdminRecord:
        record = AdminRecord(
            id=admin_id,
            name=name,
            email=email.lower(),
            role=role,
            password_hash=password_hash,
        )
        self._admins_by_email[record.email] = record
        return record

    # -- audit ---------------------------------------------------------------

    async def insert_audit_log(
        self,
        *,
        admin_id: str | None,
        action: str,
        target: str,
        before: dict[str, object] | None,
        after: dict[str, object] | None,
    ) -> AuditLogDTO:
        entry = AuditLogDTO(
            id=uuid4().hex,
            admin_id=admin_id,
            action=action,
            target=target,
            at=datetime.now(UTC),
            before=before,
            after=after,
        )
        self._audit_logs.append(entry)
        return entry

    async def list_audit_logs(
        self,
        *,
        limit: int,
        cursor: str | None,
    ) -> AuditLogPage:
        # Newest first. Cursor is the id of the last-seen entry.
        ordered = sorted(self._audit_logs, key=lambda e: e.at, reverse=True)
        if cursor:
            for idx, entry in enumerate(ordered):
                if entry.id == cursor:
                    ordered = ordered[idx + 1 :]
                    break
        page = ordered[:limit]
        next_cursor = page[-1].id if len(page) == limit and len(ordered) > limit else None
        return AuditLogPage(items=page, next_cursor=next_cursor)
