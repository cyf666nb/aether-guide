# Aether Guide

> 景区智慧导览 AI 数字人 MVP — 静态游客页 -> FastAPI -> LLM -> 统一响应 -> Trace -> OpenAPI

## Tech Stack

| Layer | Stack |
|-------|-------|
| Frontend | Next.js 15 + React 19 + Tailwind CSS 4 + TanStack Query |
| Backend | FastAPI + Pydantic v2 + SQLAlchemy (async) + Alembic |
| AI | LiteLLM (pluggable) / Fake echo (dev) |
| Infra | PostgreSQL (pgvector) + Redis + MinIO + LiveKit |
| Observability | Prometheus + Grafana + Loki + Tempo |
| Package | uv (Python) + npm workspaces (Node) |

## Project Structure

```
aether-guide/
├── apps/
│   ├── api/                  # FastAPI backend
│   │   ├── aether_api/
│   │   │   ├── auth/         # JWT + bcrypt + anonymous login
│   │   │   ├── middleware/   # CORS, rate limit, audit, trace
│   │   │   ├── models/       # SQLAlchemy ORM models
│   │   │   ├── repository/   # In-memory / SQL storage backends
│   │   │   ├── routers/      # API endpoints (tourist, admin, auth, safety...)
│   │   │   ├── schemas/      # Pydantic request/response schemas
│   │   │   ├── services/     # AI, RAG, location, voice, safety
│   │   │   └── worker/       # Background task config
│   │   ├── alembic/          # Database migrations
│   │   └── tests/
│   ├── web-tourist/          # Tourist-facing SPA (port 3001)
│   └── web-admin/            # Admin dashboard (port 3002)
├── packages/
│   └── design-system/        # Shared UI components & styles
├── infra/
│   ├── docker-compose.yml    # Postgres, Redis, MinIO, LiveKit, Grafana stack
│   └── seed/                 # Demo scenic data + admin accounts
├── docs/
│   ├── api/openapi.yaml      # Auto-generated OpenAPI spec
│   ├── design/               # Frontend visual spec
│   └── decisions/            # Architecture Decision Records
├── scripts/                  # Dev, test, eval, perf scripts
└── tests/                    # E2E, eval, perf tests
```

## Quick Start

### Prerequisites

- **Python 3.12** + [uv](https://docs.astral.sh/uv/)
- **Node.js 20+** + npm
- (Optional) **Docker** — for Postgres, Redis, etc.

### Backend

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\demo.ps1
```

Unix-like:

```bash
make demo
```

API runs at http://localhost:8000. By default uses `fake` AI provider and `inmemory` storage — no external dependencies needed.

### Frontend

```powershell
cmd /c npm install
cmd /c npm run web:dev:tourist   # -> http://localhost:3001
cmd /c npm run web:dev:admin     # -> http://localhost:3002
```

Override API base URL:

```powershell
$env:NEXT_PUBLIC_API_BASE = "http://your-api:8000"
```

## Configuration

All settings are prefixed with `AETHER_` and can be set via environment variables or `.env` file. See [`.env.example`](.env.example) for the full list.

| Variable | Default | Description |
|----------|---------|-------------|
| `AETHER_STORAGE_MODE` | `inmemory` | `inmemory` or `database` |
| `AETHER_AI_PROVIDER` | `fake` | `fake` (echo) or `litellm` |
| `AETHER_DATABASE_URL` | `sqlite+aiosqlite:///...` | Async DB connection string |
| `AETHER_REDIS_URL` | `redis://localhost:6379/0` | Redis for rate limiting |
| `AETHER_JWT_SECRET` | `dev-only-secret-...` | **Must override in production** |
| `AETHER_CORS_ORIGINS` | `*` | Comma-separated allowed origins |

## Verify

```powershell
# Backend tests
powershell -ExecutionPolicy Bypass -File scripts\test.ps1

# Frontend checks
cmd /c npm run web:lint
cmd /c npm run web:typecheck
cmd /c npm run web:build
```

## API Endpoints

```
POST   /api/v1/auth/anonymous       # Tourist anonymous login
POST   /admin/v1/auth/login          # Admin login (username + password)
POST   /api/v1/sessions              # Create chat session
POST   /api/v1/chat                   # Send message (SSE streaming)
GET    /api/v1/landmarks              # List landmarks
GET    /api/v1/safety/alerts          # Safety alerts
POST   /api/v1/safety/lost            # Report lost person
GET    /admin/v1/summary              # Dashboard summary
GET    /admin/v1/audit                # Audit logs
```

Full spec: [`docs/api/openapi.yaml`](docs/api/openapi.yaml)

## License

Private — not for distribution.
