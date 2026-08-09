@echo off
echo ============================================
echo   AI Novel Agent - One-click Start
echo ============================================
echo.
echo [1/2] Starting backend (http://localhost:8000) ...
start "AI-Novel-Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
echo [2/2] Starting frontend (http://localhost:5173) ...
start "AI-Novel-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
echo.
echo Open http://localhost:5173 in browser.
echo Backend API docs: http://localhost:8000/docs
echo Close a window to stop its service.
timeout /t 5 >nul
