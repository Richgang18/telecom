#!/bin/bash
# get_cert.sh — Automated TLS certificate via GoDaddy DNS API (direct)
# Run with: sudo -E bash get_cert.sh

set -e

DOMAIN="pbx.vouchersdept.com"
ROOT_DOMAIN="vouchersdept.com"
SUBDOMAIN="_acme-challenge.pbx"

if [ -z "$GODADDY_API_KEY" ] || [ -z "$GODADDY_API_SECRET" ]; then
    echo "Error: GoDaddy API credentials not set."
    echo "Run:"
    echo "  export GODADDY_API_KEY=your_key"
    echo "  export GODADDY_API_SECRET=your_secret"
    echo "  sudo -E bash get_cert.sh"
    exit 1
fi

AUTH_HEADER="Authorization: sso-key ${GODADDY_API_KEY}:${GODADDY_API_SECRET}"

# ---------------------------------------------------------------------------
# Step 1: Get certificate via manual DNS hook
# ---------------------------------------------------------------------------

echo "[get_cert] Starting certbot with manual DNS hooks..."

# Write the auth hook script
cat > /tmp/godaddy_auth.sh << 'HOOK'
#!/bin/bash
# Called by certbot — adds TXT record via GoDaddy API
SUBDOMAIN="_acme-challenge.pbx"
ROOT_DOMAIN="vouchersdept.com"
AUTH_HEADER="Authorization: sso-key ${GODADDY_API_KEY}:${GODADDY_API_SECRET}"

echo "[auth_hook] Adding TXT record: ${SUBDOMAIN}.${ROOT_DOMAIN} = ${CERTBOT_VALIDATION}"

curl -s -X PUT "https://api.godaddy.com/v1/domains/${ROOT_DOMAIN}/records/TXT/${SUBDOMAIN}" \
    -H "${AUTH_HEADER}" \
    -H "Content-Type: application/json" \
    -d "[{\"data\": \"${CERTBOT_VALIDATION}\", \"ttl\": 600}]"

echo ""
echo "[auth_hook] TXT record added. Waiting 60 seconds for DNS propagation..."
sleep 60
HOOK

# Write the cleanup hook script
cat > /tmp/godaddy_cleanup.sh << 'HOOK'
#!/bin/bash
# Called by certbot after challenge — removes TXT record
SUBDOMAIN="_acme-challenge.pbx"
ROOT_DOMAIN="vouchersdept.com"
AUTH_HEADER="Authorization: sso-key ${GODADDY_API_KEY}:${GODADDY_API_SECRET}"

echo "[cleanup_hook] Removing TXT record..."
curl -s -X DELETE "https://api.godaddy.com/v1/domains/${ROOT_DOMAIN}/records/TXT/${SUBDOMAIN}" \
    -H "${AUTH_HEADER}" \
    -H "Content-Type: application/json"
echo ""
echo "[cleanup_hook] TXT record removed."
HOOK

chmod +x /tmp/godaddy_auth.sh /tmp/godaddy_cleanup.sh

# Export vars so hooks can use them
export GODADDY_API_KEY
export GODADDY_API_SECRET

echo "[get_cert] Running certbot..."
certbot certonly \
    --manual \
    --preferred-challenges dns \
    --manual-auth-hook /tmp/godaddy_auth.sh \
    --manual-cleanup-hook /tmp/godaddy_cleanup.sh \
    --non-interactive \
    --agree-tos \
    --register-unsafely-without-email \
    -d "$DOMAIN"

# ---------------------------------------------------------------------------
# Step 2: Copy certs to Asterisk
# ---------------------------------------------------------------------------

echo "[get_cert] Copying certs to Asterisk..."
mkdir -p /etc/asterisk/keys
cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem /etc/asterisk/keys/
cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem /etc/asterisk/keys/
chmod 600 /etc/asterisk/keys/privkey.pem

# ---------------------------------------------------------------------------
# Step 3: Write renewal hook
# ---------------------------------------------------------------------------

mkdir -p /etc/letsencrypt/renewal-hooks/deploy
cat > /etc/letsencrypt/renewal-hooks/deploy/asterisk-reload.sh << 'EOF'
#!/bin/bash
asterisk -rx "module reload res_pjsip.so"
EOF
chmod +x /etc/letsencrypt/renewal-hooks/deploy/asterisk-reload.sh

echo "[get_cert] Certificate installed successfully!"
echo "[get_cert] Cert location: /etc/asterisk/keys/"
