$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:UV_CACHE_DIR = Join-Path $root ".uv-cache"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $root ".uv-python"
if (-not $env:AETHER_STORAGE_MODE) { $env:AETHER_STORAGE_MODE = "inmemory" }
if (-not $env:AETHER_AI_PROVIDER) { $env:AETHER_AI_PROVIDER = "fake" }

$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($docker) {
  docker compose -f infra/docker-compose.yml up -d redis postgres minio
}

if ($env:AETHER_STORAGE_MODE -eq "database") {
  New-Item -ItemType Directory -Force -Path .local | Out-Null
  Write-Host "==> Running Alembic migrations (AETHER_STORAGE_MODE=database)"
  Push-Location apps/api
  uv run alembic upgrade head
  Pop-Location
}

uv run --project apps/api uvicorn aether_api.main:app --host 0.0.0.0 --port 8000
