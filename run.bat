@echo off
title AI Resume Assistant
echo Starting AI Resume Assistant...
echo.

REM Server starts in this script's own directory
start "AI Resume Assistant Server" /min .venv\Scripts\python.exe -m uvicorn app:app --port 8000

echo Waiting for server to load...
set /a count=0
:wait_loop
timeout /t 2 /nobreak >nul
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri http://127.0.0.1:8000/login -UseBasicParsing -TimeoutSec 3 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 goto :ready
set /a count+=1
if %count% lss 30 goto :wait_loop
echo Server took too long to start.
pause
exit /b 1

:ready
echo Server is running at http://127.0.0.1:8000
start http://127.0.0.1:8000/login
echo.
echo To stop, close the server window.
pause