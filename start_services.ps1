# Restart backend and frontend services as hidden background processes.
# Usage:  powershell -ExecutionPolicy Bypass -File .\start_services.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $env:TEMP 'ai_novel_agent_service_pids.txt'

# 1. Stop only the services previously started by this script (recorded PIDs)
if (Test-Path $pidFile) {
    Get-Content $pidFile | ForEach-Object {
        $pidValue = $_
        if ($pidValue -match '^\d+$') {
            $proc = Get-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Output ("Stopping previous service: " + $proc.ProcessName + " (PID " + $proc.Id + ")")
                taskkill /PID $pidValue /T /F 2>$null | Out-Null
            }
        }
    }
    Remove-Item $pidFile -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 1

# 2. Start backend (port 8000) hidden
$backend = Start-Process -FilePath 'python' -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory (Join-Path $root 'backend') -WindowStyle Hidden -PassThru

# 3. Start frontend (port 5173) hidden
$frontend = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run','dev' -WorkingDirectory (Join-Path $root 'frontend') -WindowStyle Hidden -PassThru

@($backend.Id, $frontend.Id) | Set-Content $pidFile -Encoding UTF8

Write-Output 'Backend (8000) and frontend (5173) are starting in the background.'
Write-Output 'PIDs recorded; use stop_services.ps1 to stop them.'
Write-Output 'Wait a few seconds, then open: http://localhost:5173'
