@echo off
REM Setup ngrok for Smart Outbound Dialer
REM This copies ngrok.exe from Downloads to the app folder

echo ========================================
echo Ngrok Setup for Smart Outbound Dialer
echo ========================================
echo.

cd /d "%~dp0"

REM Check if ngrok.exe already exists here
if exist "ngrok.exe" (
    echo Ngrok is already set up in this folder!
    echo Location: %~dp0ngrok.exe
    echo.
    echo You can now use "Start Services" in the app.
    echo.
    pause
    exit /b 0
)

REM Check Downloads folder
set "DOWNLOADS=%USERPROFILE%\Downloads"
set "NGROK_SOURCE=%DOWNLOADS%\ngrok.exe"

if exist "%NGROK_SOURCE%" (
    echo Found ngrok.exe in Downloads folder
    echo Copying to app folder...
    copy "%NGROK_SOURCE%" "ngrok.exe" /Y
    echo.
    echo ========================================
    echo SUCCESS!
    echo ========================================
    echo.
    echo Ngrok is now set up!
    echo Location: %~dp0ngrok.exe
    echo.
    echo You can now use "Start Services" in the app.
    echo.
) else (
    echo ERROR: ngrok.exe not found in Downloads folder
    echo.
    echo Please:
    echo 1. Download ngrok from: https://ngrok.com/download
    echo 2. Extract ngrok.exe to your Downloads folder
    echo 3. Run this script again
    echo.
    echo OR manually copy ngrok.exe to:
    echo %~dp0
    echo.
)

pause
