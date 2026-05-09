# Get path relative to this script
$scriptDir = $PSScriptRoot
$projectDir = Split-Path -Parent $scriptDir
$watchdogScript = Join-Path $scriptDir "namo_watchdog.ps1"
$logDir = Join-Path $projectDir "logs"

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

Write-Host "[*] Setting up Namo Core Watchdog Monitoring (Dynamic Path)..." -ForegroundColor Cyan

# สร้างเนื้อหา watchdog แบบ Dynamic
$watchdogContent = @"
`$projectDir = '$projectDir'
`$logFile = Join-Path `$projectDir "logs\watchdog.log"
`$pidFile = Join-Path `$projectDir "logs\.pids"

function Log-Message {
    param([string]`$msg)
    `$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    `$logMsg = "[`$timestamp] `$msg"
    if (-not (Test-Path (Split-Path `$logFile))) { New-Item -ItemType Directory -Path (Split-Path `$logFile) -Force | Out-Null }
    Add-Content -Path `$logFile -Value `$logMsg
    Write-Host `$logMsg
}

Log-Message "=== Watchdog cycle started ==="
if (Test-Path `$pidFile) {
    try {
        `$pids = Get-Content `$pidFile | ConvertFrom-Json
        if (`$pids -and `$pids.backend -gt 0) {
            `$proc = Get-Process -Id `$pids.backend -ErrorAction SilentlyContinue
            if (`$null -eq `$proc) {
                Log-Message "[!] Backend (PID `$(`$pids.backend)) is NOT running. Restarting..."
                powershell -ExecutionPolicy Bypass -File "`$projectDir\scripts\namo_start_all.ps1" -ApiOnly
            } else {
                `$mem = [math]::Round(`$proc.WorkingSet64 / 1MB, 2)
                Log-Message "[OK] Backend is healthy (PID `$(`$pids.backend), RAM `$(`$mem)MB)"
            }
        }
    } catch {
        Log-Message "[ERROR] Failed to check status: `$(`$_.Exception.Message)"
    }
} else { 
    Log-Message "[WARN] No PID file found at `$pidFile" 
}
Log-Message "=== Watchdog cycle completed ==="
"@

$watchdogContent | Out-File -FilePath $watchdogScript -Encoding UTF8 -Force
Write-Host "[OK] Created watchdog script at $watchdogScript" -ForegroundColor Green

# ลงทะเบียน Task
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$watchdogScript`""
$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 2) -Once -At (Get-Date)
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0 -MultipleInstances IgnoreNew -RunOnlyIfNetworkAvailable

try {
    if ($null -eq $action) { throw "Variable `$action is not defined. Make sure New-ScheduledTaskAction was called." }
    Register-ScheduledTask -TaskName "Namo Core Watchdog" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force -ErrorAction Stop | Out-Null
    Write-Host "[OK] Watchdog registered successfully to: $projectDir" -ForegroundColor Green
}
catch {
    if ($_.Exception.Message -match "Access is denied") {
        Write-Host "[X] ERROR: Access Denied!" -ForegroundColor Red
        Write-Host "Please make sure you are running PowerShell as ADMINISTRATOR." -ForegroundColor Yellow
    }
    else {
        Write-Host "[X] ERROR: Registration failed." -ForegroundColor Red
        Write-Host "Details: $($_.Exception.Message)" -ForegroundColor Gray
    }
    exit 1
}