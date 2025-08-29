# PowerShell script to create a desktop shortcut for the soundboard
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$([Environment]::GetFolderPath('Desktop'))\Virtual Soundboard.lnk")
$Shortcut.TargetPath = "C:\Users\sinadvd\Soundboard\soundboard_app\launch-with-browser.bat"
$Shortcut.WorkingDirectory = "C:\Users\sinadvd\Soundboard\soundboard_app"
$Shortcut.Description = "Virtual Soundboard Application - Auto-launches browser"
$Shortcut.IconLocation = "C:\Users\sinadvd\Soundboard\soundboard_app\Virtual Soundboard Icon.ico"
$Shortcut.Save()

Write-Host "Desktop shortcut created successfully!" -ForegroundColor Green
Write-Host "You can now double-click 'Virtual Soundboard' on your desktop to run the app." -ForegroundColor Yellow
