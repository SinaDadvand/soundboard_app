@echo off
echo Starting Virtual Soundboard Executable...
cd /d "C:\Users\sinadvd\Soundboard\soundboard_app\dist"

REM Start the executable in background
start "" "VirtualSoundboard.exe"

REM Wait a moment for the server to start
timeout /t 5 /nobreak >nul

REM Open the browser
echo Opening browser...
start http://localhost:5001

echo Virtual Soundboard is now running!
echo Keep this window open while using the soundboard
echo Press any key to exit...
pause >nul
