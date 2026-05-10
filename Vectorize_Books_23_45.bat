@echo off
REM Vectorize Books 23-45 and append to existing FAISS index
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ============================================================
echo  P25: Vectorize Books 23-45 Pipeline
echo ============================================================
echo.

echo [1/2] Standardizing Books 23-45...
python scripts/standardize_books_23_45.py
if errorlevel 1 (
    echo ERROR: Standardization failed!
    pause
    exit /b 1
)

echo.
echo [2/2] Vectorizing and appending to FAISS index...
echo (This may take 1-2 minutes depending on CPU)
echo.
python scripts/vectorize_and_append_books_23_45.py
if errorlevel 1 (
    echo ERROR: Vectorization failed!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  ✅ P25 Complete - Books 23-45 vectorized and appended
echo ============================================================
echo.
pause
