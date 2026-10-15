$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $ProjectRoot "frontend"
Push-Location $Frontend
try {
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
        npm install
    }
    Write-Host "Starting Vite on http://localhost:5173 ..." -ForegroundColor Green
    npm run dev
}
finally {
    Pop-Location
}
