"""
Upload voicemail.mp3 to SignalWire media storage and update config with direct URL.
Run once: python upload_voicemail_signalwire.py
"""
import configparser, io, requests
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
auth    = (sid, tok)
vm_path = Path(__file__).parent / cfg["voicemail"].get("voicemail_file", "voicemail.mp3")

if not vm_path.exists():
    print(f"ERROR: {vm_path} not found")
    exit(1)

print(f"Uploading {vm_path.name} ({vm_path.stat().st_size:,} bytes) to SignalWire...")

# Upload via SignalWire Compatibility API recordings/media endpoint
# SignalWire supports uploading media via their REST API
upload_url = f"{space}/api/laml/2010-04-01/Accounts/{sid}/Recordings.json"

# Actually use the correct endpoint — SignalWire media upload
media_url = f"{space}/api/laml/2010-04-01/Accounts/{sid}/Media.json"

with open(vm_path, "rb") as f:
    r = requests.post(
        media_url,
        files={"Media": (vm_path.name, f, "audio/mpeg")},
        auth=auth,
        timeout=30,
    )

print(f"HTTP {r.status_code}")

if r.ok:
    data = r.json()
    media_sid = data.get("sid", "")
    direct_url = f"{space}/api/laml/2010-04-01/Accounts/{sid}/Media/{media_sid}.mp3"
    print(f"Uploaded! SID: {media_sid}")
    print(f"Direct URL: {direct_url}")
    cfg["voicemail"]["voicemail_url"] = direct_url
    save_cfg(cfg)
    print("Saved voicemail_url to config.ini")
else:
    print(f"Upload failed: {r.text[:300]}")
    print("\nFallback: Using direct MP3 URL from a public host.")
    print("Upload voicemail.mp3 to any public URL (e.g. Dropbox, Google Drive direct link)")
    print("Then set voicemail_url = https://your-url/voicemail.mp3 in config.ini")
