@echo off
REM Create Desktop Shortcut for Smart Outbound Dialer
REM Run this once to create a desktop shortcut with icon

echo ========================================
echo Smart Outbound Dialer
echo Creating Desktop Shortcut...
echo ========================================
echo.

REM Navigate to script directory
cd /d "%~dp0"

REM Step 1: Create icon
echo [1/2] Creating application icon...
python create_icon.py
if errorlevel 1 (
    echo Warning: Could not create icon, using default
)
echo.

REM Step 2: Create shortcut
echo [2/2] Creating desktop shortcut...
powershell -ExecutionPolicy Bypass -File "%~dp0create_shortcut.ps1"

echo.
echo ========================================
echo Done!
echo ========================================
echo.
echo Look for "Smart Outbound Dialer" on your desktop!
echo.
pause
