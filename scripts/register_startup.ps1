# Register Namo Core as Windows Startup Task (runs at logon)
$scriptPath = "C:\Users\icezi\Downloads\Github repo\namo_core_project\scripts\namo_start_all.ps1"

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""

$trigger  = New-ScheduledTaskTrigger -AtLogOn -User "icezi"
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0 -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName "Namo Core Startup" `
    -Action   $action `
    -Trigger  $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Force

Write-Host "[OK] Task registered: 'Namo Core Startup' will run at every logon." -ForegroundColor Green
