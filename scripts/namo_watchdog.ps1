$projectDir = "C:\Users\icezi\Downloads\Github repo\namo_core_project"
$logFile = "$projectDir\logs\watchdog.log"
$pidFile = "$projectDir\.pid"

function Log-Message {
    param([string]$msg)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMsg = "[$timestamp] $msg"
    Add-Content -Path $logFile -Value $logMsg
    Write-Host $logMsg
}

Log-Message "=== Watchdog cycle started ==="

if (Test-Path $pidFile) {
    $pid = Get-Content $pidFile -Raw -ErrorAction SilentlyContinue
    $pid = $pid.Trim()

    if ($pid -match '^\d+$') {
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue

        if ($proc) {
            $memMB = [math]::Round($proc.WorkingSet64 / 1MB, 2)
            Log-Message "OK Backend running (PID=$pid, RAM=${memMB}MB)"
        } else {
            Log-Message "WARN Backend crashed! PID=$pid not found. Restarting..."
            Remove-Item $pidFile -Force -ErrorAction SilentlyContinue

            try {
                Start-Process -FilePath "powershell.exe" `
                    -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$projectDir\scripts\namo_start_backend.ps1`"" `
                    -WindowStyle Hidden
                Log-Message "OK Backend restart command issued"
                Start-Sleep -Seconds 5
            } catch {
                Log-Message "ERROR Failed to restart backend: $_"
            }
        }
    }
} else {
    Log-Message "WARN PID file not found"
}

Log-Message "=== Watchdog cycle completed ==="
