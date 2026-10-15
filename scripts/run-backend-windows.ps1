$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $ProjectRoot "backend"

Write-Host "[1/4] Checking Python 3.11..." -ForegroundColor Cyan
py -3.11 --version

Write-Host "[2/4] Installing/updating backend dependencies..." -ForegroundColor Cyan
py -3.11 -m pip install -r (Join-Path $Backend "requirements.txt")

Write-Host "[3/4] Applying database migrations..." -ForegroundColor Cyan
Push-Location $Backend
try {
    py -3.11 -m alembic upgrade head

    Write-Host "[4/4] Starting FastAPI on http://127.0.0.1:8000 ..." -ForegroundColor Green
    py -3.11 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
}
finally {
    Pop-Location
}
