# =============================================================================
# Namo Core - Master Startup Script (Phase 9+)
# Starts NRE API Server + Cloudflare Tunnel together as background processes.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\namo_start_all.ps1
#
# Options:
#   -ApiOnly     Start API only (no tunnel)
#   -TunnelOnly  Start tunnel only (API must already be running)
# =============================================================================

param(
    [switch]$ApiOnly,
    [switch]$TunnelOnly
)

$ErrorActionPreference = "Continue"
$Root        = Split-Path -Parent $PSScriptRoot
$ScriptDir   = $PSScriptRoot
$VenvPython  = Join-Path $Root ".venv\Scripts\python.exe"
$Cloudflared = Join-Path $ScriptDir "cloudflared.exe"
$LogDir      = Join-Path $Root "logs"
$PidFile     = Join-Path $LogDir ".pids"
$TunnelLog   = Join-Path $LogDir "tunnel.log"
$ApiLog      = Join-Path $LogDir "backend.log"
$ApiErrLog   = Join-Path $LogDir "backend_error.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Namo Core - Starting All Services" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$pids = @{ backend = 0; tunnel = 0 }

# ---------------------------------------------------------------------------
# START: NRE API Server
# ---------------------------------------------------------------------------
if (-not $TunnelOnly) {

    if (-not (Test-Path $VenvPython)) {
        Write-Host "[ERROR] .venv not found. Run install_windows.ps1 first." -ForegroundColor Red
        exit 1
    }

    # Stop old process if exists
    if (Test-Path $PidFile) {
        try {
            $oldPids = Get-Content $PidFile | ConvertFrom-Json
            if ($oldPids.backend -gt 0) {
                Stop-Process -Id $oldPids.backend -Force -ErrorAction SilentlyContinue
            }
        } catch {}
    }

    Write-Host "[API] Starting NRE API Server..." -ForegroundColor Yellow

    if (Test-Path $ApiLog)    { Clear-Content $ApiLog    -ErrorAction SilentlyContinue }
    if (Test-Path $ApiErrLog) { Clear-Content $ApiErrLog -ErrorAction SilentlyContinue }

    $apiProc = Start-Process -FilePath $VenvPython `
        -ArgumentList "-m", "namo_core.main" `
        -WorkingDirectory (Join-Path $Root "backend") `
        -RedirectStandardOutput $ApiLog `
        -RedirectStandardError  $ApiErrLog `
        -PassThru -NoNewWindow

    $pids.backend = $apiProc.Id
    Write-Host "  PID: $($apiProc.Id)" -ForegroundColor Gray

    # Wait for /health
    Write-Host "  Waiting for API" -NoNewline -ForegroundColor Gray
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        Write-Host "." -NoNewline -ForegroundColor Gray
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" `
                -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($r.StatusCode -eq 200) { $ready = $true; break }
        } catch {}
    }
    Write-Host ""

    if ($ready) {
        Write-Host "  [OK] API ready at http://127.0.0.1:8000" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] API not responding. Check: $ApiErrLog" -ForegroundColor Yellow
    }
}

# ---------------------------------------------------------------------------
# START: Cloudflare Tunnel
# ---------------------------------------------------------------------------
if (-not $ApiOnly) {

    if (-not (Test-Path $Cloudflared)) {
        Write-Host "[ERROR] cloudflared.exe not found in scripts/" -ForegroundColor Red
        exit 1
    }

    # Stop old tunnel if exists
    if (Test-Path $PidFile) {
        try {
            $oldPids = Get-Content $PidFile | ConvertFrom-Json
            if ($oldPids.tunnel -gt 0) {
                Stop-Process -Id $oldPids.tunnel -Force -ErrorAction SilentlyContinue
            }
        } catch {}
    }

    Write-Host ""
    Write-Host "[Tunnel] Starting Cloudflare Tunnel: namo-core ..." -ForegroundColor Yellow

    if (Test-Path $TunnelLog) { Clear-Content $TunnelLog -ErrorAction SilentlyContinue }

    $ConfigFile  = Join-Path $env:USERPROFILE ".cloudflared\config.yml"

    $tunnelProc = Start-Process -FilePath $Cloudflared `
        -ArgumentList "tunnel", "--config", $ConfigFile, "run", "namo-core" `
        -RedirectStandardError $TunnelLog `
        -PassThru -WindowStyle Hidden

    $pids.tunnel = $tunnelProc.Id
    Write-Host "  PID: $($tunnelProc.Id)" -ForegroundColor Gray

    # Wait for connection
    Write-Host "  Connecting" -NoNewline -ForegroundColor Gray
    $connected = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1
        Write-Host "." -NoNewline -ForegroundColor Gray
        if (Test-Path $TunnelLog) {
            $content = Get-Content $TunnelLog -Raw -ErrorAction SilentlyContinue
            if ($content -match "Registered tunnel connection") {
                $connected = $true; break
            }
        }
    }
    Write-Host ""

    if ($connected) {
        Write-Host "  [OK] Tunnel connected" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Tunnel not connected yet. Check: $TunnelLog" -ForegroundColor Yellow
    }
}

# ---------------------------------------------------------------------------
# Save PIDs
# ---------------------------------------------------------------------------
$pids | ConvertTo-Json | Set-Content $PidFile -Encoding ascii

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  Namo Core - Ready!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host "  Local API  : http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  Public API : https://api.namonexus.com" -ForegroundColor Yellow
Write-Host "  WebSocket  : wss://api.namonexus.com/ws" -ForegroundColor Cyan
Write-Host "  Stop       : .\scripts\namo_stop_all.ps1" -ForegroundColor Gray
Write-Host "  Logs       : .\logs\" -ForegroundColor Gray
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
