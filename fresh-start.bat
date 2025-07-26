@echo off
echo Stopping any existing Python processes...
taskkill /f /im python.exe 2>nul

echo Clearing browser cache directories...
REM Clear Chrome cache
if exist "%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache" (
    rd /s /q "%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache" 2>nul
)

REM Clear Edge cache  
if exist "%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache" (
    rd /s /q "%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache" 2>nul
)

echo Starting fresh soundboard on port 5001...
call launch-with-browser.bat
