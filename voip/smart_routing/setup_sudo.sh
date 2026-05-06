#!/bin/bash
# Setup passwordless sudo for Asterisk service
# Run this ONCE to allow the app to start Asterisk automatically

echo "=========================================="
echo "Asterisk Passwordless Sudo Setup"
echo "=========================================="
echo ""
echo "This will allow the desktop app to start/stop Asterisk"
echo "without requiring a password."
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

# Get current user
CURRENT_USER=$(whoami)

echo ""
echo "Creating sudoers rule for $CURRENT_USER..."

# Create sudoers file
SUDOERS_FILE="/etc/sudoers.d/asterisk-$CURRENT_USER"

# Write sudoers rule
sudo tee "$SUDOERS_FILE" > /dev/null <<EOF
# Allow $CURRENT_USER to manage Asterisk service without password
$CURRENT_USER ALL=(ALL) NOPASSWD: /bin/systemctl start asterisk
$CURRENT_USER ALL=(ALL) NOPASSWD: /bin/systemctl stop asterisk
$CURRENT_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart asterisk
$CURRENT_USER ALL=(ALL) NOPASSWD: /bin/systemctl status asterisk
$CURRENT_USER ALL=(ALL) NOPASSWD: /bin/systemctl is-active asterisk
EOF

# Set correct permissions
sudo chmod 0440 "$SUDOERS_FILE"

# Validate sudoers file
if sudo visudo -c -f "$SUDOERS_FILE" > /dev/null 2>&1; then
    echo ""
    echo "=========================================="
    echo "SUCCESS!"
    echo "=========================================="
    echo ""
    echo "Passwordless sudo configured for Asterisk."
    echo ""
    echo "The desktop app can now start Asterisk automatically!"
    echo ""
    echo "Test it:"
    echo "  sudo -n systemctl start asterisk"
    echo ""
else
    echo ""
    echo "ERROR: Sudoers file validation failed!"
    echo "Removing invalid file..."
    sudo rm -f "$SUDOERS_FILE"
    exit 1
fi
