# Create Desktop Shortcut
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LauncherPath = Join-Path $ScriptDir "Launch_Dialer.bat"
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Smart Dialer.lnk"

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $LauncherPath
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.Description = "Smart Outbound Dialer"
$Shortcut.IconLocation = "shell32.dll,13"
$Shortcut.Save()

Write-Host "Desktop shortcut created!" -ForegroundColor Green
