# Stop backend and frontend processes started by start_services.ps1.
$ErrorActionPreference = 'SilentlyContinue'

$pidFile = Join-Path $env:TEMP 'ai_novel_agent_service_pids.txt'
if (-not (Test-Path $pidFile)) {
    Write-Output 'No service PID file found. Nothing to stop.'
    return
}

Get-Content $pidFile | ForEach-Object {
    $pidValue = $_
    if ($pidValue -match '^\d+$') {
        $proc = Get-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Output ("Stopping " + $proc.ProcessName + " (PID " + $proc.Id + ")")
            taskkill /PID $pidValue /T /F 2>$null | Out-Null
        }
    }
}
Remove-Item $pidFile -ErrorAction SilentlyContinue
Write-Output 'Done. Services started by this script are stopped.'
