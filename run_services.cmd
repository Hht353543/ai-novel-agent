@echo off
rem Start backend detached (logs in ..\logs\)
cd /d %~dp0backend
start /b python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > "%~dp0..\logs\backend.out.log" 2> "%~dp0..\logs\backend.err.log"
