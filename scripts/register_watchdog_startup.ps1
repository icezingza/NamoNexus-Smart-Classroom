# Register Namo Core Watchdog Monitor
$projectDir = "C:\Users\icezi\Downloads\Github repo\namo_core_project"
$watchdogScript = "$projectDir\scripts\namo_watchdog.ps1"
$logDir = "$projectDir\logs"

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

Write-Host "[*] Setting up Namo Core Watchdog Monitoring..." -ForegroundColor Cyan

$watchdogContent = @'
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
'@

$watchdogContent | Out-File -FilePath $watchdogScript -Encoding UTF8 -Force
Write-Host "[OK] Created watchdog script" -ForegroundColor Green

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$watchdogScript`""

$trigger = New-ScheduledTaskTrigger `
    -RepetitionInterval (New-TimeSpan -Minutes 2) `
    -Once -At (Get-Date)

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit 0 `
    -MultipleInstances IgnoreNew `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask `
    -TaskName "Namo Core Watchdog" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Force | Out-Null

Write-Host "[OK] Watchdog registered successfully" -ForegroundColor Green
Write-Host "     Task: Namo Core Watchdog" -ForegroundColor Green
Write-Host "     Interval: Every 2 minutes" -ForegroundColor Green
