<#
.SYNOPSIS
  Aether Guide - one-shot dev launcher (Windows PowerShell)

.DESCRIPTION
  Spins up FastAPI (8000), tourist Next.js (3001), and admin Next.js (3002)
  together, then opens the browser to the tourist app once it is ready.
  Each service runs in its own PowerShell window so logs stay readable;
  this main window coordinates readiness, browser launch, and cleanup.

.PARAMETER NoAdmin
  Do not start the admin app.

.PARAMETER NoTourist
  Do not start the tourist app.

.PARAMETER NoOpen
  Do not auto-open the browser.

.PARAMETER Clean
  Remove apps/web-*/.next build caches before starting (needed only when
  a previous build corrupted the incremental cache).

.PARAMETER Docker
  Also start postgres / redis / minio via docker compose.

.PARAMETER SkipInstall
  Skip `npm install` and `uv sync` preflight (assumes deps already present).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\start.ps1
  # Default: API + Tourist + Admin, auto-opens browser

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -NoAdmin -Docker
  # API + Tourist + infra containers, no admin
#>
[CmdletBinding()]
param(
    [switch]$NoAdmin,
    [switch]$NoTourist,
    [switch]$NoOpen,
    [switch]$Clean,
    [switch]$Docker,
    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'

# ---------- paths & constants ------------------------------------------------
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$apiPort     = 8000
$touristPort = 3001
$adminPort   = 3002

$logDir = Join-Path $root '.local'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

$env:UV_CACHE_DIR          = Join-Path $root '.uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $root '.uv-python'

# ---------- helpers ----------------------------------------------------------
function Write-Step  { param($m) Write-Host "==> $m" -ForegroundColor Cyan }
function Write-Ok    { param($m) Write-Host "  OK  $m" -ForegroundColor Green }
function Write-Warn2 { param($m) Write-Host "  !!  $m" -ForegroundColor Yellow }
function Write-Err2  { param($m) Write-Host "  XX  $m" -ForegroundColor Red }

function Import-DotEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    foreach ($rawLine in Get-Content -Path $Path) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith('#')) { continue }
        $m = [regex]::Match($line, '^\s*([^#=\s]+)\s*=\s*(.*)\s*$')
        if (-not $m.Success) { continue }
        $name  = $m.Groups[1].Value
        $value = $m.Groups[2].Value.Trim()
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
}

function Get-PortOwner {
    param([int]$Port)
    # netstat is available on every supported Windows; Get-NetTCPConnection is
    # not (Server Core / older builds), so stick with the portable path.
    $lines = netstat -ano 2>$null | Select-String ":$Port\s.*LISTENING"
    $pids  = @()
    foreach ($ln in $lines) {
        $parts = ($ln.ToString() -split '\s+') | Where-Object { $_ -ne '' }
        $candidate = $parts[-1]
        if ($candidate -match '^\d+$' -and [int]$candidate -gt 0) {
            $pids += [int]$candidate
        }
    }
    return ($pids | Select-Object -Unique)
}

function Stop-PortOwner {
    param([int]$Port)
    foreach ($procId in (Get-PortOwner -Port $Port)) {
        try {
            Stop-Process -Id $procId -Force -ErrorAction Stop
            Write-Warn2 "killed PID $procId on :$Port"
        } catch {
            # process already gone - ignore
        }
    }
}

