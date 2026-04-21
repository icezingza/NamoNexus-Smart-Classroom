# run_stress_test.ps1 — Execute Orchestrator Stress Test
param(
    [int]$Workers = 10,
    [int]$Requests = 50
)

$projectDir = "C:\Users\icezi\Downloads\Github repo\namo_core_project"
$venvPath = "$projectDir\.venv\Scripts\activate.ps1"
$testScript = "$projectDir\tests\test_orchestrator_stress.py"

Write-Host "═════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " NAMO CORE — ORCHESTRATOR SINGLETON STRESS TEST" -ForegroundColor Cyan
Write-Host "═════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor White
Write-Host "  📊 Concurrent Workers: $Workers"
Write-Host "  📝 Total Requests:      $Requests"
Write-Host "  🎯 Target: http://localhost:8000"
Write-Host ""

# Activate venv
if (Test-Path $venvPath) {
    Write-Host "[*] Activating virtual environment..." -ForegroundColor Yellow
    & $venvPath
} else {
    Write-Host "[!] Virtual environment not found!" -ForegroundColor Red
    exit 1
}

# Check dependencies
Write-Host "[*] Checking dependencies..." -ForegroundColor Yellow
python -m pip show psutil -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "    Installing psutil..." -ForegroundColor Yellow
    python -m pip install psutil -q
}

python -m pip show httpx -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "    Installing httpx..." -ForegroundColor Yellow
    python -m pip install httpx -q
}

# Check if backend is running
Write-Host ""
Write-Host "[*] Verifying backend is running..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -ErrorAction Stop -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Backend is online" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Backend is NOT running on localhost:8000" -ForegroundColor Red
    Write-Host "    Start the backend first with: namo_start_backend.ps1" -ForegroundColor Yellow
    exit 1
}

# Run stress test
Write-Host ""
Write-Host "[▶] Running stress test..." -ForegroundColor Cyan
Write-Host ""

python "$testScript" $Workers $Requests

Write-Host ""
Write-Host "═════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " Test complete. Check tests\stress_test_report.json for details" -ForegroundColor Cyan
Write-Host "═════════════════════════════════════════════" -ForegroundColor Cyan
