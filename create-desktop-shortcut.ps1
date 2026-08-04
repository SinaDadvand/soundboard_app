# PowerShell script to create a desktop shortcut for the soundboard
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$([Environment]::GetFolderPath('Desktop'))\Virtual Soundboard.lnk")
$Shortcut.TargetPath = "C:\Users\sinadvd\Soundboard\soundboard_app\dist\VirtualSoundboard.exe"
$Shortcut.WorkingDirectory = "C:\Users\sinadvd\Soundboard\soundboard_app\dist"
$Shortcut.Description = "Virtual Soundboard - Standalone Executable with Neon V Icon"
$Shortcut.IconLocation = "C:\Users\sinadvd\Soundboard\soundboard_app\neon_v_soundboard_icon.ico"
$Shortcut.Save()

Write-Host "Desktop shortcut created successfully!" -ForegroundColor Green
Write-Host "You can now double-click 'Virtual Soundboard' on your desktop to run the app." -ForegroundColor Yellow
