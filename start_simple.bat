@echo off
echo =====================================================
echo Starting Soundboard with Global Hotkeys (Simple)
echo =====================================================
echo.

echo 1. Starting Docker container...
docker-compose up -d

echo 2. Waiting for container to be ready...
timeout /t 3 /nobreak > nul

echo 3. Opening browser...
start http://localhost:5000

echo 4. Starting hotkey client...
echo.
echo IMPORTANT INSTRUCTIONS:
echo 1. Click anywhere on the soundboard page that just opened
echo 2. You can minimize the browser window (but keep the tab open)
echo 3. Now you can use hotkeys from any application!
echo.
echo Hotkeys available:
echo - Ctrl + numbers (1-9, 0, .)
echo - Alt + numbers (1-9, 0, .)  
echo - Ctrl + Alt + 7, 8 (your requested third group!)
echo.
echo Starting global hotkey client...
python hotkey_client.py

echo.
echo Hotkey client stopped.
pause
