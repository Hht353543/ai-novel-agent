@echo off
rem Run backend in foreground so you can see any startup error.
cd /d %~dp0backend
echo ============================================
echo  If you see "Uvicorn running on http://127.0.0.1:8000"
echo  the backend is OK. Otherwise copy the error below.
echo ============================================
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
echo.
echo Backend stopped. Press any key to close...
pause
