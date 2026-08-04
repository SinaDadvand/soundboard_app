@echo off
cd /d "%~dp0"

echo Starting Virtual Soundboard...
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install/update requirements
echo Installing dependencies...
pip install -r requirements.txt

REM Run the app
echo.
echo Starting soundboard application...
python app.py

pause
