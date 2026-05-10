UV_CACHE_DIR ?= $(CURDIR)/.uv-cache
UV_PYTHON_INSTALL_DIR ?= $(CURDIR)/.uv-python
UV := UV_CACHE_DIR=$(UV_CACHE_DIR) UV_PYTHON_INSTALL_DIR=$(UV_PYTHON_INSTALL_DIR) uv

.PHONY: dev demo migrate test eval perf openapi start

start:
	bash start.sh

dev:
	$(UV) run --project apps/api uvicorn aether_api.main:app --host 0.0.0.0 --port 8000 --reload

demo:
	$(UV) run --project apps/api uvicorn aether_api.main:app --host 0.0.0.0 --port 8000

migrate:
	cd apps/api && $(UV) run alembic upgrade head

test:
	$(UV) run --project apps/api ruff check apps/api/aether_api apps/api/tests tests/eval scripts
	$(UV) run --project apps/api mypy apps/api/aether_api
	$(UV) run --project apps/api pytest apps/api/tests

eval:
	$(UV) run --project apps/api python tests/eval/rag_eval.py

perf:
	k6 run tests/perf/k6-smoke.js

openapi:
	$(UV) run --project apps/api python scripts/export_openapi.py
