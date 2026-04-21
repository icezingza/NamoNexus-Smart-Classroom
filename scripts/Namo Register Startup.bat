@echo off
:: Re-launch as Administrator if not already elevated
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    cd /d "%~dp0.."
powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

powershell -ExecutionPolicy Bypass -File "%~dp0register_startup.ps1"
pause
