# Stop backend and frontend processes started by start_services.ps1.
$ErrorActionPreference = 'SilentlyContinue'

Get-NetTCPConnection -LocalPort 8000,5173 -State Listen |
    ForEach-Object {
        $proc = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Output ("Stopping " + $proc.ProcessName + " (PID " + $proc.Id + ")")
            Stop-Process -Id $proc.Id -Force
        }
    }

Write-Output "Done. Ports 8000 and 5173 are free."
