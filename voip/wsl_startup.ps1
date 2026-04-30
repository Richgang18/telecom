# wsl_startup.ps1 — WSL2 startup script
#
# Runs on every Windows boot/login via the "WSL2 VoIP Startup" Task Scheduler
# task created by setup_windows_host.ps1.
#
# Responsibilities:
#   1. Ensure WSL2 is running
#   2. Resolve the current (dynamic) WSL2 IP
#   3. Update the netsh portproxy rule with the new IP
#   4. Start the Asterisk service inside WSL2
#
# Requirements: 1a.4, 1a.5, 1a.6

# ---------------------------------------------------------------------------
# 1. Start WSL2 if not already running
# ---------------------------------------------------------------------------
wsl -e echo "WSL2 started"

# Wait for WSL2 to be fully ready before resolving the IP
Start-Sleep -Seconds 10

# ---------------------------------------------------------------------------
# 2. Resolve the current WSL2 IP dynamically
#    (WSL2 IP changes on every Windows reboot)
# ---------------------------------------------------------------------------
$wslIP = (wsl hostname -I).Trim().Split(" ")[0]
Write-Host "WSL2 IP resolved: $wslIP"

# ---------------------------------------------------------------------------
# 3. Update netsh portproxy rule with the current WSL2 IP
# ---------------------------------------------------------------------------
# Remove the old rule (ignore errors if it doesn't exist yet)
netsh interface portproxy delete v4tov4 listenport=5061 listenaddress=0.0.0.0 2>$null

# Add the updated rule pointing to the current WSL2 IP
netsh interface portproxy add v4tov4 `
    listenport=5061 `
    listenaddress=0.0.0.0 `
    connectport=5061 `
    connectaddress=$wslIP

Write-Host "Portproxy rule updated: 0.0.0.0:5061 -> ${wslIP}:5061"

# ---------------------------------------------------------------------------
# 4. Start the Asterisk service inside WSL2
# ---------------------------------------------------------------------------
wsl -e sudo systemctl start asterisk
Write-Host "Asterisk service start command sent."
