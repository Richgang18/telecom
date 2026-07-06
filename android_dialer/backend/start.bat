@echo off
echo Starting Agent Dialer Backend...
cd /d "%~dp0"
pip install -r requirements.txt -q
python agent_api.py
pause
