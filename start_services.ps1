# Restart backend and frontend services in separate windows.
# Usage:  powershell -ExecutionPolicy Bypass -File .\start_services.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Stop any existing services on ports 8000 / 5173
Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

# 2. Start backend (port 8000) in its own window
Start-Process cmd.exe -ArgumentList '/k','cd /d "' + (Join-Path $root 'backend') + '" && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000' -WindowStyle Normal

# 3. Start frontend (port 5173) in its own window
Start-Process cmd.exe -ArgumentList '/k','cd /d "' + (Join-Path $root 'frontend') + '" && npm run dev' -WindowStyle Normal

Write-Output 'Backend (8000) and frontend (5173) are starting in separate windows.'
Write-Output 'Wait a few seconds, then open: http://localhost:5173'
