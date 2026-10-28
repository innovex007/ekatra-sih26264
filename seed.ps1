# Generates the synthetic dataset (80 institutions, 2,000 cases, answer key) and loads it into SQLite.
# Prints the demo-case table at the end. Safe to re-run: it resets the demo to a clean state.
$ErrorActionPreference = "Continue"   # native stderr (library warnings) must not abort the script
$root = $PSScriptRoot
$py = Join-Path $root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "Run .\dev.ps1 once first to create the venv." -ForegroundColor Yellow; exit 1 }
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
Push-Location $root
try { & $py -m data.generator.seed --seed 42 } finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { Write-Host "Seeding failed (exit $LASTEXITCODE)." -ForegroundColor Red; exit $LASTEXITCODE }
