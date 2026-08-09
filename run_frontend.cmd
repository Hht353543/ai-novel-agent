@echo off
rem Start frontend detached (logs in ..\logs\)
cd /d %~dp0frontend
start /b npm run dev > "%~dp0..\logs\frontend.out.log" 2> "%~dp0..\logs\frontend.err.log"
