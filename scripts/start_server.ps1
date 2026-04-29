param(
    [switch]$BackendOnly
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"

Write-Host "========================================" -ForegroundColor Green
Write-Host "  Price Monitor Launcher" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host ""
Write-Host "[Backend] Starting..." -ForegroundColor Cyan
$backendCmd = "Set-Location `"$backendDir`"; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
Write-Host "[Backend] http://localhost:8000" -ForegroundColor Cyan

if (-not $BackendOnly) {
    Write-Host ""
    Write-Host "[Frontend] Starting..." -ForegroundColor Magenta
    $frontendCmd = "Set-Location `"$frontendDir`"; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd
    Write-Host "[Frontend] http://localhost:3000" -ForegroundColor Magenta

    Write-Host ""
    Write-Host "Tip: Use -BackendOnly for backend only" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Services started." -ForegroundColor Yellow
Write-Host "  Close windows to stop." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Green