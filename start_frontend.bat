@echo off
cd /d %~dp0frontend
echo Starting frontend: http://localhost:5173 (close this window to stop)
npm run dev
