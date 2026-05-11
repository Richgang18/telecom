@echo off
REM ============================================================================
REM Smart Outbound Dialer - Launcher v2.1
REM Works on any Windows machine with WSL2 installed
REM ============================================================================
title Smart Dialer - Starting...
color 0A
cd /d "%~dp0"

REM Store PIDs for cleanup
set "PID_FILE=%TEMP%\smartdialer_pids.txt"
if exist "%PID_FILE%" del "%PID_FILE%"

echo.
echo  ============================================================
echo   SMART OUTBOUND DIALER
echo  ============================================================
echo.

REM ============================================================================
REM Create desktop shortcut silently (first run only)
REM ============================================================================
set "SHORTCUT=%USERPROFILE%\Desktop\Smart Dialer.lnk"
if not exist "%SHORTCUT%" (
    powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0Create_Shortcut.ps1" >nul 2>&1
)

REM ============================================================================
REM STEP 1: Start Asterisk silently in WSL2
REM Uses the WSL sudo password from config, no popup window
REM ============================================================================
echo  [1/4] Starting Asterisk...

REM Read sudo password from config (default: 8898)
set "SUDO_PASS=8898"
for /f "tokens=2 delims==" %%a in ('findstr /i "wsl_sudo_password" "%~dp0config.ini" 2^>nul') do (
    set "SUDO_PASS=%%a"
    set "SUDO_PASS=!SUDO_PASS: =!"
)

REM Start Asterisk silently - no window, no password prompt
powershell -ExecutionPolicy Bypass -WindowStyle Hidden -Command ^
  "& { $p = Start-Process -FilePath 'wsl' -ArgumentList '-e','bash','-c','echo %SUDO_PASS% | sudo -S systemctl start asterisk 2>/dev/null' -WindowStyle Hidden -PassThru -Wait; }" >nul 2>&1

timeout /t 2 /nobreak >nul
echo  [OK] Asterisk started
echo.

REM ============================================================================
REM STEP 2: Start FastAPI backend (port 5000)
REM ============================================================================
echo  [2/4] Starting API backend...

REM Kill any existing process on port 5000
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5000 " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

REM Start API
start "SmartDialer-API" /MIN cmd /c "python "%~dp0api.py" 2>&1 >> "%~dp0api.log""

REM Wait for API to be ready (poll up to 15s)
set /a API_WAIT=0
:wait_api
timeout /t 1 /nobreak >nul
set /a API_WAIT+=1
curl -s http://localhost:5000/api/status >nul 2>&1
if not errorlevel 1 goto api_ready
if %API_WAIT% GEQ 15 (
    echo  [!] API failed to start. Check api.log for errors.
    goto api_ready
)
goto wait_api
:api_ready

REM Save API PID
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5000 " ^| findstr "LISTENING"') do (
    echo API=%%a >> "%PID_FILE%"
)
echo  [OK] API backend ready on port 5000
echo.

REM ============================================================================
REM STEP 3: Start Next.js UI (port 3000)
REM ============================================================================
echo  [3/4] Starting UI...

REM Kill any existing process on port 3000
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":3000 " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

REM Start Next.js
start "SmartDialer-UI" /MIN cmd /c "cd /d "%~dp0ui" && npm run dev 2>&1 >> "%~dp0ui.log""

REM Wait for Next.js to be ready (poll up to 30s)
set /a UI_WAIT=0
:wait_ui
timeout /t 2 /nobreak >nul
set /a UI_WAIT+=2
curl -s http://localhost:3000 >nul 2>&1
if not errorlevel 1 goto ui_ready
if %UI_WAIT% GEQ 30 (
    echo  [!] UI taking longer than expected. Opening browser anyway...
    goto ui_ready
)
goto wait_ui
:ui_ready

REM Save UI PID
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":3000 " ^| findstr "LISTENING"') do (
    echo UI=%%a >> "%PID_FILE%"
)
echo  [OK] UI ready on port 3000
echo.

REM ============================================================================
REM STEP 4: Open browser
REM ============================================================================
echo  [4/4] Opening browser...
start "" "http://localhost:3000"
echo  [OK] Browser opened
echo.

REM ============================================================================
REM READY
REM ============================================================================
echo  ============================================================
echo   SYSTEM IS RUNNING
echo  ============================================================
echo.
echo   Dashboard  :  http://localhost:3000
echo   API        :  http://localhost:5000
echo.
echo   Quick steps:
echo     1. Go to Settings - enter Twilio credentials + mobile number
echo     2. Go to Contacts  - upload your CSV file
echo     3. Click Start Services (for Ngrok)
echo     4. Click Start Campaign
echo.
echo   Close this window to STOP all services.
echo  ============================================================
echo.

REM ============================================================================
REM Keep running - cleanup on exit
REM ============================================================================
:main_loop
timeout /t 5 /nobreak >nul

REM Check if UI is still running, restart if crashed
curl -s http://localhost:3000 >nul 2>&1
if errorlevel 1 (
    echo  [!] UI crashed - restarting...
    start "SmartDialer-UI" /MIN cmd /c "cd /d "%~dp0ui" && npm run dev 2>&1 >> "%~dp0ui.log""
)

goto main_loop
