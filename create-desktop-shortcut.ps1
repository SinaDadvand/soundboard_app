# PowerShell script to create a desktop shortcut for the soundboard
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$([Environment]::GetFolderPath('Desktop'))\Virtual Soundboard.lnk")
$Shortcut.TargetPath = "$PSScriptRoot\dist\VirtualSoundboard.exe"
$Shortcut.WorkingDirectory = "$PSScriptRoot\dist"
$Shortcut.Description = "Virtual Soundboard - Standalone Executable with Neon V Icon"
$Shortcut.IconLocation = "$PSScriptRoot\neon_v_soundboard_icon.ico"
$Shortcut.Save()

Write-Host "Desktop shortcut created successfully!" -ForegroundColor Green
Write-Host "You can now double-click 'Virtual Soundboard' on your desktop to run the app." -ForegroundColor Yellow
