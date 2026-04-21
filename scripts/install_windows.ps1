# =============================================================================
# Namo Core — Windows One-Time Installation Script
# Phase 8: Deployment
#
# Run once on a fresh machine to set up the full environment.
# Execute from the project root:
#   powershell -ExecutionPolicy Bypass -File .\scripts\install_windows.ps1
# =============================================================================

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Namo Core — Installation (Windows)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------------------
# Step 1: Python version check
# ---------------------------------------------------------------------------
Write-Host "[1/6] Checking Python version..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Python not found. Install Python 3.10+ from https://python.org" -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# Step 2: Create virtual environment
# ---------------------------------------------------------------------------
Write-Host "[2/6] Creating Python virtual environment..." -ForegroundColor Yellow
$venvPath = Join-Path $Root ".venv"
if (Test-Path $venvPath) {
    Write-Host "  .venv already exists — skipping creation." -ForegroundColor Gray
} else {
    python -m venv $venvPath
    Write-Host "  Created: $venvPath" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# Step 3: Install Python dependencies
# ---------------------------------------------------------------------------
Write-Host "[3/6] Installing Python dependencies..." -ForegroundColor Yellow
$pip = Join-Path $venvPath "Scripts\pip.exe"
$requirementsPath = Join-Path $Root "namo_core\requirements.txt"
& $pip install --upgrade pip -q
& $pip install -r $requirementsPath
Write-Host "  Dependencies installed." -ForegroundColor Green

# ---------------------------------------------------------------------------
# Step 4: Node.js check + frontend install
# ---------------------------------------------------------------------------
Write-Host "[4/6] Installing frontend dependencies..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "  Found Node.js: $nodeVersion" -ForegroundColor Green
    $dashboardPath = Join-Path $Root "dashboard"
    Push-Location $dashboardPath
    npm install --silent
    Pop-Location
    Write-Host "  Frontend dependencies installed." -ForegroundColor Green
} catch {
    Write-Host "  WARNING: Node.js not found. Dashboard will not be available." -ForegroundColor Yellow
    Write-Host "  Install from https://nodejs.org if you need the dashboard." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Step 5: Copy .env.example → .env (if not exists)
# ---------------------------------------------------------------------------
Write-Host "[5/6] Configuring environment..." -ForegroundColor Yellow
$envFile = Join-Path $Root ".env"
$envExample = Join-Path $Root ".env.example"
if (Test-Path $envFile) {
    Write-Host "  .env already exists — skipping copy." -ForegroundColor Gray
} else {
    Copy-Item $envExample $envFile
    Write-Host "  Created .env from .env.example" -ForegroundColor Green
    Write-Host "  IMPORTANT: Edit .env to configure your API keys and settings." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Step 6: Create data directories
# ---------------------------------------------------------------------------
Write-Host "[6/6] Creating runtime directories..." -ForegroundColor Yellow
$dirs = @(
    (Join-Path $Root "namo_core\data"),
    (Join-Path $Root "backups"),
    (Join-Path $Root "logs")
)
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Write-Host "  Created: $dir" -ForegroundColor Green
    }
}

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Installation complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit .env with your LLM API keys (if using real LLM)" -ForegroundColor White
Write-Host "  2. Run: powershell -ExecutionPolicy Bypass -File .\scripts\start_windows.ps1" -ForegroundColor White
Write-Host ""
