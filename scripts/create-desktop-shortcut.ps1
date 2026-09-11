# PowerShell script to create a desktop shortcut for Virtual Soundboard 2
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$ExePath = Join-Path $ProjectRoot "dist\VirtualSoundboard2.exe"
$IcoPath = Join-Path $ProjectRoot "assets\app_icon.ico"
$WorkingDir = Join-Path $ProjectRoot "dist"

$DesktopPath = [Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $DesktopPath "Virtual Soundboard 2.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = $WorkingDir
$Shortcut.Description = "Virtual Soundboard 2 - Standalone Executable with DSP Audio Engine"

if (Test-Path $IcoPath) {
    $Shortcut.IconLocation = "$IcoPath,0"
} else {
    $Shortcut.IconLocation = "$ExePath,0"
}

$Shortcut.Save()

# Notify Windows Explorer of association/icon changes
try {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class ShellNotifier {
    [DllImport("shell32.dll")]
    public static extern void SHChangeNotify(int wEventId, int uFlags, IntPtr dwItem1, IntPtr dwItem2);
}
'@ -ErrorAction SilentlyContinue
    [ShellNotifier]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
} catch {
    # Fallback to ie4uinit if available
    Start-Process -FilePath "ie4uinit.exe" -ArgumentList "-show" -NoNewWindow -ErrorAction SilentlyContinue
}

Write-Host "Desktop shortcut for Virtual Soundboard 2 created successfully at:" -ForegroundColor Green
Write-Host "  $ShortcutPath" -ForegroundColor Cyan
Write-Host "Target:       $ExePath" -ForegroundColor Gray
Write-Host "IconLocation: $($Shortcut.IconLocation)" -ForegroundColor Gray
