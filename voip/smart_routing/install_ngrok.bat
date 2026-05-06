@echo off
REM Install ngrok to system PATH

echo ========================================
echo Ngrok Installation Helper
echo ========================================
echo.

REM Check if ngrok.exe exists in Downloads
set "DOWNLOADS=%USERPROFILE%\Downloads"
set "NGROK_SOURCE=%DOWNLOADS%\ngrok.exe"
set "NGROK_DEST=C:\ngrok"

if not exist "%NGROK_SOURCE%" (
    echo ERROR: ngrok.exe not found in Downloads folder
    echo.
    echo Please download ngrok from: https://ngrok.com/download
    echo Save it to your Downloads folder, then run this script again.
    echo.
    pause
    exit /b 1
)

echo Found ngrok.exe in Downloads folder
echo.

REM Create ngrok directory
echo Creating C:\ngrok directory...
if not exist "%NGROK_DEST%" (
    mkdir "%NGROK_DEST%"
)

REM Copy ngrok.exe
echo Copying ngrok.exe to C:\ngrok...
copy "%NGROK_SOURCE%" "%NGROK_DEST%\ngrok.exe" /Y

REM Add to PATH
echo Adding C:\ngrok to system PATH...
setx PATH "%PATH%;C:\ngrok" /M >nul 2>&1

if errorlevel 1 (
    echo.
    echo WARNING: Could not add to system PATH automatically.
    echo You may need administrator privileges.
    echo.
    echo Manual steps:
    echo 1. Right-click "This PC" ^> Properties
    echo 2. Click "Advanced system settings"
    echo 3. Click "Environment Variables"
    echo 4. Under "System variables", find "Path"
    echo 5. Click "Edit" and add: C:\ngrok
    echo.
) else (
    echo.
    echo ========================================
    echo SUCCESS!
    echo ========================================
    echo.
    echo Ngrok installed to: C:\ngrok\ngrok.exe
    echo Added to system PATH
    echo.
    echo IMPORTANT: Close and reopen the desktop app
    echo for the changes to take effect.
    echo.
)

pause
