$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:UV_CACHE_DIR = Join-Path $root ".uv-cache"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $root ".uv-python"

function Import-DotEnv {
  param([string]$Path)
  if (-not (Test-Path $Path)) { return }
  foreach ($rawLine in Get-Content -Path $Path) {
    $line = $rawLine.Trim()
    if (-not $line -or $line.StartsWith("#")) { continue }
    $match = [regex]::Match($line, '^\s*([^#=\s]+)\s*=\s*(.*)\s*$')
    if (-not $match.Success) { continue }
    $name = $match.Groups[1].Value
    $value = $match.Groups[2].Value.Trim()
    if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
      $value = $value.Substring(1, $value.Length - 2)
    }
    [Environment]::SetEnvironmentVariable($name, $value, "Process")
  }
}

Import-DotEnv (Join-Path $root ".env")
Import-DotEnv (Join-Path $root ".env.local")

if (-not $env:AETHER_STORAGE_MODE) { $env:AETHER_STORAGE_MODE = "inmemory" }

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
