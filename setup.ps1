# One-time setup on Windows: Python venv + backend packages, frontend packages (and optionally the Playwright test tools).
# Usage: .\setup.ps1            (app only)      .\setup.ps1 -Tests   (also Playwright + Chromium for scripts\*.mjs)
param([switch]$Tests)
$ErrorActionPreference = "Continue"   # native stderr notices (e.g. pip upgrade hints) must not abort the script
$root = $PSScriptRoot
function Check($what) { if ($LASTEXITCODE -ne 0) { Write-Host "$what failed (exit $LASTEXITCODE)." -ForegroundColor Red; exit $LASTEXITCODE } }

$py = Join-Path $root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { python -m venv (Join-Path $root "backend\.venv"); Check "Creating the Python venv" }
& $py -m pip install -q --disable-pip-version-check -r (Join-Path $root "backend\requirements.txt"); Check "Installing backend packages"
Write-Host "Backend packages ready. (Optional Hindi embeddings: backend\.venv\Scripts\python.exe -m pip install sentence-transformers)" -ForegroundColor Green

Push-Location (Join-Path $root "frontend"); npm install --no-audit --no-fund; Check "Installing frontend packages"; Pop-Location
if ($Tests) {
    Push-Location (Join-Path $root "scripts"); npm install --no-audit --no-fund; Check "Installing test tools"; npx playwright install chromium; Check "Installing Chromium"; Pop-Location
}
Write-Host "Setup done. Next: .\seed.ps1  then  .\dev.ps1" -ForegroundColor Green
