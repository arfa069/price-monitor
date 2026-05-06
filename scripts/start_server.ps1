param(
    [switch]$BackendOnly
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"

function Get-PortUsage {
    param([int]$Port)
    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($connections) {
        $results = @()
        foreach ($conn in $connections) {
            $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
            $procName = if ($proc) { $proc.ProcessName } else { "Unknown" }
            $results += [PSCustomObject]@{
                PID = $conn.OwningProcess
                ProcessName = $procName
                LocalAddress = $conn.LocalAddress
                State = $conn.State
            }
        }
        return $results
    }
    return $null
}

function Close-ServiceWindows {
    $keywords = @("uvicorn", "npm", "vite", "node", "python")
    $toClose = @()

    $procs = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match "powershell|pwsh|cmd" -and $_.CommandLine
    }

    foreach ($proc in $procs) {
        $cmdLine = $proc.CommandLine
        $matched = $false
        foreach ($kw in $keywords) {
            if ($cmdLine -match $kw) {
                $matched = $true
                break
            }
        }
        if ($matched -and $proc.ProcessId -ne $PID) {
            $toClose += $proc.ProcessId
        }
    }

    foreach ($id in $toClose) {
        $p = Get-Process -Id $id -ErrorAction SilentlyContinue
        if ($p) {
            Write-Host "  Closing window: $($p.ProcessName) (PID: $id)" -ForegroundColor DarkGray
            $p.CloseMainWindow() | Out-Null
            Start-Sleep -Milliseconds 100
            if (-not ($p.HasExited)) {
                $p.Kill()
            }
        }
    }
}

Write-Host "========================================" -ForegroundColor Green
Write-Host "  Price Monitor Launcher" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host ""
Write-Host "[Check] Scanning port usage..." -ForegroundColor Cyan

$portIssues = @()

$frontendPort = Get-PortUsage -Port 3000
if ($frontendPort) {
    $portIssues += [PSCustomObject]@{
        Port = 3000
        Service = "Frontend"
        Info = $frontendPort
    }
}

$backendPort = Get-PortUsage -Port 8000
if ($backendPort) {
    $portIssues += [PSCustomObject]@{
        Port = 8000
        Service = "Backend"
        Info = $backendPort
    }
}

if ($portIssues) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "  Ports in use - closing windows" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow

    Close-ServiceWindows

    foreach ($issue in $portIssues) {
        foreach ($p in $issue.Info) {
            if ($p.State -eq "Listen") {
                Write-Host "  Stopping: $($p.ProcessName) (PID: $($p.PID))" -ForegroundColor DarkGray
                Stop-Process -Id $p.PID -Force -ErrorAction SilentlyContinue
            }
        }
    }

    Start-Sleep -Milliseconds 500
}

Write-Host "  [OK] Port 3000 (Frontend): Free" -ForegroundColor Green
Write-Host "  [OK] Port 8000 (Backend):  Free" -ForegroundColor Green

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
