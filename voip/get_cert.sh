#!/bin/bash
# get_cert.sh — Automated TLS certificate via GoDaddy DNS API
# Run with: sudo -E bash get_cert.sh

set -e

if [ -z "$GODADDY_API_KEY" ] || [ -z "$GODADDY_API_SECRET" ]; then
    echo "Error: GoDaddy API credentials not set."
    echo "Run:"
    echo "  export GODADDY_API_KEY=your_key"
    echo "  export GODADDY_API_SECRET=your_secret"
    echo "  sudo -E bash get_cert.sh"
    exit 1
fi

echo "[get_cert] Installing certbot-dns-godaddy plugin..."
pip3 install certbot-dns-godaddy==0.1.1

echo "[get_cert] Writing GoDaddy credentials..."
mkdir -p /etc/letsencrypt
cat > /etc/letsencrypt/godaddy.ini <<EOF
dns_godaddy_secret = $GODADDY_API_SECRET
dns_godaddy_key = $GODADDY_API_KEY
EOF
chmod 600 /etc/letsencrypt/godaddy.ini

echo "[get_cert] Running certbot with automated DNS challenge..."
certbot certonly \
    --authenticator dns-godaddy \
    --dns-godaddy-credentials /etc/letsencrypt/godaddy.ini \
    --dns-godaddy-propagation-seconds 60 \
    --non-interactive \
    --agree-tos \
    --register-unsafely-without-email \
    -d pbx.vouchersdept.com

echo "[get_cert] Copying certs to Asterisk..."
mkdir -p /etc/asterisk/keys
cp /etc/letsencrypt/live/pbx.vouchersdept.com/fullchain.pem /etc/asterisk/keys/
cp /etc/letsencrypt/live/pbx.vouchersdept.com/privkey.pem /etc/asterisk/keys/
chmod 600 /etc/asterisk/keys/privkey.pem

echo "[get_cert] Certificate installed successfully!"
