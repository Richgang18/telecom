"""
test_telnyx_call.py — Make one test call via Telnyx to verify the full flow.
Usage: python test_telnyx_call.py +1XXXXXXXXXX
If no number given, calls the agent mobile number from config.
"""
import sys
import configparser
import requests
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.ini"

def load_config():
    cfg = configparser.ConfigParser()
    cfg.read_string(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    return cfg

def main():
    cfg = load_config()
    api_key       = cfg["telnyx"]["api_key"].strip()
    from_number   = cfg["telnyx"]["from_number"].strip()
    connection_id = cfg["telnyx"].get("connection_id", "").strip()
    webhook       = cfg["twilio"]["webhook_base_url"].strip().rstrip("/")

    # Target number — arg or agent mobile
    to_number = sys.argv[1] if len(sys.argv) > 1 else cfg["agents"].get("agent_mobile_numbers", "").split(",")[0].strip()

    print(f"Telnyx test call")
    print(f"  From:          {from_number}")
    print(f"  To:            {to_number}")
    print(f"  Connection ID: {connection_id or '(none — using default)'}")
    print(f"  Webhook:       {webhook}")
    print()

    payload = {
        "to": to_number,
        "from": from_number,
        "webhook_url": f"{webhook}/ringing",
        "webhook_url_method": "POST",
        "timeout_secs": 20,
        "answering_machine_detection": "detect_beep",
        "answering_machine_detection_webhook_url": f"{webhook}/connect",
    }
    if connection_id:
        payload["connection_id"] = connection_id

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    r = requests.post(
        "https://api.telnyx.com/v2/calls",
        json=payload,
        headers=headers,
        timeout=15,
    )

    print(f"HTTP {r.status_code}")
    try:
        data = r.json()
        if r.ok:
            call = data.get("data", {})
            print(f"  call_control_id: {call.get('call_control_id')}")
            print(f"  call_leg_id:     {call.get('call_leg_id')}")
            print(f"  state:           {call.get('state')}")
            print()
            print("SUCCESS — call initiated. Check your phone.")
        else:
            errors = data.get("errors", [])
            for e in errors:
                print(f"  ERROR {e.get('code')}: {e.get('title')} — {e.get('detail')}")
    except Exception:
        print(r.text[:300])

if __name__ == "__main__":
    main()
