@echo off
REM ============================================
REM Smart Outbound Dialer - Shortcut Creator
REM Double-click this file to create a desktop shortcut
REM ============================================

echo.
echo ========================================
echo  Smart Outbound Dialer
echo  Desktop Shortcut Setup
echo ========================================
echo.

cd /d "%~dp0"

REM Create icon first
echo [Step 1/2] Creating application icon...
python create_icon.py >nul 2>&1
if exist "app_icon.ico" (
    echo   ^> Icon created successfully!
) else (
    echo   ^> Using default icon
)
echo.

REM Create shortcut using VBScript (most compatible)
echo [Step 2/2] Creating desktop shortcut...
cscript //nologo create_shortcut.vbs

echo.
echo ========================================
echo  Setup Complete!
echo ========================================
echo.
echo Check your desktop for:
echo   "Smart Outbound Dialer" shortcut
echo.
echo Double-click it to launch the app!
echo.
pause
