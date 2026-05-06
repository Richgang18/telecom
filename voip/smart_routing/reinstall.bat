@echo off
REM ============================================================================
REM Smart Outbound Dialer - Quick Reinstall Script
REM ============================================================================
REM This script reinstalls Python dependencies and verifies the installation
REM ============================================================================

echo.
echo ============================================================================
echo Smart Outbound Dialer - Quick Reinstall
echo ============================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/5] Python version:
python --version
echo.

REM Check if we're in the right directory
if not exist "desktop_app.py" (
    echo [ERROR] desktop_app.py not found
    echo Please run this script from the smart_routing directory
    pause
    exit /b 1
)

echo [2/5] Installing Python dependencies...
pip install flask twilio requests configparser
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

echo [3/5] Checking required files...
set MISSING=0

if not exist "dialer.py" (
    echo [MISSING] dialer.py
    set MISSING=1
)
if not exist "webhook_server.py" (
    echo [MISSING] webhook_server.py
    set MISSING=1
)
if not exist "agent_router.py" (
    echo [MISSING] agent_router.py
    set MISSING=1
)
if not exist "voicemail_drop.py" (
    echo [MISSING] voicemail_drop.py
    set MISSING=1
)
if not exist "voicemail.mp3" (
    echo [WARNING] voicemail.mp3 not found - you'll need to add this
)

if %MISSING%==1 (
    echo [ERROR] Some required files are missing
    echo Please ensure all files are present in this directory
    pause
    exit /b 1
)
echo [OK] All required files present
echo.

echo [4/5] Checking ngrok installation...
set NGROK_FOUND=0

if exist "C:\Users\Admin\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe" (
    echo [OK] Ngrok found at: C:\Users\Admin\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe
    set NGROK_FOUND=1
) else if exist "C:\Users\Admin\Downloads\ngrok.exe" (
    echo [OK] Ngrok found at: C:\Users\Admin\Downloads\ngrok.exe
    set NGROK_FOUND=1
) else if exist "ngrok.exe" (
    echo [OK] Ngrok found in current directory
    set NGROK_FOUND=1
) else (
    echo [WARNING] Ngrok not found in common locations
    echo Download from: https://ngrok.com/download
    echo Extract to: C:\Users\Admin\Downloads\ngrok-v3-stable-windows-amd64\
)
echo.

echo [5/5] Checking WSL2 and Asterisk...
wsl --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] WSL2 not detected or not running
    echo Asterisk requires WSL2 Ubuntu 24.04
) else (
    echo [OK] WSL2 is installed
    wsl systemctl is-active asterisk >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] Asterisk is not running in WSL2
        echo Start with: wsl sudo systemctl start asterisk
    ) else (
        echo [OK] Asterisk is running
    )
)
echo.

echo ============================================================================
echo Installation Summary
echo ============================================================================
echo.
echo [OK] Python dependencies installed
echo [OK] Required files verified
if %NGROK_FOUND%==1 (
    echo [OK] Ngrok found
) else (
    echo [!] Ngrok needs to be installed
)
echo.
echo Next Steps:
echo 1. Launch the desktop app: launch_app.bat
echo 2. Configure Twilio credentials in Settings tab
echo 3. Start services from Dashboard tab
echo 4. Upload contacts and start calling
echo.
echo For detailed instructions, see: REINSTALL_GUIDE.md
echo.
echo ============================================================================
echo.

pause
