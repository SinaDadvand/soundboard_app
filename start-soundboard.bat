@echo off
setlocal

REM Set window title
title Virtual Soundboard Launcher

REM Change to the soundboard directory
cd /d "c:\Users\sinadvd\Soundboard\soundboard_app"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python and try again.
    pause
    exit /b 1
)

REM Check if virtual environment exists, create if not
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment
    pause
    exit /b 1
)

REM Install/update requirements
echo Checking dependencies...
pip install -r requirements.txt --quiet

REM Clear screen and start the app
cls
echo.
echo ================================================
echo          VIRTUAL SOUNDBOARD STARTING
echo ================================================
echo.
echo The soundboard will be available at:
echo http://localhost:5000
echo.
echo Press Ctrl+C to stop the application
echo ================================================
echo.

REM Run the application
python app.py
