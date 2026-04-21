@echo off
chcp 65001 > nul
:: %~dp0 resolves to this script's directory (scripts\), go up one level for project root
set PROJECT_DIR=%~dp0..
set PYTHONPATH=%PROJECT_DIR%\backend
set VENV_PYTHON=%PROJECT_DIR%\.venv\Scripts\python.exe

cd /d "%PROJECT_DIR%"

if not exist "%VENV_PYTHON%" (
    echo [WARN] .venv not found at: %VENV_PYTHON%
    echo Run install_windows.ps1 first.
    pause
    exit /b 1
)

"%VENV_PYTHON%" -m uvicorn namo_core.api.app:app --host 127.0.0.1 --port 8000 >> "%PROJECT_DIR%\logs\backend_error.log" 2>&1
