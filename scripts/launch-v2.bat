@echo off
title Virtual Soundboard 2 Launcher
cd /d "%~dp0.."
echo ======================================================
echo    Starting Virtual Soundboard 2 Standalone Executable
echo ======================================================
if exist "dist\VirtualSoundboard2.exe" (
    start "" "dist\VirtualSoundboard2.exe"
) else (
    echo Error: dist\VirtualSoundboard2.exe not found!
    pause
)
