@echo off
:: ============================================================
:: NamoNexus Smart Classroom -- One-Click Launcher
:: Opens the Teacher Dashboard in one click from the Desktop.
::
:: Startup order (each step waits for the previous to be ready):
::   1. Redis       -- via WSL2 Ubuntu (port 6379)
::   2. Backend     -- FastAPI on port 8000
::   3. Frontend    -- Vite dev server on port 5173
::   4. Browser     -- opens http://localhost:5173/teacher
:: ============================================================

title NamoNexus -- Starting...
setlocal EnableDelayedExpansion

:: Resolve project root (one level up from scripts\)
set "ROOT=%~dp0.."
pushd "%ROOT%"

set "VENV_PYTHON=%ROOT%\.venv\Scripts\python.exe"
set "LOG_DIR=%ROOT%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo.
echo  =============================================
echo   NamoNexus Smart Classroom  -- Starting
echo  =============================================
echo.

:: --------------------------------------------------------
:: STEP 1: Redis (WSL2)
:: --------------------------------------------------------
echo  [1/4] Starting Redis...

:: Quick check -- is Redis already up?
powershell -NoProfile -Command ^
  "try { $t=New-Object Net.Sockets.TcpClient; $t.Connect('127.0.0.1',6379); $t.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL%==0 (
    echo        Redis: ALREADY RUNNING
    goto redis_ok
)

:: Start Redis inside WSL2 Ubuntu as root (no password prompt)
wsl -d Ubuntu -u root -- service redis-server start >nul 2>&1

:: Poll Redis -- up to 10 seconds
set /a redis_tries=0
:redis_poll
timeout /t 1 /nobreak >nul
powershell -NoProfile -Command ^
  "try { $t=New-Object Net.Sockets.TcpClient; $t.Connect('127.0.0.1',6379); $t.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL%==0 goto redis_ok
set /a redis_tries+=1
if !redis_tries! LSS 10 goto redis_poll
echo        WARNING: Redis not responding -- WebSocket PubSub may be degraded.
echo        Fix: wsl -d Ubuntu -u root -- service redis-server start
goto redis_done
:redis_ok
echo        Redis: ONLINE
:redis_done

:: --------------------------------------------------------
:: STEP 2: Backend (FastAPI -- port 8000)
:: --------------------------------------------------------
echo  [2/4] Starting Backend...

:: Already running?
powershell -NoProfile -Command ^
  "try { $t=New-Object Net.Sockets.TcpClient; $t.Connect('127.0.0.1',8000); $t.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL%==0 (
    echo        Backend: ALREADY RUNNING
    goto backend_ok
)

:: Launch uvicorn in a new minimised window so it stays alive
start "NamoNexus Backend" /min cmd /c ^
  ""%VENV_PYTHON%" -m namo_core.main > "%LOG_DIR%\backend.log" 2> "%LOG_DIR%\backend_error.log""

:: Poll backend -- up to 30 seconds (model load on first start takes ~8s)
set /a backend_tries=0
:backend_poll
timeout /t 1 /nobreak >nul
powershell -NoProfile -Command ^
  "try { $r=(Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 2 -EA Stop).StatusCode; exit ($r -eq 200 ? 0 : 1) } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL%==0 goto backend_ok
set /a backend_tries+=1
if !backend_tries! LSS 30 goto backend_poll
echo        ERROR: Backend did not start in 30s.
echo        Check logs\backend_error.log for details.
pause
goto end
:backend_ok
echo        Backend: READY  (http://127.0.0.1:8000)

:: --------------------------------------------------------
:: STEP 3: Frontend (Vite -- port 5173)
:: --------------------------------------------------------
echo  [3/4] Starting Frontend...

:: Already running?
powershell -NoProfile -Command ^
  "try { $t=New-Object Net.Sockets.TcpClient; $t.Connect('127.0.0.1',5173); $t.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL%==0 (
    echo        Frontend: ALREADY RUNNING
    goto frontend_ok
)

:: Launch Vite dev server in a new minimised window
start "NamoNexus Frontend" /min cmd /c ^
  "cd /d "%ROOT%\frontend" && cmd.exe /c npm.cmd run dev > "%LOG_DIR%\frontend.log" 2>&1"

:: Poll frontend -- up to 20 seconds
set /a frontend_tries=0
:frontend_poll
timeout /t 1 /nobreak >nul
powershell -NoProfile -Command ^
  "try { $t=New-Object Net.Sockets.TcpClient; $t.Connect('127.0.0.1',5173); $t.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL%==0 goto frontend_ok
set /a frontend_tries+=1
if !frontend_tries! LSS 20 goto frontend_poll
echo        WARNING: Frontend not responding -- opening anyway.
:frontend_ok
echo        Frontend: READY (http://localhost:5173)

:: --------------------------------------------------------
:: STEP 4: Open Teacher Dashboard
:: --------------------------------------------------------
echo  [4/4] Opening Teacher Dashboard...
timeout /t 1 /nobreak >nul
start "" "http://localhost:5173/teacher"

echo.
echo  =============================================
echo   NamoNexus is LIVE!
echo   Dashboard  : http://localhost:5173/teacher
echo   API        : http://127.0.0.1:8000
echo   API Docs   : http://127.0.0.1:8000/docs
echo  =============================================
echo.
echo  This window can be closed. Services run in background.
echo  To stop all: run scripts\Namo Stop.bat
echo.

:end
popd
:: Brief pause so the user can read the summary (no stdin required)
ping -n 6 127.0.0.1 >nul 2>&1
