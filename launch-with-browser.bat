@echo off
setlocal

REM Set window title
title Virtual Soundboard - Auto Launch

REM Change to the soundboard directory
cd /d "%~dp0"

REM Setup virtual environment and dependencies (quiet)
if not exist "venv" (
    echo Setting up environment...
    python -m venv venv
)

call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet

REM Start the app in background and open browser
echo Starting soundboard...
start /b python app.py

REM Wait a moment for the server to start
timeout /t 3 /nobreak >nul

REM Open the browser
echo Opening browser...
start http://localhost:5001/?v=%RANDOM%

REM Keep the window open to show server output
echo.
echo ================================================
echo     SOUNDBOARD IS RUNNING
echo ================================================
echo Browser opened at: http://localhost:5000
echo.
echo Keep this window open while using the soundboard
echo Press Ctrl+C to stop the application
echo ================================================
echo.

REM Wait for the python process to finish
:wait
tasklist /fi "imagename eq python.exe" 2>nul | find /i "python.exe" >nul
if "%errorlevel%"=="0" (
    timeout /t 5 /nobreak >nul
    goto wait
)

echo Soundboard stopped.
pause
