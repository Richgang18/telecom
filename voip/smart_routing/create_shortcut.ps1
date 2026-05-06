# Create Desktop Shortcut for Smart Outbound Dialer
# Run this script once to create a desktop shortcut

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Smart Outbound Dialer.lnk"

# Create WScript Shell object
$WshShell = New-Object -ComObject WScript.Shell

# Create shortcut
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "python.exe"
$Shortcut.Arguments = "`"$ScriptDir\desktop_app.py`""
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.Description = "Smart Outbound Dialer - VoIP Calling System"
$Shortcut.IconLocation = "$ScriptDir\app_icon.ico"
$Shortcut.WindowStyle = 1  # Normal window

# Save shortcut
$Shortcut.Save()

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Desktop Shortcut Created Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Shortcut location: $ShortcutPath" -ForegroundColor Yellow
Write-Host ""
Write-Host "You can now double-click 'Smart Outbound Dialer' on your desktop to launch the app!" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit"
