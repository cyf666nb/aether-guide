$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$k6 = Get-Command k6 -ErrorAction SilentlyContinue
if (-not $k6) {
  Write-Error "k6 is not installed. Install k6 to run tests/perf/k6-smoke.js."
}
k6 run tests/perf/k6-smoke.js

