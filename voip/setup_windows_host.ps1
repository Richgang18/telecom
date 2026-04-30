# setup_windows_host.ps1 — Windows host configuration script
#
# Run as Administrator on the Windows 11 host.
# Configures netsh portproxy, Windows Firewall rules, and a Task Scheduler
# task so that WSL2 starts automatically and VoIP ports are forwarded.
#
# Requirements: 1a.1, 1a.2, 1a.3, 1a.4, 1a.7

#Requires -RunAsAdministrator

# ---------------------------------------------------------------------------
# 1. Resolve the current WSL2 IP dynamically
# ---------------------------------------------------------------------------
$wslIP = (wsl hostname -I).Trim().Split(" ")[0]
Write-Host "WSL2 IP resolved: $wslIP"

# ---------------------------------------------------------------------------
# 2. Configure netsh portproxy — forward TCP 5061 from Windows host to WSL2
# ---------------------------------------------------------------------------
# Remove any existing rule first to avoid duplicates
netsh interface portproxy delete v4tov4 listenport=5061 listenaddress=0.0.0.0 2>$null

netsh interface portproxy add v4tov4 `
    listenport=5061 `
    listenaddress=0.0.0.0 `
    connectport=5061 `
    connectaddress=$wslIP

Write-Host "Portproxy rule added: 0.0.0.0:5061 -> ${wslIP}:5061"

# ---------------------------------------------------------------------------
# 3. Windows Firewall inbound rules
# ---------------------------------------------------------------------------

# Allow TCP 5061 inbound (SIP/TLS)
New-NetFirewallRule `
    -DisplayName "VoIP SIP TLS" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 5061 `
    -Action Allow `
    -ErrorAction SilentlyContinue

# Allow UDP 10000-20000 inbound (RTP media)
New-NetFirewallRule `
    -DisplayName "VoIP RTP" `
    -Direction Inbound `
    -Protocol UDP `
    -LocalPort 10000-20000 `
    -Action Allow `
    -ErrorAction SilentlyContinue

# Allow TCP 443 inbound (HTTPS/AMI)
New-NetFirewallRule `
    -DisplayName "VoIP HTTPS" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 443 `
    -Action Allow `
    -ErrorAction SilentlyContinue

# Block TCP 5060 inbound (plain SIP — must be blocked per security policy)
New-NetFirewallRule `
    -DisplayName "Block SIP TCP" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 5060 `
    -Action Block `
    -ErrorAction SilentlyContinue

# Block UDP 5060 inbound (plain SIP — must be blocked per security policy)
New-NetFirewallRule `
    -DisplayName "Block SIP UDP" `
    -Direction Inbound `
    -Protocol UDP `
    -LocalPort 5060 `
    -Action Block `
    -ErrorAction SilentlyContinue

Write-Host "Windows Firewall rules configured."

# ---------------------------------------------------------------------------
# 4. Task Scheduler — run wsl_startup.ps1 on user login
# ---------------------------------------------------------------------------
$scriptPath = "C:\VoIP\wsl_startup.ps1"

$action = New-ScheduledTaskAction `
    -Execute "PowerShell.exe" `
    -Argument "-NonInteractive -File $scriptPath"

$trigger = New-ScheduledTaskTrigger -AtLogOn

Register-ScheduledTask `
    -TaskName "WSL2 VoIP Startup" `
    -Action $action `
    -Trigger $trigger `
    -RunLevel Highest `
    -Force

Write-Host "Task Scheduler task 'WSL2 VoIP Startup' registered."
Write-Host "Windows host configuration complete."
