# namo_start_backend.ps1 — Start Backend with PID Tracking
$projectDir = "C:\Users\icezi\Downloads\Github repo\namo_core_project"
$backendDir = "$projectDir\backend"
$pidFile = "$projectDir\.pid"
$venvPath = "$projectDir\.venv\Scripts\activate.ps1"

Write-Host "[*] Starting Namo Core Backend..." -ForegroundColor Cyan

# Activate venv
if (Test-Path $venvPath) {
    & $venvPath
} else {
    Write-Host "⚠️  Virtual environment not found at $venvPath" -ForegroundColor Yellow
}

# Remove old PID file
Remove-Item $pidFile -Force -ErrorAction SilentlyContinue

# Start backend process and capture PID
try {
    $proc = Start-Process -FilePath "python" `
        -ArgumentList "-m uvicorn namo_core.api.app:app --host 0.0.0.0 --port 8000 --reload" `
        -WorkingDirectory $backendDir `
        -PassThru `
        -NoNewWindow

    # Save PID to file
    $proc.Id | Out-File -FilePath $pidFile -Force
    Write-Host "[OK] Backend started with PID: $($proc.Id)" -ForegroundColor Green
    Write-Host "[OK] PID saved to: $pidFile" -ForegroundColor Green
} catch {
    Write-Host "[❌] Failed to start backend: $_" -ForegroundColor Red
}
