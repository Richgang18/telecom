#!/bin/bash
# Start Asterisk service
# Run this in WSL2 if Asterisk is not running

echo "Starting Asterisk..."
sudo systemctl start asterisk

echo "Checking status..."
sudo systemctl status asterisk --no-pager

echo ""
echo "Verifying..."
asterisk -rx "core show version"

echo ""
echo "Done! Asterisk should now be running."
