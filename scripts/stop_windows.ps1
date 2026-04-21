# =============================================================================
# Namo Core — Windows Graceful Stop Script
# Phase 8: Deployment
#
# Stops the backend and frontend processes started by start_windows.ps1
# Run from the project root:
#   powershell -ExecutionPolicy Bypass -File .\scripts\stop_windows.ps1
# =============================================================================

$Root = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $Root "logs\.pids"

Write-Host ""
Write-Host "Stopping Namo Core..." -ForegroundColor Yellow

function Stop-ProcessSafely($pid, $name) {
    if ($pid -and $pid -gt 0) {
        try {
            $proc = Get-Process -Id $pid -ErrorAction Stop
            $proc.Kill()
            Write-Host "  Stopped $name (PID $pid)" -ForegroundColor Green
        } catch {
            Write-Host "  $name (PID $pid) already stopped or not found." -ForegroundColor Gray
        }
    }
}

if (Test-Path $PidFile) {
    $pids = Get-Content $PidFile | ConvertFrom-Json
    Stop-ProcessSafely $pids.backend "Backend"
    Stop-ProcessSafely $pids.frontend "Frontend"
    Remove-Item $PidFile -Force
} else {
    Write-Host "  No PID file found. Attempting to stop by process name..." -ForegroundColor Yellow
    Get-Process -Name "python" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*namo_core*" } |
        ForEach-Object { $_.Kill(); Write-Host "  Stopped python PID $($_.Id)" -ForegroundColor Green }
}

Write-Host "  Done." -ForegroundColor Green
Write-Host ""
