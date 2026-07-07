@echo off
echo ============================================
echo   ACCENT CONVERSION DEMO
echo ============================================
echo.

echo Freeing port 8082...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8082 " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo Installing dependencies...
pip install fastapi uvicorn httpx websockets -q

echo.
echo Starting demo server on port 8082...
echo Open http://localhost:8082 in your browser
echo Or share via ngrok: ngrok http 8082
echo.
echo Press Ctrl+C to stop
echo.
python accent_demo.py
pause
