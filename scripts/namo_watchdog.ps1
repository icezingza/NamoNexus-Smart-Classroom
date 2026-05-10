$projectDir = 'C:\Users\icezi\NamoNexus-Smart-Classroom'
$logFile    = Join-Path $projectDir "logs\watchdog.log"
$pidFile    = Join-Path $projectDir "logs\.pids"

function Log-Message {
    param([string]$msg)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMsg = "[$timestamp] $msg"

    if (Test-Path $logFile) {
        if ((Get-Item $logFile).Length -gt 1MB) { Clear-Content $logFile }
    }
    if (-not (Test-Path (Split-Path $logFile))) {
        New-Item -ItemType Directory -Path (Split-Path $logFile) -Force | Out-Null
    }
    Add-Content -Path $logFile -Value $logMsg
    Write-Host $logMsg
}

function Test-BackendHealth {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" `
            -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        return $r.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Test-PortListening {
    param([int]$Port)
    return $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

Log-Message "=== Watchdog cycle started ==="

# -- Backend health check (HTTP health first, then port) ----------------------
$backendHealthy = Test-BackendHealth
if (-not $backendHealthy) {
    $portUp = Test-PortListening -Port 8000
    if (-not $portUp) {
        Log-Message "[!] Backend not responding on port 8000. Restarting..."
        powershell -ExecutionPolicy Bypass -File "$projectDir\scripts\namo_start_all.ps1" -ApiOnly
    } else {
        Log-Message "[WARN] Port 8000 up but /health failed - backend may be loading (normal cold start)"
    }
} else {
    $uvicornConn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($uvicornConn) {
        $uvicornProc = Get-Process -Id $uvicornConn.OwningProcess -ErrorAction SilentlyContinue
        $ram = if ($uvicornProc) { [math]::Round($uvicornProc.WorkingSet64 / 1MB, 1) } else { "?" }
        Log-Message "[OK] Backend healthy - port 8000 alive, PID $($uvicornConn.OwningProcess), RAM ${ram}MB"
    } else {
        Log-Message "[OK] Backend healthy - /health returned 200"
    }
}

# -- Tunnel check -------------------------------------------------------------
if (Test-Path $pidFile) {
    try {
        $savedPids = Get-Content $pidFile | ConvertFrom-Json
        $tunnelPid = [int]$savedPids.tunnel
        if ($tunnelPid -gt 4) {
            $tunnelProc = Get-Process -Id $tunnelPid -ErrorAction SilentlyContinue
            if ($null -eq $tunnelProc) {
                Log-Message "[WARN] Cloudflare tunnel (PID $tunnelPid) is gone - run namo_start_all.ps1 to restart"
            } else {
                Log-Message "[OK] Tunnel alive (PID $tunnelPid)"
            }
        } else {
            Log-Message "[INFO] Tunnel not managed via PID file (run namo_start_all.ps1 to start with tunnel)"
        }
    } catch {
        Log-Message "[ERROR] PID file read failed: $($_.Exception.Message)"
    }
} else {
    Log-Message "[WARN] No PID file at $pidFile - run namo_start_all.ps1 first"
}

Log-Message "=== Watchdog cycle completed ==="
