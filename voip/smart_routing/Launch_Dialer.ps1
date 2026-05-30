# ============================================================
# Smart Outbound Dialer - PowerShell Launcher
# ONE window controls everything.
# Close this window = all services stop.
# ============================================================

$ErrorActionPreference = "SilentlyContinue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile   = "$env:TEMP\smartdialer_pids.txt"

$script:apiProc  = $null
$script:uiProc   = $null
$script:ngrokProc = $null

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
    # Wait until port is actually free (up to 5s)
    $waited = 0
    while ((Port-Listening 5000) -and $waited -lt 10) {
        Start-Sleep -Milliseconds 500
        $waited++
    }
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

    foreach ($p in @($script:apiProc, $script:uiProc, $script:ngrokProc)) {
        if ($null -ne $p -and -not $p.HasExited) {
            taskkill /PID $p.Id /F /T 2>$null | Out-Null
        }
    }

    foreach ($port in @(5000, 3000, 4040)) {
        Kill-Port $port
    }

    taskkill /IM node.exe /F 2>$null | Out-Null
    taskkill /IM ngrok.exe /F 2>$null | Out-Null

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

# ── STEP 2b: Start Ngrok from launcher ───────────────────────
Log "Starting Ngrok tunnel..."

# Find ngrok
$ngrokExe = $null
$ngrokPaths = @(
    "$ScriptDir\ngrok.exe",
    "$ScriptDir\ngrok",
    "C:\Users\Admin\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe",
    "C:\Users\Admin\Downloads\ngrok.exe",
    "ngrok"
)
foreach ($p in $ngrokPaths) {
    try {
        $test = & $p version 2>$null
        if ($LASTEXITCODE -eq 0) { $ngrokExe = $p; break }
    } catch {}
}

if ($ngrokExe) {
    # Configure authtoken if set in config
    $ngrokToken = ""
    if (Test-Path "$ScriptDir\config.ini") {
        $tline = Get-Content "$ScriptDir\config.ini" | Where-Object { $_ -match "ngrok_authtoken\s*=" }
        if ($tline) {
            $ngrokToken = ($tline -split "=", 2)[1].Trim()
        }
    }
    if ($ngrokToken -and $ngrokToken.Length -gt 10) {
        & $ngrokExe config add-authtoken $ngrokToken 2>$null | Out-Null
        Log "Ngrok authtoken configured"
    }

    # Kill any existing ngrok
    Kill-Port 4040
    taskkill /IM ngrok.exe /F 2>$null | Out-Null
    Start-Sleep -Milliseconds 500

    # Always use ngrok.yml config file — it sets ngrok-skip-browser-warning header
    # Without this header, SignalWire gets an HTML interstitial instead of TwiML
    $ngrokConfigFile = "$ScriptDir\ngrok.yml"
    if (Test-Path $ngrokConfigFile) {
        $script:ngrokProc = Start-Process $ngrokExe `
            -ArgumentList "start", "smart-dialer", "--config", $ngrokConfigFile `
            -WindowStyle Hidden `
            -PassThru
    } else {
        # Fallback if config file missing
        $script:ngrokProc = Start-Process $ngrokExe `
            -ArgumentList "http", "5000", "--request-header-add", "ngrok-skip-browser-warning:true" `
            -WindowStyle Hidden `
            -PassThru
    }

    # Wait up to 10s for tunnel
    $nw = 0
    $ngrokReady = $false
    while ($nw -lt 10 -and -not $ngrokReady) {
        Start-Sleep 1
        $nw++
        try {
            $resp = Invoke-WebRequest "http://localhost:4040/api/tunnels" -TimeoutSec 1 -UseBasicParsing -EA Stop
            $data = $resp.Content | ConvertFrom-Json
            if ($data.tunnels.Count -gt 0) {
                $ngrokUrl = $data.tunnels[0].public_url
                Log "Ngrok tunnel ready: $ngrokUrl"
                # Save to config.ini
                $configContent = Get-Content "$ScriptDir\config.ini" -Raw
                $configContent = $configContent -replace "webhook_base_url\s*=.*", "webhook_base_url = $ngrokUrl"
                # Write WITHOUT BOM — Python configparser breaks with UTF-8 BOM
                $utf8NoBom = New-Object System.Text.UTF8Encoding $false
                [System.IO.File]::WriteAllText("$ScriptDir\config.ini", $configContent, $utf8NoBom)
                $ngrokReady = $true
            }
        } catch {}
    }
    if (-not $ngrokReady) { Log "Ngrok starting slowly - UI will detect it" }
} else {
    Log "Ngrok not found - skipping (place ngrok.exe in Smart Dialer folder)"
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
