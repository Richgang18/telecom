@echo off
REM ============================================================================
REM Smart Outbound Dialer - Client Installation Script
REM Run this ONCE on the client machine to set everything up
REM ============================================================================
title Smart Dialer - Installation
color 0B
cd /d "%~dp0"

echo.
echo  ============================================================
echo   SMART OUTBOUND DIALER - Installation
echo   This will set up everything needed on this machine
echo  ============================================================
echo.

REM ============================================================================
REM Check for admin rights
REM ============================================================================
net session >nul 2>&1
if errorlevel 1 (
    echo  [!] This installer needs Administrator rights.
    echo      Right-click INSTALL_ON_CLIENT.bat and choose "Run as administrator"
    echo.
    pause
    exit /b 1
)
echo  [OK] Running as Administrator
echo.

REM ============================================================================
REM STEP 1: Check Python
REM ============================================================================
echo [1/7] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [!] Python not found. Downloading Python 3.11...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
    echo  Installing Python...
    "%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    echo  [OK] Python installed. Please restart this script.
    pause
    exit /b 0
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  [OK] %%v found
)
echo.

REM ============================================================================
REM STEP 2: Check Node.js
REM ============================================================================
echo [2/7] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo  [!] Node.js not found. Downloading Node.js LTS...
    powershell -Command "Invoke-WebRequest -Uri 'https://nodejs.org/dist/v20.18.0/node-v20.18.0-x64.msi' -OutFile '%TEMP%\node_installer.msi'"
    echo  Installing Node.js...
    msiexec /i "%TEMP%\node_installer.msi" /quiet /norestart
    echo  [OK] Node.js installed. Please restart this script.
    pause
    exit /b 0
) else (
    for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo  [OK] Node.js %%v found
)
echo.

REM ============================================================================
REM STEP 3: Install Python dependencies
REM ============================================================================
echo [3/7] Installing Python dependencies...
python -m pip install --upgrade pip --quiet >nul 2>&1
python -m pip install fastapi uvicorn python-multipart twilio requests --quiet
if errorlevel 1 (
    echo  [!] Failed to install Python packages
    pause
    exit /b 1
)
echo  [OK] Python packages installed
echo.

REM ============================================================================
REM STEP 4: Install Node.js dependencies
REM ============================================================================
echo [4/7] Installing Node.js dependencies...
if not exist "%~dp0ui\node_modules" (
    echo  Installing npm packages (this may take 2-3 minutes)...
    cmd /c "cd /d "%~dp0ui" && npm install --silent 2>&1"
    if errorlevel 1 (
        echo  [!] npm install failed
        pause
        exit /b 1
    )
)
echo  [OK] Node.js packages installed
echo.

REM ============================================================================
REM STEP 5: Enable WSL2
REM ============================================================================
echo [5/7] Checking WSL2...
wsl --list >nul 2>&1
if errorlevel 1 (
    echo  [!] WSL2 not found. Enabling WSL2...
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart >nul 2>&1
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart >nul 2>&1
    echo.
    echo  [!] WSL2 features enabled. A RESTART IS REQUIRED.
    echo      After restart:
    echo        1. Open PowerShell as Admin
    echo        2. Run: wsl --install -d Ubuntu
    echo        3. Set username and password (remember the password!)
    echo        4. Run this installer again
    echo.
    pause
    exit /b 0
) else (
    echo  [OK] WSL2 is available
)
echo.

REM ============================================================================
REM STEP 6: Install Asterisk in WSL2
REM ============================================================================
echo [6/7] Setting up Asterisk in WSL2...

REM Check if Asterisk is already installed
wsl -e bash -c "which asterisk" >nul 2>&1
if errorlevel 1 (
    echo  Installing Asterisk (this takes 3-5 minutes)...
    wsl -e bash -c "sudo apt-get update -qq && sudo apt-get install -y asterisk -qq"
    echo  [OK] Asterisk installed
) else (
    echo  [OK] Asterisk already installed
)

REM Configure passwordless sudo for asterisk service (so launcher works silently)
echo  Configuring sudo for silent startup...
wsl -e bash -c "echo '%sudo ALL=(ALL) NOPASSWD: /bin/systemctl start asterisk, /bin/systemctl stop asterisk, /bin/systemctl restart asterisk, /bin/systemctl status asterisk' | sudo tee /etc/sudoers.d/asterisk-nopasswd > /dev/null"
echo  [OK] Asterisk configured
echo.

REM ============================================================================
REM STEP 7: Configure Asterisk endpoints
REM ============================================================================
echo [7/7] Configuring Asterisk PJSIP...
wsl -e bash -c "sudo bash -s" << 'ASTERISK_SETUP'
cat > /tmp/pjsip_agents.conf << 'EOF'
[transport-tcp]
type=transport
protocol=tcp
bind=0.0.0.0:5060

[transport-udp]
type=transport
protocol=udp
bind=0.0.0.0:5060

[101]
type=endpoint
transport=transport-tcp
context=internal
disallow=all
allow=ulaw,alaw
auth=auth101
aors=aor101
dtmf_mode=rfc4733
direct_media=no

[auth101]
type=auth
auth_type=userpass
username=101
password=ChangeMe101!

[aor101]
type=aor
max_contacts=5
remove_existing=yes

[102]
type=endpoint
transport=transport-tcp
context=internal
disallow=all
allow=ulaw,alaw
auth=auth102
aors=aor102
dtmf_mode=rfc4733
direct_media=no

[auth102]
type=auth
auth_type=userpass
username=102
password=ChangeMe102!

[aor102]
type=aor
max_contacts=5
remove_existing=yes
EOF
cp /tmp/pjsip_agents.conf /etc/asterisk/pjsip.conf
systemctl restart asterisk
ASTERISK_SETUP

echo  [OK] Asterisk configured
echo.

REM ============================================================================
REM Create desktop shortcut
REM ============================================================================
powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0Create_Shortcut.ps1" >nul 2>&1
echo  [OK] Desktop shortcut created
echo.

REM ============================================================================
REM DONE
REM ============================================================================
echo  ============================================================
echo   INSTALLATION COMPLETE!
echo  ============================================================
echo.
echo   What was installed:
echo     - Python packages (FastAPI, Twilio, etc.)
echo     - Node.js packages (Next.js UI)
echo     - Asterisk PBX (in WSL2)
echo     - Desktop shortcut
echo.
echo   Next steps:
echo     1. Double-click "Smart Dialer" on your desktop
echo     2. Go to Settings and enter your Twilio credentials
echo     3. Enter your mobile number for call forwarding
echo     4. Upload your contact list
echo     5. Click Start Campaign!
echo.
echo   IMPORTANT: Update config.ini with your Twilio credentials
echo   before starting the campaign.
echo  ============================================================
echo.
pause
