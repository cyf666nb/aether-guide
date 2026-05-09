# Local Development Runbook

## Windows

```powershell
powershell -ExecutionPolicy Bypass -File scripts\demo.ps1
```

## Health Checks

- API: `GET http://localhost:8000/healthz`
- Tourist UI: `http://localhost:8000`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Modes

- `AETHER_AI_PROVIDER=fake`: deterministic echo response.
- `AETHER_STORAGE_MODE=inmemory`: seed-backed demo repository.
- `AETHER_AI_PROVIDER=litellm`: requires installing the `ai` dependency group and configuring provider keys.

