$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$env:UV_CACHE_DIR = Join-Path $root ".uv-cache"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $root ".uv-python"

$touristPort = 3001
$adminPort = 3002
$apiPort = 8000
$allPorts = @($touristPort, $adminPort, $apiPort)

function Stop-PortProcess {
    param([int]$Port)
    $conns = netstat -ano | Select-String ":$Port\s.*LISTENING"
    foreach ($line in $conns) {
        $targetPid = ($line -split "\s+")[-1]
        if ($targetPid -match "^\d+$" -and [int]$targetPid -gt 0) {
            Write-Host "  Killing PID $targetPid on port $Port"
            Stop-Process -Id ([int]$targetPid) -Force -ErrorAction SilentlyContinue
        }
    }
}

# 1. Kill stale processes on target ports
Write-Host "`n==> Cleaning stale processes on ports $($allPorts -join ', ')..."
foreach ($port in $allPorts) {
    Stop-PortProcess -Port $port
}

# 2. Clean .next build artifacts
Write-Host "`n==> Cleaning .next directories..."
$touristNext = Join-Path $root "apps\web-tourist\.next"
$adminNext = Join-Path $root "apps\web-admin\.next"
if (Test-Path $touristNext) { Remove-Item -Recurse -Force $touristNext; Write-Host "  Removed $touristNext" }
if (Test-Path $adminNext) { Remove-Item -Recurse -Force $adminNext; Write-Host "  Removed $adminNext" }

# 3. Start API backend
Write-Host "`n==> Starting API on port $apiPort..."
$apiJob = Start-Job -ScriptBlock {
    param($root)
    Set-Location $root
    $env:UV_CACHE_DIR = Join-Path $root ".uv-cache"
    $env:UV_PYTHON_INSTALL_DIR = Join-Path $root ".uv-python"
    uv run --project apps/api uvicorn aether_api.main:app --host 0.0.0.0 --port 8000
} -ArgumentList $root

# 4. Start tourist frontend
Write-Host "`n==> Starting tourist app on port $touristPort..."
$touristJob = Start-Job -ScriptBlock {
    param($root)
    Set-Location $root
    cmd /c "npm --workspace @aether/web-tourist run dev -- --port 3001"
} -ArgumentList $root

# 5. Start admin frontend
Write-Host "`n==> Starting admin app on port $adminPort..."
$adminJob = Start-Job -ScriptBlock {
    param($root)
    Set-Location $root
    cmd /c "npm --workspace @aether/web-admin run dev -- --port 3002"
} -ArgumentList $root

Write-Host "`n==> All services starting..."
Write-Host "  API:       http://localhost:$apiPort"
Write-Host "  Tourist:   http://localhost:$touristPort"
Write-Host "  Admin:     http://localhost:$adminPort"
Write-Host "`nPress Ctrl+C to stop all services.`n"

# Wait for Ctrl+C, then clean up
try {
    while ($true) {
        # Print job output as it arrives
        foreach ($job in @($apiJob, $touristJob, $adminJob)) {
            $output = Receive-Job $job -ErrorAction SilentlyContinue
            if ($output) { Write-Host $output }
        }
        # Check if any job died
        foreach ($job in @($apiJob, $touristJob, $adminJob)) {
            if ($job.State -eq "Failed") {
                Write-Host "WARNING: Job '$($job.Name)' failed." -ForegroundColor Yellow
            }
        }
        Start-Sleep -Seconds 2
    }
} finally {
    Write-Host "`n==> Stopping all services..."
    Stop-Job -Job $apiJob, $touristJob, $adminJob -ErrorAction SilentlyContinue
    Remove-Job -Job $apiJob, $touristJob, $adminJob -Force -ErrorAction SilentlyContinue
    foreach ($port in $allPorts) { Stop-PortProcess -Port $port }
    Write-Host "Done."
}
