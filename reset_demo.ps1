# Restores the demo to the clean seeded state (no flags/overrides/new cases) in about a second, no full re-seed.
# Works while the API is running. Needs one prior .\seed.ps1 (it saves data\ekatra.clean.db).
$ErrorActionPreference = "Continue"
$py = Join-Path $PSScriptRoot "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "Run .\setup.ps1 first." -ForegroundColor Yellow; exit 1 }
$env:PYTHONIOENCODING = "utf-8"
& $py (Join-Path $PSScriptRoot "scripts\reset_demo.py")
exit $LASTEXITCODE
