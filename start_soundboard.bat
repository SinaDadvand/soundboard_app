@echo off
echo ====================================================
echo Starting Soundboard with Global Hotkeys
echo ====================================================
echo.

REM Check if Docker is running
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running or not installed
    echo Please start Docker Desktop and try again
    pause
    exit /b 1
)

echo 1. Starting containerized soundboard...
docker-compose up -d

REM Wait for container to be ready
echo 2. Waiting for container to start...
timeout /t 5 /nobreak >nul

REM Check if container is running
docker-compose ps | findstr "Up" >nul
if errorlevel 1 (
    echo ERROR: Failed to start soundboard container
    echo Check docker-compose logs for details
    pause
    exit /b 1
)

echo 3. Container started successfully!
echo 4. Starting global hotkey client...
echo.

REM Check if virtual environment exists for hotkey client
if not exist "venv_hotkeys" (
    echo Setting up hotkey client environment...
    python -m venv venv_hotkeys
    call venv_hotkeys\Scripts\activate
    pip install -r requirements_hotkey_client.txt
) else (
    call venv_hotkeys\Scripts\activate
)

echo 5. Starting global hotkeys (this window must stay open)...
echo.
echo ====================================================
echo INSTRUCTIONS:
echo - Web interface: http://localhost:5000
echo - Global hotkeys are now active
echo - Keep this window open for hotkeys to work
echo - Press Ctrl+C to stop everything
echo ====================================================
echo.

python hotkey_client.py

REM Cleanup when hotkey client exits
echo.
echo Stopping soundboard container...
docker-compose down
echo Done!
pause
