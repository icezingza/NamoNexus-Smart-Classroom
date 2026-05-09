$projectDir = 'C:\Users\icezi\NamoNexus-Smart-Classroom'
$logFile = Join-Path $projectDir "logs\watchdog.log"
$pidFile = Join-Path $projectDir "logs\.pids"

function Log-Message {
    param([string]$msg)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMsg = "[$timestamp] $msg"
    
    # Log Rotation: If log > 1MB, clear it
    if (Test-Path $logFile) {
        if ((Get-Item $logFile).Length -gt 1MB) { Clear-Content $logFile }
    }

    if (-not (Test-Path (Split-Path $logFile))) { New-Item -ItemType Directory -Path (Split-Path $logFile) -Force | Out-Null }
    Add-Content -Path $logFile -Value $logMsg
    Write-Host $logMsg
}

Log-Message "=== Watchdog cycle started ==="
if (Test-Path $pidFile) {
    try {
        $pids = Get-Content $pidFile | ConvertFrom-Json
        if ($pids -and $pids.backend -gt 0) {
            $proc = Get-Process -Id $pids.backend -ErrorAction SilentlyContinue
            if ($null -eq $proc) {
                Log-Message "[!] Backend (PID $($pids.backend)) is NOT running. Restarting..."
                powershell -ExecutionPolicy Bypass -File "$projectDir\scripts\namo_start_all.ps1" -ApiOnly
            }
            else {
                $mem = [math]::Round($proc.WorkingSet64 / 1MB, 2)
                Log-Message "[OK] Backend is healthy (PID $($pids.backend), RAM $($mem)MB)"
            }
        }
    }
    catch {
        Log-Message "[ERROR] Failed to check status: $($_.Exception.Message)"
    }
}
else { 
    Log-Message "[WARN] No PID file found at $pidFile" 
}
Log-Message "=== Watchdog cycle completed ==="
