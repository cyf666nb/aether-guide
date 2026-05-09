$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:UV_CACHE_DIR = Join-Path $root ".uv-cache"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $root ".uv-python"
$env:AETHER_STORAGE_MODE = "inmemory"
$env:AETHER_AI_PROVIDER = "fake"

$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($docker) {
  docker compose -f infra/docker-compose.yml up -d redis postgres minio
}

uv run --project apps/api uvicorn aether_api.main:app --host 0.0.0.0 --port 8000
