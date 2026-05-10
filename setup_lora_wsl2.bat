@echo off
REM Namo-LoRA WSL2 Setup Launcher (Batch)
REM Double-click this file or run: setup_lora_wsl2.bat

setlocal enabledelayedexpansion

title Namo-LoRA WSL2 Setup

echo.
echo ========================================
echo Namo-LoRA Training - WSL2 Setup Launcher
echo ========================================
echo.

REM Check if WSL2 is installed
echo [Check] Verifying WSL2 installation...
wsl --list --verbose >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] WSL2 not found. Please install WSL2 first:
    echo   1. Open PowerShell as Administrator
    echo   2. Run: wsl --install -d Ubuntu
    echo.
    pause
    exit /b 1
)

echo [OK] WSL2 detected
echo.
echo [Info] Launching WSL2 and running setup script...
echo.

REM Run the setup script in WSL2
set PROJECT_PATH=C:\Users\icezi\NamoNexus-Smart-Classroom
set WSL_PROJECT_PATH=/mnt/c/Users/icezi/NamoNexus-Smart-Classroom

wsl -d Ubuntu bash "%WSL_PROJECT_PATH%/setup_lora_wsl2.sh"

if errorlevel 1 (
    echo.
    echo [ERROR] Setup failed. Check messages above.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo [SUCCESS] WSL2 Setup Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Open WSL2 Ubuntu terminal:
echo      wsl -d Ubuntu
echo.
echo   2. Navigate to project:
echo      cd /mnt/c/Users/icezi/NamoNexus-Smart-Classroom
echo.
echo   3. Activate virtual environment:
echo      source .venv_linux/bin/activate
echo.
echo   4. Prepare training data:
echo      python3 tools/lora/prepare_data.py
echo.
echo   5. Start LoRA training:
echo      python3 tools/lora/train.py
echo.
pause
