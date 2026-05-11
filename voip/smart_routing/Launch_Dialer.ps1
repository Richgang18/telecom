# ============================================================
# Smart Outbound Dialer - PowerShell Launcher
# ONE window controls everything.
# Close this window = all services stop.
# ============================================================

$ErrorActionPreference = "SilentlyContinue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile   = "$env:TEMP\smartdialer_pids.txt"

$script:apiProc = $null
$script:uiProc  = $null

function Log($msg) {
    $t = Get-Date -Format "HH:mm:ss"
    Write-Host "  [$t] $msg" -ForegroundColor Cyan
}

function Port-Listening($port) {
    $result = netstat -ano 2>$null | Select-String ":$port " | Select-String "LISTENING"
    return ($null -ne $result -and $result.Count -gt 0)
}

function Api-Alive {
    try {
        $r = Invoke-WebRequest "http://localhost:5000/api/status" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        return ($r.StatusCode -eq 200)
    } catch {
        return $false
    }
}

function Kill-Port($port) {
    $lines = netstat -ano 2>$null | Select-String ":$port " | Select-String "LISTENING"
    foreach ($l in $lines) {
        if ($l -match '\s+(\d+)$') {
            Stop-Process -Id ([int]$Matches[1]) -Force -ErrorAction SilentlyContinue
        }
    }
}

function Start-Api {
    Kill-Port 5000
    Start-Sleep -Milliseconds 500
    $script:apiProc = Start-Process python `
        -ArgumentList "`"$ScriptDir\api.py`"" `
        -WorkingDirectory $ScriptDir `
        -WindowStyle Hidden `
        -RedirectStandardError "$ScriptDir\api_err.log" `
        -PassThru
    Log "API process started (PID $($script:apiProc.Id))"
}

function Start-UI {
    Kill-Port 3000
    Start-Sleep -Milliseconds 500
    $script:uiProc = Start-Process cmd `
        -ArgumentList "/c", "cd /d `"$ScriptDir\ui`" && npm run dev >> `"$ScriptDir\ui.log`" 2>&1" `
        -WindowStyle Hidden `
        -PassThru
    Log "UI process started (PID $($script:uiProc.Id))"
}

function Stop-All {
    Write-Host ""
    Write-Host "  Stopping all services..." -ForegroundColor Yellow

    foreach ($p in @($script:apiProc, $script:uiProc)) {
        if ($null -ne $p -and -not $p.HasExited) {
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        }
    }

    foreach ($port in @(5000, 3000, 4040)) {
        Kill-Port $port
    }

    Get-Process -Name "node" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

    if (Test-Path $PidFile) {
        Remove-Item $PidFile -Force
    }

    Write-Host "  All services stopped." -ForegroundColor Green
}

Register-EngineEvent PowerShell.Exiting -Action { Stop-All } | Out-Null

# ── Banner ────────────────────────────────────────────────────
Clear-Host
Write-Host ""
Write-Host "  ============================================================" -ForegroundColor DarkCyan
Write-Host "   SMART OUTBOUND DIALER" -ForegroundColor White
Write-Host "   Close this window to stop ALL services" -ForegroundColor Gray
Write-Host "  ============================================================" -ForegroundColor DarkCyan
Write-Host ""

# ── Desktop shortcut ─────────────────────────────────────────
$shortcut = "$env:USERPROFILE\Desktop\Smart Dialer.lnk"
if (-not (Test-Path $shortcut)) {
    & powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "$ScriptDir\Create_Shortcut.ps1" 2>$null
}

# ── Read sudo password from config.ini ───────────────────────
$sudoPass = "8898"
if (Test-Path "$ScriptDir\config.ini") {
    $line = Get-Content "$ScriptDir\config.ini" | Where-Object { $_ -match "wsl_sudo_password\s*=" }
    if ($line) {
        $sudoPass = ($line -split "=", 2)[1].Trim()
    }
}

# ── STEP 1: Start Asterisk silently ──────────────────────────
Log "Starting Asterisk in WSL2..."
Start-Process wsl `
    -ArgumentList "-e", "bash", "-c", "echo $sudoPass | sudo -S systemctl start asterisk > /dev/null 2>&1" `
    -WindowStyle Hidden -Wait
Log "Asterisk started"

# ── STEP 2: Start API backend ─────────────────────────────────
Log "Starting API backend (port 5000)..."
Start-Api

$w = 0
while (-not (Api-Alive) -and $w -lt 20) {
    Start-Sleep 1
    $w++
}
if (Api-Alive) {
    Log "API ready on port 5000"
} else {
    Log "API slow to start - continuing anyway"
}

# ── STEP 3: Start Next.js UI ──────────────────────────────────
Log "Starting UI (port 3000)..."
Start-UI

$w = 0
while (-not (Port-Listening 3000) -and $w -lt 45) {
    Start-Sleep 2
    $w += 2
}
if (Port-Listening 3000) {
    Log "UI ready on port 3000"
} else {
    Log "UI slow to start - opening browser anyway"
}

# ── STEP 4: Open browser ──────────────────────────────────────
Log "Opening browser in 5 seconds..."
Start-Sleep 5
Start-Process "http://localhost:3000"

# ── Ready ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ============================================================" -ForegroundColor Green
Write-Host "   SYSTEM RUNNING" -ForegroundColor White
Write-Host "   Dashboard : http://localhost:3000" -ForegroundColor Cyan
Write-Host "   API       : http://localhost:5000" -ForegroundColor Cyan
Write-Host ""
Write-Host "   CLOSE THIS WINDOW TO STOP EVERYTHING" -ForegroundColor Yellow
Write-Host "  ============================================================" -ForegroundColor Green
Write-Host ""

@($script:apiProc.Id, $script:uiProc.Id) | Out-File $PidFile

# ── Watchdog loop ─────────────────────────────────────────────
while ($true) {
    Start-Sleep 15

    if ($null -ne $script:apiProc -and $script:apiProc.HasExited) {
        Log "API stopped - restarting..."
        Start-Api
        Start-Sleep 3
    }

    if ($null -ne $script:uiProc -and $script:uiProc.HasExited) {
        Log "UI stopped - restarting..."
        Start-UI
        Start-Sleep 3
    }
}
