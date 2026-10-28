# Starts the Ekatra API (port 8010) and UI (http://localhost:5174) in two windows.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$py = Join-Path $root "backend\.venv\Scripts\python.exe"

foreach ($port in 8010, 5174) {
    if (netstat -ano | Select-String "[:\]]$port\s+\S+\s+LISTENING") {
        Write-Host "Port $port is already in use (an earlier Ekatra run?). Run .\stop.ps1 first." -ForegroundColor Red
        exit 1
    }
}

if (-not (Test-Path $py)) {
    Write-Host "Creating Python venv and installing backend packages..." -ForegroundColor Cyan
    python -m venv (Join-Path $root "backend\.venv")
    & $py -m pip install -q -r (Join-Path $root "backend\requirements.txt")
}
if (-not (Test-Path (Join-Path $root "frontend\node_modules"))) {
    Write-Host "Installing frontend packages..." -ForegroundColor Cyan
    Push-Location (Join-Path $root "frontend"); npm install --no-audit --no-fund; Pop-Location
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; & '$py' -m uvicorn app.main:app --host localhost --port 8010 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"

Write-Host "API: http://localhost:8010/health" -ForegroundColor Green
Write-Host "UI:  http://localhost:5174" -ForegroundColor Green
