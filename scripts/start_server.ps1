$ErrorActionPreference = "Stop"

# Change to project root (parent of scripts dir)
Set-Location $PSScriptRoot/..

Write-Host "Starting price-monitor backend..." -ForegroundColor Green

# Check database connection
try {
    $null = python -c "import asyncio; from app.database import engine; asyncio.run(engine.connect())" 2>$null
    Write-Host "[OK] Database connection OK" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Database connection failed - ensure PostgreSQL is running" -ForegroundColor Yellow
}

# Start uvicorn directly (no --reload).
# On Windows, uvicorn --reload spawns a child process that uses SelectorEventLoop,
# which cannot create subprocesses — breaking Playwright's browser driver launch.
# Run via python -m so the event loop policy set in app/main.py takes effect first.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000