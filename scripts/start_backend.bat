@echo off
chcp 65001 > nul
set PYTHONPATH=%~dp0backend
cd /d "%~dp0"
"C:\Users\icezi\Downloads\Github repo\namo_core_project\.venv\Scripts\python.exe" -m uvicorn namo_core.api.app:app --host 127.0.0.1 --port 8000 >> "%~dp0logs\backend_error.log" 2>&1
