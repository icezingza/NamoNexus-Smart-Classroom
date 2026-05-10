# Namo-LoRA WSL2 Setup Launcher (PowerShell)
# Run with: powershell -ExecutionPolicy Bypass -File setup_lora_wsl2.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Namo-LoRA Training — WSL2 Setup Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if WSL2 is installed
Write-Host "[Check] Verifying WSL2 installation..." -ForegroundColor Yellow
$wslCheck = wsl --list --verbose 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ WSL2 not found. Please install WSL2 first:" -ForegroundColor Red
    Write-Host "  1. Open PowerShell as Administrator"
    Write-Host "  2. Run: wsl --install -d Ubuntu"
    exit 1
}

# Check if Ubuntu is available
if ($wslCheck -like "*Ubuntu*") {
    Write-Host "✓ WSL2 with Ubuntu detected" -ForegroundColor Green
} else {
    Write-Host "⚠️  Ubuntu distribution not found in WSL2" -ForegroundColor Yellow
    Write-Host "Installing Ubuntu... (this may take a few minutes)"
    wsl --install -d Ubuntu
}

Write-Host ""
Write-Host "[Info] Launching WSL2 and running setup script..." -ForegroundColor Yellow
Write-Host ""

# Run the setup script in WSL2 Ubuntu
$projectPath = "C:\Users\icezi\NamoNexus-Smart-Classroom"
$wslProjectPath = "/mnt/c/Users/icezi/NamoNexus-Smart-Classroom"

# Execute setup in WSL2
wsl -d Ubuntu bash "$wslProjectPath/setup_lora_wsl2.sh"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✓ WSL2 Setup Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Open WSL2 Ubuntu terminal:"
    Write-Host "     wsl -d Ubuntu"
    Write-Host ""
    Write-Host "  2. Navigate to project:"
    Write-Host "     cd /mnt/c/Users/icezi/NamoNexus-Smart-Classroom"
    Write-Host ""
    Write-Host "  3. Activate virtual environment:"
    Write-Host "     source .venv_linux/bin/activate"
    Write-Host ""
    Write-Host "  4. Prepare training data:"
    Write-Host "     python3 tools/lora/prepare_data.py"
    Write-Host ""
    Write-Host "  5. Start LoRA training:"
    Write-Host "     python3 tools/lora/train.py"
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Setup failed. Check error messages above." -ForegroundColor Red
    exit 1
}
