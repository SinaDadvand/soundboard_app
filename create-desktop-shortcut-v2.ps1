# PowerShell script to create a desktop shortcut for Virtual Soundboard 2
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$([Environment]::GetFolderPath('Desktop'))\Virtual Soundboard 2.lnk")
$Shortcut.TargetPath = "$PSScriptRoot\dist\VirtualSoundboard2.exe"
$Shortcut.WorkingDirectory = "$PSScriptRoot\dist"
$Shortcut.Description = "Virtual Soundboard 2 - Standalone Executable with DSP Audio Engine & Neon Icon"
$Shortcut.IconLocation = "$PSScriptRoot\app_icon.ico"
$Shortcut.Save()

Write-Host "Desktop shortcut for Virtual Soundboard 2 created successfully with new icon!" -ForegroundColor Green
Write-Host "You can now double-click 'Virtual Soundboard 2' on your desktop to run the app." -ForegroundColor Yellow
