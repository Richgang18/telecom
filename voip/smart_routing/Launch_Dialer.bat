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
REM STEP 2: Start Webhook Server
REM ============================================================================
echo [2/5] Starting Webhook Server...
echo.

REM Check if webhook_server.py exists
if not exist "webhook_server.py" (
    echo [ERROR] webhook_server.py not found
    pause
    exit /b 1
)

REM Start webhook server in background
start "Webhook Server" /MIN python webhook_server.py

REM Wait for webhook server to start
timeout /t 3 /nobreak >nul

echo [OK] Webhook Server started on port 5000
echo.

REM ============================================================================
REM STEP 3: Start Ngrok Tunnel
REM ============================================================================
echo [3/5] Starting Ngrok Tunnel...
echo.

REM Find ngrok
set NGROK_PATH=
if exist "C:\Users\Admin\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe" (
    set NGROK_PATH=C:\Users\Admin\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe
) else if exist "C:\Users\Admin\Downloads\ngrok.exe" (
    set NGROK_PATH=C:\Users\Admin\Downloads\ngrok.exe
) else if exist "ngrok.exe" (
    set NGROK_PATH=ngrok.exe
)

if "%NGROK_PATH%"=="" (
    echo [WARNING] Ngrok not found - webhook will only work locally
    echo Download ngrok from: https://ngrok.com/download
    echo.
) else (
    echo Starting ngrok tunnel...
    start "Ngrok Tunnel" "%NGROK_PATH%" http 5000
    timeout /t 3 /nobreak >nul
    echo [OK] Ngrok tunnel started
    echo.
)

REM ============================================================================
REM STEP 4: Launch Desktop Application
REM ============================================================================
echo [4/5] Launching Desktop Application...
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
REM STEP 5: System Ready
REM ============================================================================
echo [5/5] System Ready!
echo.
echo ============================================================================
echo                         SYSTEM STATUS
echo ============================================================================
echo.
echo  [OK] WSL2 and Asterisk     : Running
echo  [OK] Webhook Server        : Running on port 5000
if not "%NGROK_PATH%"=="" (
    echo  [OK] Ngrok Tunnel         : Running
) else (
    echo  [--] Ngrok Tunnel         : Not configured
)
echo  [OK] Desktop Application   : Running
echo.
echo ============================================================================
echo.
echo  Your system is ready to make calls!
echo.
echo  Next steps:
echo    1. Configure your Twilio credentials in Settings
echo    2. Upload your contact list
echo    3. Configure your mobile number (for mobile agent mode)
echo    4. Start calling!
echo.
echo  To stop the system:
echo    - Close the Desktop Application
echo    - Close this window
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
