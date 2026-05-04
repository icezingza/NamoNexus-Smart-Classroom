# =============================================================================
# Namo Core -- Windows Startup Script
# Phase 8: Deployment
#
# Starts the FastAPI backend and optionally the React dashboard.
# Run from the project root:
#   powershell -ExecutionPolicy Bypass -File .\scripts\start_windows.ps1
#
# Options:
#   -BackendOnly    Start only the backend API server
#   -Port 8000      Override API port
# =============================================================================

param(
    [switch]$BackendOnly,
    [int]$Port = 0
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$EnvFile = Join-Path $Root "backend\namo_core\.env"
$LogDir = Join-Path $Root "logs"

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Namo Core -- Starting (Windows)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $VenvPython)) {
    Write-Host "ERROR: Virtual environment not found." -ForegroundColor Red
    Write-Host "Run first: powershell -ExecutionPolicy Bypass -File .\scripts\install_windows.ps1" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $EnvFile)) {
    Write-Host "ERROR: .env not found at $EnvFile" -ForegroundColor Red
    Write-Host "Security Policy Violation: You must explicitly create a .env file with valid credentials before starting the system." -ForegroundColor Yellow
    exit 1
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# Override port if specified
if ($Port -gt 0) {
    $env:NAMO_API_PORT = $Port
}

# ---------------------------------------------------------------------------
# Redis Pre-flight -- required for WebSocket PubSub (Latency <50ms)
# ---------------------------------------------------------------------------
Write-Host "[Redis] Checking Redis on localhost:6379..." -ForegroundColor Yellow
$redisReady = $false
try {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $tcpClient.Connect("127.0.0.1", 6379)
    $tcpClient.Close()
    $redisReady = $true
    Write-Host "  Redis: ONLINE" -ForegroundColor Green
} catch {
    Write-Host "  Redis: OFFLINE -- attempting to start via WSL2..." -ForegroundColor Yellow
    $wslCheck = wsl --list --verbose 2>&1 | Select-String "Ubuntu"
    if ($wslCheck) {
        Start-Process -FilePath "wsl" -ArgumentList "-d", "Ubuntu", "-u", "root", "--", "service", "redis-server", "start" -NoNewWindow -Wait
        Start-Sleep -Seconds 3
        try {
            $tcpClient2 = New-Object System.Net.Sockets.TcpClient
            $tcpClient2.Connect("127.0.0.1", 6379)
            $tcpClient2.Close()
            $redisReady = $true
            Write-Host "  Redis: ONLINE (started via WSL2)" -ForegroundColor Green
        } catch {
            Write-Host "  WARNING: Redis still unreachable. WebSocket PubSub will be degraded." -ForegroundColor Red
            Write-Host "  Manual fix: wsl -d Ubuntu -- sudo service redis-server start" -ForegroundColor Gray
        }
    } else {
        Write-Host "  WARNING: WSL2 Ubuntu not found. Start Redis manually." -ForegroundColor Red
    }
}

# ---------------------------------------------------------------------------
# Start Backend (FastAPI + uvicorn)
# ---------------------------------------------------------------------------
Write-Host "[Backend] Starting FastAPI server..." -ForegroundColor Yellow
$BackendLog = Join-Path $LogDir "backend.log"
$BackendProcess = Start-Process -FilePath $VenvPython `
    -ArgumentList "-m", "namo_core.main" `
    -WorkingDirectory (Join-Path $Root "backend") `
    -RedirectStandardOutput $BackendLog `
    -RedirectStandardError "$LogDir\backend_error.log" `
    -PassThru -NoNewWindow

$env:NAMO_BACKEND_PID = $BackendProcess.Id
Write-Host "  Backend PID: $($BackendProcess.Id)" -ForegroundColor Green
Write-Host "  Log: $BackendLog" -ForegroundColor Gray

# Wait for backend to become ready
Write-Host "  Waiting for backend to be ready..." -ForegroundColor Gray
$apiPort = if ($Port -gt 0) { $Port } else { 8000 }
$maxWait = 20
$ready = $false
for ($i = 0; $i -lt $maxWait; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$apiPort/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {}
    Write-Host "  ." -NoNewline -ForegroundColor Gray
}
Write-Host ""

if ($ready) {
    Write-Host "  Backend ready at http://127.0.0.1:$apiPort" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Backend health check timed out. Check $BackendLog" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Start Frontend (React + Vite) -- optional
# ---------------------------------------------------------------------------
if (-not $BackendOnly) {
    $DashboardPath = Join-Path $Root "frontend"
    $NodeModules = Join-Path $DashboardPath "node_modules"

    if (Test-Path $NodeModules) {
        Write-Host ""
        Write-Host "[Frontend] Starting React dashboard..." -ForegroundColor Yellow
        $FrontendLog = Join-Path $LogDir "frontend.log"
        $FrontendProcess = Start-Process -FilePath "npm" `
            -ArgumentList "run", "dev" `
            -WorkingDirectory $DashboardPath `
            -RedirectStandardOutput $FrontendLog `
            -PassThru -NoNewWindow

        $env:NAMO_FRONTEND_PID = $FrontendProcess.Id
        Start-Sleep -Seconds 3
        Write-Host "  Frontend PID: $($FrontendProcess.Id)" -ForegroundColor Green
        Write-Host "  Dashboard at http://localhost:5173" -ForegroundColor Green
    } else {
        Write-Host "[Frontend] Skipped -- run install_windows.ps1 first." -ForegroundColor Gray
    }
}

# Save PIDs for stop script
$PidFile = Join-Path $Root "logs\.pids"
@{
    backend = $BackendProcess.Id
    frontend = if ($env:NAMO_FRONTEND_PID) { [int]$env:NAMO_FRONTEND_PID } else { 0 }
} | ConvertTo-Json | Set-Content $PidFile

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Namo Core is running!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  API:       http://127.0.0.1:$apiPort" -ForegroundColor White
Write-Host "  API Docs:  http://127.0.0.1:$apiPort/docs" -ForegroundColor White
if (-not $BackendOnly) {
    Write-Host "  Dashboard: http://localhost:5173" -ForegroundColor White
}
Write-Host ""
Write-Host "  To stop:   powershell -ExecutionPolicy Bypass -File .\scripts\stop_windows.ps1" -ForegroundColor Gray
Write-Host "  Logs:      $LogDir" -ForegroundColor Gray
Write-Host ""
