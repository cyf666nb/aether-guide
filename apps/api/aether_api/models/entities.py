# SCORE-IMPACT: Enterprise schema coverage for RAG, sessions, safety, and admin.
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aether_api.models.base import Base, TimestampMixin


class ScenicArea(TimestampMixin, Base):
    __tablename__ = "scenic_areas"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    geo_polygon: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    default_persona_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    atmosphere: Mapped[str] = mapped_column(String(40), default="forest")


class Persona(TimestampMixin, Base):
    __tablename__ = "personas"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenic_id: Mapped[str] = mapped_column(ForeignKey("scenic_areas.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    voice_id: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_id: Mapped[str] = mapped_column(String(120), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenic_id: Mapped[str] = mapped_column(ForeignKey("scenic_areas.id"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    source_uri: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document")


class Chunk(TimestampMixin, Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    doc_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    ord: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    sparse_vector: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_metadata: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    document: Mapped[Document] = relationship(back_populates="chunks")


class Landmark(TimestampMixin, Base):
    __tablename__ = "landmarks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenic_id: Mapped[str] = mapped_column(ForeignKey("scenic_areas.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    opening_hours: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    avg_duration_min: Mapped[int] = mapped_column(Integer, default=10)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    qr_token: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    visual_features: Mapped[str | None] = mapped_column(Text, nullable=True)
    visual_embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    reference_photos: Mapped[list[str]] = mapped_column(JSON, default=list)
    emergency_nearby: Mapped[list[str]] = mapped_column(JSON, default=list)
    audio_cache_uri: Mapped[str | None] = mapped_column(Text, nullable=True)


class LandmarkEdge(TimestampMixin, Base):
    __tablename__ = "landmark_edges"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    from_id: Mapped[str] = mapped_column(ForeignKey("landmarks.id"), index=True)
    to_id: Mapped[str] = mapped_column(ForeignKey("landmarks.id"), index=True)
    walk_minutes: Mapped[int] = mapped_column(Integer, nullable=False)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    openid: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(120), nullable=True)
    interest_vec: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    location_consent: Mapped[str] = mapped_column(String(40), default="approximate")


class Session(TimestampMixin, Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    scenic_id: Mapped[str] = mapped_column(ForeignKey("scenic_areas.id"), index=True)
    persona_id: Mapped[str | None] = mapped_column(ForeignKey("personas.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    satisfaction: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Turn(TimestampMixin, Base):
    __tablename__ = "turns"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    ord: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    audio_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    asr_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tts_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retrieved_chunks: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)


class UserTrail(TimestampMixin, Base):
    __tablename__ = "user_trails"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    scenic_id: Mapped[str] = mapped_column(ForeignKey("scenic_areas.id"), index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Admin(TimestampMixin, Base):
    __tablename__ = "admins"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(240), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, default="")


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    admin_id: Mapped[str | None] = mapped_column(ForeignKey("admins.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    target: Mapped[str] = mapped_column(String(200), nullable=False)
    before: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PromptExperiment(TimestampMixin, Base):
    __tablename__ = "prompt_experiments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    variant_a: Mapped[str] = mapped_column(Text, nullable=False)
    variant_b: Mapped[str] = mapped_column(Text, nullable=False)
    traffic_split: Mapped[float] = mapped_column(Float, default=0.5)
    metric: Mapped[str] = mapped_column(String(80), nullable=False)
    winner: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
