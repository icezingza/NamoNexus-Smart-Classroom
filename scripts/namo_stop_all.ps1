# =============================================================================
# Namo Core - Master Stop Script
# Stops NRE API Server + Cloudflare Tunnel
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\namo_stop_all.ps1
# =============================================================================

$Root    = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $Root "logs\.pids"

Write-Host ""
Write-Host "[Namo] Stopping all services..." -ForegroundColor Yellow

function Stop-ByPid($id, $label) {
    if ($id -and $id -gt 0) {
        try {
            Stop-Process -Id $id -Force -ErrorAction Stop
            Write-Host "  [OK] Stopped $label (PID $id)" -ForegroundColor Green
        } catch {
            Write-Host "  [-] $label (PID $id) not running" -ForegroundColor Gray
        }
    }
}

if (Test-Path $PidFile) {
    $savedPids = Get-Content $PidFile | ConvertFrom-Json
    Stop-ByPid $savedPids.backend "NRE API Server"
    Stop-ByPid $savedPids.tunnel  "Cloudflare Tunnel"
    Remove-Item $PidFile -Force
    Write-Host ""
    Write-Host "  [DONE] All services stopped." -ForegroundColor Green
} else {
    Write-Host "  [INFO] No PID file found. Stopping by process name..." -ForegroundColor Yellow
    Get-Process -Name "python"      -ErrorAction SilentlyContinue | ForEach-Object {
        $_.Kill()
        Write-Host "  [OK] Stopped python PID $($_.Id)" -ForegroundColor Green
    }
    Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue | ForEach-Object {
        $_.Kill()
        Write-Host "  [OK] Stopped cloudflared PID $($_.Id)" -ForegroundColor Green
    }
}

Write-Host ""
