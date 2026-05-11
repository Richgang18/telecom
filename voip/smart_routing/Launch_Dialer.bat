@echo off
REM ============================================================================
REM Smart Outbound Dialer - Unified Launcher
REM ============================================================================
REM This script starts everything you need in the correct order
REM ============================================================================

title Smart Outbound Dialer - Starting...
color 0A

echo.
echo ============================================================================
echo                    SMART OUTBOUND DIALER
echo                         Starting System...
echo ============================================================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM ============================================================================
REM STEP 0: Create Desktop Shortcut (if not exists)
REM ============================================================================
set SHORTCUT_PATH=%USERPROFILE%\Desktop\Smart Dialer.lnk

if not exist "%SHORTCUT_PATH%" (
    echo [0/5] Creating desktop shortcut...
    powershell -ExecutionPolicy Bypass -File "Create_Shortcut.ps1" >nul 2>&1
    if exist "%SHORTCUT_PATH%" (
        echo [OK] Desktop shortcut created
    )
    echo.
)

REM ============================================================================
REM STEP 1: Start WSL2 and Asterisk
REM ============================================================================
echo [1/5] Starting WSL2 and Asterisk...
echo.

REM Check if WSL2 is available
wsl --list >nul 2>&1
if errorlevel 1 (
    echo [ERROR] WSL2 is not installed or not available
    echo Please install WSL2 first: https://aka.ms/wsl2
    pause
    exit /b 1
)

REM Start Asterisk in WSL2
echo Starting Asterisk PBX...
start "Asterisk" wsl -e bash -c "sudo systemctl start asterisk && echo 'Asterisk started successfully' && sudo asterisk -rvvvvv"

REM Wait for Asterisk to start
timeout /t 3 /nobreak >nul

echo [OK] Asterisk started
echo.

REM ============================================================================
REM STEP 2: Launch Desktop Application
REM ============================================================================
echo [2/3] Launching Desktop Application...
echo.

REM Check if desktop_app.py exists
if not exist "desktop_app.py" (
    echo [ERROR] desktop_app.py not found
    pause
    exit /b 1
)

REM Launch desktop app
start "Smart Dialer" python desktop_app.py

timeout /t 2 /nobreak >nul

echo [OK] Desktop Application launched
echo.

REM ============================================================================
REM STEP 3: System Ready
REM ============================================================================
echo [3/3] System Ready!
echo.
echo ============================================================================
echo                         SYSTEM STATUS
echo ============================================================================
echo.
echo  [OK] WSL2 and Asterisk     : Running
echo  [OK] Desktop Application   : Running
echo.
echo  [--] Webhook Server        : Use "Start Services" button in app
echo  [--] Ngrok Tunnel          : Use "Start Services" button in app
echo.
echo ============================================================================
echo.
echo  Your system is ready!
echo.
echo  Next steps:
echo    1. In the Desktop App, click "Start Services" button
echo    2. Configure your Twilio credentials in Settings
echo    3. Configure your mobile number in Settings
echo    4. Upload your contact list
echo    5. Start calling!
echo.
echo  Note: With mobile agent mode, calls will ring on your mobile phone,
echo        not on this computer.
echo.
echo ============================================================================
echo.
echo Press any key to minimize this window...
pause >nul

REM Minimize this window
powershell -window minimized -command ""

REM Keep window open but minimized
:loop
timeout /t 60 /nobreak >nul
goto loop
