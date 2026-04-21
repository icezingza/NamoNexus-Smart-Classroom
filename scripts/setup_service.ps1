# =============================================================================
# Namo Core - NSSM Service Setup (Phase 9+ / Enterprise Readiness)
# Creates a robust Windows Service for the backend using NSSM
# =============================================================================

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$NssmPath = Join-Path $Root "scripts\nssm.exe"
$ServiceName = "NamoCoreBackend"

if (-not (Test-Path $NssmPath)) {
    Write-Host "[ERROR] nssm.exe not found in scripts/ directory. Please download it from http://nssm.cc/" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Installing Namo Core as a Windows Service..." -ForegroundColor Cyan

& $NssmPath install $ServiceName "$Root\.venv\Scripts\python.exe" "-m uvicorn namo_core.api.app:app --host 0.0.0.0 --port 8000"
& $NssmPath set $ServiceName AppDirectory "$Root\backend"
& $NssmPath set $ServiceName AppStdout "$Root\logs\backend_service.log"
& $NssmPath set $ServiceName AppStderr "$Root\logs\backend_service_error.log"
& $NssmPath set $ServiceName AppRestartDelay 2000

Write-Host "[OK] Service '$ServiceName' installed successfully. You can start it via Services.msc or 'nssm start $ServiceName'" -ForegroundColor Green