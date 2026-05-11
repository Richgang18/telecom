@echo off
REM ============================================================================
REM Smart Outbound Dialer - Unified Launcher v2.0
REM ============================================================================
title Smart Dialer - Starting...
color 0A
cd /d "%~dp0"

echo.
echo  ============================================================
echo   SMART OUTBOUND DIALER - Starting System
echo  ============================================================
echo.

REM ============================================================================
REM STEP 0: Create desktop shortcut silently
REM ============================================================================
set SHORTCUT=%USERPROFILE%\Desktop\Smart Dialer.lnk
if not exist "%SHORTCUT%" (
    powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0Create_Shortcut.ps1" >nul 2>&1
)

REM ============================================================================
REM STEP 1: Start Asterisk in WSL2 silently (auto-enter password 8898)
REM ============================================================================
echo [1/4] Starting Asterisk in WSL2...

REM Write a helper script that feeds the sudo password
powershell -ExecutionPolicy Bypass -WindowStyle Hidden -Command ^
  "Start-Process wsl -ArgumentList '-e','bash','-c','echo 8898 | sudo -S systemctl start asterisk 2>/dev/null; echo DONE' -WindowStyle Hidden -Wait" >nul 2>&1

timeout /t 2 /nobreak >nul
echo  [OK] Asterisk started silently
echo.

REM ============================================================================
REM STEP 2: Start FastAPI backend
REM ============================================================================
echo [2/4] Starting API backend (port 5000)...

REM Check if port 5000 is already in use
netstat -ano | findstr ":5000 " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo  [OK] API already running on port 5000
) else (
    REM Install uvicorn + fastapi if needed
    python -c "import uvicorn" >nul 2>&1
    if errorlevel 1 (
        echo  Installing API dependencies...
        pip install fastapi uvicorn python-multipart --quiet >nul 2>&1
    )
    start "SmartDialer-API" /MIN python "%~dp0api.py"
    timeout /t 3 /nobreak >nul
    echo  [OK] API backend started
)
echo.

REM ============================================================================
REM STEP 3: Start Next.js UI
REM ============================================================================
echo [3/4] Starting Next.js UI (port 3000)...

REM Check if port 3000 is already in use
netstat -ano | findstr ":3000 " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo  [OK] UI already running on port 3000
) else (
    start "SmartDialer-UI" /MIN cmd /c "cd /d "%~dp0ui" && npm run dev 2>&1"
    timeout /t 5 /nobreak >nul
    echo  [OK] Next.js UI started
)
echo.

REM ============================================================================
REM STEP 4: Open browser
REM ============================================================================
echo [4/4] Opening browser...
timeout /t 4 /nobreak >nul
start "" "http://localhost:3000"
echo  [OK] Browser opened
echo.

REM ============================================================================
REM READY
REM ============================================================================
echo  ============================================================
echo   SYSTEM READY
echo  ============================================================
echo.
echo   Dashboard : http://localhost:3000
echo   API       : http://localhost:5000
echo.
echo   Next steps:
echo     1. Click "Start Services" in the UI to start Ngrok
echo     2. Upload your contact list
echo     3. Configure your mobile number in Settings
echo     4. Click "Start Campaign"
echo.
echo   To stop: close this window (all processes will be tracked)
echo  ============================================================
echo.

REM Track PIDs for cleanup on exit
set API_PID=
set UI_PID=

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000 " ^| findstr "LISTENING"') do set API_PID=%%a
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000 " ^| findstr "LISTENING"') do set UI_PID=%%a

echo   API PID : %API_PID%
echo   UI PID  : %UI_PID%
echo.
echo  Press Ctrl+C or close this window to stop all services.
echo.

REM Keep window open and wait for exit signal
:wait_loop
timeout /t 5 /nobreak >nul
goto wait_loop
