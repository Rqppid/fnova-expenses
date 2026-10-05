# One-time: register the daily expense check in Windows Task Scheduler (runs as you, 21:30 daily,
# catches up if the PC was off, only when logged on so OneDrive is syncing).
# Run in PowerShell:  powershell -ExecutionPolicy Bypass -File routine\register-task.ps1
$repo = Split-Path -Parent $PSScriptRoot
$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$repo\routine\run-daily.ps1`""
$trigger = New-ScheduledTaskTrigger -Daily -At 21:30
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'FoneNova Daily Expense Check' -Action $action -Trigger $trigger `
    -Settings $settings -Description 'Gmail + receipts folders -> VAT tracker (fonenova-expenses repo)' -Force
Write-Host "Registered. Test now with: Start-ScheduledTask -TaskName 'FoneNova Daily Expense Check'"
