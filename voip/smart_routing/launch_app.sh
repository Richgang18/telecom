#!/bin/bash
# Smart Outbound Dialer - Desktop Application Launcher
# This script launches the desktop app from WSL2/Linux

echo "========================================"
echo "Smart Outbound Dialer"
echo "========================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Navigate to script directory
cd "$(dirname "$0")"

# Launch the desktop app
echo "Starting application..."
python3 desktop_app.py

if [ $? -ne 0 ]; then
    echo
    echo "ERROR: Application failed to start"
    read -p "Press Enter to continue..."
fi
