@echo off
echo ============================================
echo   ACCENT CONVERSION DEMO
echo ============================================
echo.
echo Installing dependencies...
pip install fastapi uvicorn httpx websockets -q

echo.
echo Starting demo server on port 8080...
echo Open http://localhost:8080 in your browser
echo Or share via ngrok: ngrok http 8080
echo.
echo Press Ctrl+C to stop
echo.
python accent_demo.py
pause