function Wait-ForHttp {
    param(
        [string]$Url,
        [int]$TimeoutSec = 60,
        [string]$Label = 'service'
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($r.StatusCode -lt 500) {
                Write-Ok "$Label ready ($Url, HTTP $($r.StatusCode))"
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    Write-Err2 "$Label not ready within ${TimeoutSec}s ($Url)"
    return $false
}

# Open a service in its own PowerShell window. We pick this over
# `cmd /c start "title" ...` because cmd's quoting rules turn ugly fast once
# the title or working directory contain spaces. Returning the Process via
# -PassThru also lets us hard-kill windows on cleanup.
$script:ChildProcs = @()

function Start-ServiceWindow {
    param(
        [Parameter(Mandatory)][string]$Title,
        [Parameter(Mandatory)][string]$Command,
        # PowerShell color name, e.g. 'Cyan' / 'Green' / 'Magenta'.
        [string]$Foreground = 'Gray'
    )

    # NOTE: $Command is embedded into the new PS session via a here-string,
    # so single quotes in $Command would break the boot block. All callers
    # in this script pass safe strings (npm / call-operator against demo.ps1).
    $bootBlock = @"
`$host.UI.RawUI.WindowTitle = '$Title'
`$host.UI.RawUI.ForegroundColor = '$Foreground'
Set-Location -LiteralPath '$root'
Write-Host '>>> $Title' -ForegroundColor $Foreground
$Command
"@

    $proc = Start-Process -FilePath 'powershell.exe' `
        -ArgumentList @(
            '-NoExit',
            '-NoProfile',
            '-ExecutionPolicy', 'Bypass',
            '-Command', $bootBlock
        ) `
        -WindowStyle Normal `
        -PassThru

    $script:ChildProcs += [pscustomobject]@{
        Title = $Title
        Id    = $proc.Id
        Proc  = $proc
    }
}

# ---------- preflight --------------------------------------------------------
Write-Step 'Preflight checks'

$missing = @()
foreach ($tool in @('node','npm','uv')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { $missing += $tool }
}
if ($missing.Count -gt 0) {
    Write-Err2 "Missing required tools: $($missing -join ', ')"
    Write-Host ''
    Write-Host '  Install guides:'
    Write-Host '    uv    https://docs.astral.sh/uv/getting-started/installation/'
    Write-Host '    node  https://nodejs.org/  (LTS 20+)'
    Write-Host '    npm   bundled with node'
    exit 1
}
Write-Ok 'uv / node / npm found'

Import-DotEnv (Join-Path $root '.env')
Import-DotEnv (Join-Path $root '.env.local')
if (-not $env:AETHER_STORAGE_MODE) { $env:AETHER_STORAGE_MODE = 'inmemory' }
Write-Ok "AETHER_STORAGE_MODE = $($env:AETHER_STORAGE_MODE)"

# ---------- optional docker --------------------------------------------------
if ($Docker) {
    Write-Step 'Starting infra containers (postgres / redis / minio)'
    $dockerBin = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerBin) {
        Write-Err2 'docker not found; drop -Docker or install Docker Desktop first'
        exit 1
    }
    docker compose -f infra/docker-compose.yml up -d postgres redis minio
    Write-Ok 'infra containers up'
}

if ($env:AETHER_STORAGE_MODE -eq 'database') {
    Write-Step 'Running Alembic migrations (AETHER_STORAGE_MODE=database)'
    Push-Location (Join-Path $root 'apps/api')
    try { uv run alembic upgrade head } finally { Pop-Location }
    Write-Ok 'migrations applied'
}

# ---------- install dependencies --------------------------------------------
if (-not $SkipInstall) {
    if (-not (Test-Path (Join-Path $root 'node_modules'))) {
        Write-Step 'Installing npm dependencies (first run may take a few minutes)...'
        cmd /c 'npm install'
        if ($LASTEXITCODE -ne 0) { Write-Err2 'npm install failed'; exit 1 }
        Write-Ok 'npm install done'
    } else {
        Write-Ok 'node_modules present (skip npm install; delete the dir to force)'
    }

    if (-not (Test-Path (Join-Path $root '.venv'))) {
        Write-Step 'Creating Python virtualenv via uv sync...'
        uv sync --project apps/api
        Write-Ok 'uv sync done'
    } else {
        Write-Ok '.venv present (skip uv sync)'
    }
}

# ---------- optional clean ---------------------------------------------------
if ($Clean) {
    foreach ($next in @('apps\web-tourist\.next', 'apps\web-admin\.next')) {
        $p = Join-Path $root $next
        if (Test-Path $p) {
            Remove-Item -Recurse -Force $p
            Write-Warn2 "removed $next"
        }
    }
}

# ---------- free stale port occupants ----------------------------------------
Write-Step 'Freeing target ports'
$targets = @($apiPort)
if (-not $NoTourist) { $targets += $touristPort }
if (-not $NoAdmin)   { $targets += $adminPort }
foreach ($p in $targets) { Stop-PortOwner -Port $p }
Write-Ok "ports freed: $($targets -join ', ')"

# ---------- launch services --------------------------------------------------
Write-Step 'Launching services in separate windows'

# API: Cyan, Tourist: Green, Admin: Magenta
$apiCmd = "& '$root\scripts\demo.ps1'"
Start-ServiceWindow -Title 'Aether - API (8000)' -Foreground 'Cyan' -Command $apiCmd
Write-Ok "API window started (:$apiPort)"

if (-not $NoTourist) {
    $touristCmd = 'cmd /c "npm --workspace @aether/web-tourist run dev"'
    Start-ServiceWindow -Title 'Aether - Tourist (3001)' -Foreground 'Green' -Command $touristCmd
    Write-Ok "Tourist window started (:$touristPort)"
}

if (-not $NoAdmin) {
    $adminCmd = 'cmd /c "npm --workspace @aether/web-admin run dev"'
    Start-ServiceWindow -Title 'Aether - Admin (3002)' -Foreground 'Magenta' -Command $adminCmd
    Write-Ok "Admin window started (:$adminPort)"
}

# ---------- wait for readiness ----------------------------------------------
Write-Step 'Waiting for services to become ready'

# API health: /docs is always available; Next apps: probe the root page.
$apiOk = Wait-ForHttp -Url "http://localhost:$apiPort/docs" -TimeoutSec 90 -Label 'API'

$touristOk = $true
if (-not $NoTourist) {
    $touristOk = Wait-ForHttp -Url "http://localhost:$touristPort" -TimeoutSec 120 -Label 'Tourist'
}

$adminOk = $true
if (-not $NoAdmin) {
    $adminOk = Wait-ForHttp -Url "http://localhost:$adminPort" -TimeoutSec 120 -Label 'Admin'
}

# ---------- open browser -----------------------------------------------------
if (-not $NoOpen) {
    if (-not $NoTourist -and $touristOk) {
        Write-Step "Opening browser -> http://localhost:$touristPort"
        Start-Process "http://localhost:$touristPort" | Out-Null
    } elseif ($apiOk) {
        Write-Step "Opening API docs -> http://localhost:$apiPort/docs"
        Start-Process "http://localhost:$apiPort/docs" | Out-Null
    }
}

# ---------- summary ----------------------------------------------------------
Write-Host ''
Write-Host '==============================================================' -ForegroundColor Cyan
Write-Host '  Aether Guide is running' -ForegroundColor Cyan
Write-Host '==============================================================' -ForegroundColor Cyan
Write-Host ("  API        http://localhost:{0}/docs" -f $apiPort)
if (-not $NoTourist) { Write-Host ("  Tourist    http://localhost:{0}" -f $touristPort) }
if (-not $NoAdmin)   { Write-Host ("  Admin      http://localhost:{0}" -f $adminPort) }
Write-Host ''
Write-Host '  Press Ctrl+C in this window (or close it) to stop everything.' -ForegroundColor Yellow
Write-Host ''

# ---------- idle loop + cleanup ---------------------------------------------
try {
    while ($true) { Start-Sleep -Seconds 2 }
} finally {
    Write-Host ''
    Write-Step 'Shutting down all services'

    # 1) Port-based kill: the real listener is usually a node.exe spawned by
    # npm, not the PowerShell shell we recorded below. Port kill covers that.
    foreach ($p in $targets) { Stop-PortOwner -Port $p }

    # 2) Window-based kill: close our bookkeeping PowerShell windows too.
    foreach ($entry in $script:ChildProcs) {
        try {
            Stop-Process -Id $entry.Id -Force -ErrorAction Stop
            Write-Warn2 "closed window '$($entry.Title)' (PID $($entry.Id))"
        } catch {
            # already exited - ignore
        }
    }
    Write-Ok 'all services stopped'
}
