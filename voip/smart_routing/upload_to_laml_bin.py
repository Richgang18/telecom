"""
Create a SignalWire LaML Bin that plays the voicemail audio.
The bin URL is a direct SignalWire URL — no ngrok needed.
Run once: python upload_to_laml_bin.py
"""
import configparser, io, base64, requests
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.ini"

def load_cfg():
    cfg = configparser.ConfigParser()
    cfg.read_string(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    return cfg

def save_cfg(cfg):
    buf = io.StringIO()
    cfg.write(buf)
    CONFIG_PATH.write_text(buf.getvalue(), encoding="utf-8")

cfg = load_cfg()
sid     = cfg["twilio"]["account_sid"]
tok     = cfg["twilio"]["auth_token"]
space   = "https://" + cfg["signalwire"]["space_url"].strip()
webhook = cfg["twilio"]["webhook_base_url"].strip().rstrip("/")
auth    = (sid, tok)
vm_path = Path(__file__).parent / cfg["voicemail"].get("voicemail_file", "voicemail.mp3")

# Option 1: Create a LaML Bin with <Play> pointing to the ngrok URL
# but with User-Agent spoofing to bypass interstitial
# This won't work since SW controls the request

# Option 2: Create a LaML Bin that uses the voicemail file from a CDN
# For now: create a LaML bin that plays from the ngrok URL with skip header
# SignalWire internally doesn't hit the ngrok interstitial — it uses server UA

# Actually test if SW bypasses ngrok interstitial naturally
print("Testing if SignalWire bypasses ngrok interstitial when fetching audio...")
test_url = f"{webhook}/voicemail-audio"
r = requests.get(test_url, timeout=10)
ct = r.headers.get("content-type", "")
print(f"  HTTP {r.status_code} | Content-Type: {ct} | Size: {len(r.content)} bytes")

if "audio" in ct or "mpeg" in ct:
    print("  Audio is served correctly — ngrok is NOT blocking it")
    print("  The issue may be something else. Testing with SW UA...")
else:
    print(f"  Got non-audio response — ngrok IS blocking it (content-type: {ct})")
    print(f"  First 200 chars: {r.text[:200]}")

# Test with SignalWire-like User-Agent
r2 = requests.get(test_url, timeout=10,
    headers={"User-Agent": "SignalWire/1.0", "ngrok-skip-browser-warning": "1"})
ct2 = r2.headers.get("content-type", "")
print(f"\nWith skip header: HTTP {r2.status_code} | Content-Type: {ct2} | Size: {len(r2.content)} bytes")
if "audio" in ct2 or "mpeg" in ct2:
    print("  Header bypass works!")
else:
    print(f"  Still blocked: {r2.text[:100]}")

print("\nChecking ngrok config...")
try:
    ng = requests.get("http://localhost:4040/api/tunnels", timeout=2)
    if ng.ok:
        tunnels = ng.json().get("tunnels", [])
        for t in tunnels:
            print(f"  Tunnel: {t.get('public_url')} -> {t.get('config', {}).get('addr')}")
            print(f"  Headers: {t.get('config', {}).get('request_header_add', [])}")
except Exception:
    print("  ngrok admin API not reachable")
