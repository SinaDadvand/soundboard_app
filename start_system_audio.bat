@echo off
echo ========================================================
echo Soundboard with TRUE Global Hotkeys (System Audio)
echo ========================================================
echo This version plays audio directly through your system
echo No browser focus limitations!
echo ========================================================
echo.

echo 1. Starting Docker container...
docker-compose up -d

echo 2. Waiting for container to be ready...
timeout /t 5 /nobreak > nul

echo 3. Checking container status...
docker ps | findstr soundboard

echo 4. Optional: Opening web interface...
start http://localhost:5000

echo 5. Starting SYSTEM AUDIO hotkey client...
echo.
echo =====================================================
echo IMPORTANT: This client plays audio directly through
echo your system speakers/headphones using pygame.
echo 
echo No browser focus needed!
echo =====================================================
echo.
echo Available hotkeys:
echo - Ctrl + numbers (1-9, 0, .)
echo - Alt + numbers (1-9, 0, .)  
echo - Ctrl + Alt + 7, 8 (your requested third group!)
echo.
echo The client will download and cache all audio files
echo for instant playback...
echo.
pause
echo Starting system audio hotkey client...
echo Using virtual environment...
"C:/Users/sinad/VS Code/soundboard-app_2/venv/Scripts/python.exe" hotkey_client_system_audio.py

echo.
echo System audio hotkey client stopped.
pause
