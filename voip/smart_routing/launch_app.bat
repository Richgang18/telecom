@echo off
REM Smart Outbound Dialer - Desktop Application Launcher
REM This script launches the desktop app from Windows

echo ========================================
echo Smart Outbound Dialer
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

REM Navigate to script directory
cd /d "%~dp0"

REM Launch the desktop app
echo Starting application...
python desktop_app.py

if errorlevel 1 (
    echo.
    echo ERROR: Application failed to start
    pause
)
