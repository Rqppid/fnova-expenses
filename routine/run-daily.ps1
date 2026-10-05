# Called by Windows Task Scheduler. Runs the daily expense check from the repo.
$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$env:PYTHONIOENCODING = 'utf-8'
New-Item -ItemType Directory -Force "$repo\state" | Out-Null
& "$repo\.venv\Scripts\python.exe" -m fonenova.cli daily *>> "$repo\state\daily-task.log"
