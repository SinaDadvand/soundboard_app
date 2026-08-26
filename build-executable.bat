@echo off
title Build Soundboard Launcher Executable
cd /d "%~dp0"
echo =========================================================
echo    Building Virtual Soundboard Standalone Executable
echo =========================================================
python -m PyInstaller VirtualSoundboard2.spec --clean --noconfirm
echo.
if exist "dist\VirtualSoundboard2.exe" (
    echo =========================================================
    echo [SUCCESS] Build Complete!
    echo Output: dist\VirtualSoundboard2.exe
    echo =========================================================
) else (
    echo [ERROR] Build failed! Check the output above.
)
pause
