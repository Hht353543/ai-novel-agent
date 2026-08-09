@echo off
rem Check whether the backend on port 8000 is alive.
echo Checking http://localhost:8000/api/health ...
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 5 -UseBasicParsing; Write-Host ('BACKEND OK - HTTP ' + $r.StatusCode) } catch { Write-Host ('BACKEND DOWN - ' + $_.Exception.Message) }"
pause
