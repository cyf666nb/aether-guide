# ADR-001: Python-first MVP stack

## Status

Accepted.

## Context

The first milestone must create a runnable scenic-area guide loop while keeping room for RAG,
streaming voice, digital-human rendering, observability, and admin workflows.

## Decision

- Use FastAPI for the gateway and API contract.
- Use Pydantic v2 for every public DTO.
- Use SQLAlchemy 2.0 async and Alembic for database readiness.
- Use an in-memory repository for the demo path so the app runs without Docker.
- Keep LiteLLM behind `services/ai/client.py`; default to a fake provider until keys are configured.
- Provide Docker Compose for PostgreSQL + pgvector, Redis, MinIO, LiveKit, and LGTM-adjacent services.

## Consequences

- The demo is runnable on a bare Windows workstation with uv.
- Production integrations remain explicit replacement points instead of scattered stubs.
- Future migrations can introduce pgvector-specific indexes without changing the API surface.

