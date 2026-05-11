# Create Desktop Shortcut for Smart Outbound Dialer
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$LaunchFile = Join-Path $ScriptDir "Launch_Dialer.bat"
$Desktop    = [Environment]::GetFolderPath("Desktop")
$Shortcut   = Join-Path $Desktop "Smart Dialer.lnk"

$WS = New-Object -ComObject WScript.Shell
$SC = $WS.CreateShortcut($Shortcut)
$SC.TargetPath       = $LaunchFile
$SC.WorkingDirectory = $ScriptDir
$SC.Description      = "Smart Outbound Dialer - Call Center"
$SC.IconLocation     = "shell32.dll,13"
$SC.Save()

Write-Host "Desktop shortcut created: $Shortcut" -ForegroundColor Green
