# Aether Guide

景区智慧导览 AI 数字人后端 MVP。当前仓库实现文档第 12 节的第一步闭环：
静态游客页 -> FastAPI -> fake LLM echo -> 统一响应 -> Trace -> OpenAPI。

## Run

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\demo.ps1
```

Unix-like:

```bash
make demo
```

Then open <http://localhost:8000>.

## Frontend

Use `cmd /c npm ...` on Windows so PowerShell execution policy does not block npm.

```powershell
cmd /c npm install
cmd /c npm run web:dev:tourist
cmd /c npm run web:dev:admin
```

- Tourist app: <http://localhost:3001>
- Admin app: <http://localhost:3002>
- API base defaults to `http://127.0.0.1:8000`; override with `NEXT_PUBLIC_API_BASE`.

## Verify

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test.ps1
```

Frontend checks:

```powershell
cmd /c npm run web:lint
cmd /c npm run web:typecheck
cmd /c npm run web:build
```

The scripts set `UV_CACHE_DIR` to `.uv-cache` and `UV_PYTHON_INSTALL_DIR` to `.uv-python`
so the project does not depend on global uv state.
