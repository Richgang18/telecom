"""Create or reuse a Telnyx Call Control Application for outbound calls."""
import requests, configparser, io
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.ini"

def load_config():
    cfg = configparser.ConfigParser()
    cfg.read_string(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    return cfg

def save_config(cfg):
    buf = io.StringIO()
    cfg.write(buf)
    CONFIG_PATH.write_text(buf.getvalue(), encoding="utf-8")

cfg = load_config()
key     = cfg["telnyx"]["api_key"].strip()
webhook = cfg["twilio"]["webhook_base_url"].strip().rstrip("/")
h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

print(f"Webhook: {webhook}")

# List existing call control apps
r = requests.get("https://api.telnyx.com/v2/call_control_applications", headers=h, timeout=10)
print(f"Call control apps: HTTP {r.status_code}")
apps = r.json().get("data", []) if r.ok else []
for a in apps:
    print(f"  id={a['id']}  name={a.get('application_name')}  webhook={a.get('webhook_event_url')}")

if apps:
    app_id = apps[0]["id"]
    print(f"\nUsing existing app: {app_id}")
    # Update webhook to current ngrok URL
    ru = requests.patch(
        f"https://api.telnyx.com/v2/call_control_applications/{app_id}",
        headers=h,
        json={"webhook_event_url": f"{webhook}/telnyx"},
        timeout=10,
    )
    print(f"Webhook update: HTTP {ru.status_code}")
else:
    print("\nCreating new Call Control Application...")
    rc = requests.post(
        "https://api.telnyx.com/v2/call_control_applications",
        headers=h,
        json={
            "application_name": "Smart Dialer",
            "webhook_event_url": f"{webhook}/telnyx",
            "webhook_api_version": "2",
            "dtmf_type": "RFC 2833",
            "first_command_timeout": True,
            "first_command_timeout_secs": 30,
        },
        timeout=15,
    )
    print(f"Create: HTTP {rc.status_code}")
    if not rc.ok:
        print(rc.text[:400])
        exit(1)
    app_id = rc.json()["data"]["id"]
    print(f"Created app id={app_id}")

# Assign phone number to this app
num_id = "2973971289267504291"
print(f"\nAssigning +19109090124 to call control app {app_id}...")
ra = requests.patch(
    f"https://api.telnyx.com/v2/phone_numbers/{num_id}",
    headers=h,
    json={"connection_id": app_id},
    timeout=10,
)
print(f"Assignment: HTTP {ra.status_code}")
if not ra.ok:
    print(ra.text[:200])

# Save to config
cfg["telnyx"]["connection_id"] = app_id
save_config(cfg)
print(f"\nSaved connection_id={app_id} to config.ini")
print("Done — run test_telnyx_call.py to verify")
