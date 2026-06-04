"""
setup_telnyx.py — Auto-configure Telnyx and verify setup.
Run: python setup_telnyx.py
"""
import configparser
import io
import requests
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

def main():
    cfg = load_config()
    api_key  = cfg["telnyx"]["api_key"].strip()
    from_num = cfg["telnyx"]["from_number"].strip()
    webhook  = cfg["twilio"].get("webhook_base_url", "").strip()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    print("=" * 60)
    print("TELNYX SETUP")
    print("=" * 60)

    # 1. Verify API key by listing phone numbers
    print("\n1. Verifying API key...")
    r = requests.get(
        "https://api.telnyx.com/v2/phone_numbers?page[size]=20",
        headers=headers, timeout=15
    )
    if not r.ok:
        print(f"   ERROR {r.status_code}: {r.text[:300]}")
        return
    all_nums = r.json().get("data", [])
    print(f"   API key valid — {len(all_nums)} number(s) on account")
    for n in all_nums:
        print(f"     {n.get('phone_number')} | status={n.get('status')} | id={n.get('id')}")

    # 2. Get or create outbound voice profile
    print("\n2. Looking for outbound voice profile...")
    r2 = requests.get(
        "https://api.telnyx.com/v2/outbound_voice_profiles?page[size]=5",
        headers=headers, timeout=15
    )
    connection_id = ""
    if r2.ok:
        profiles = r2.json().get("data", [])
        if profiles:
            connection_id = profiles[0].get("id", "")
            print(f"   Found: {profiles[0].get('name')} | id={connection_id}")
        else:
            print("   None found — creating one...")
            rc = requests.post(
                "https://api.telnyx.com/v2/outbound_voice_profiles",
                headers=headers,
                json={
                    "name": "Smart Dialer Outbound",
                    "traffic_type": "conversational",
                    "service_plan": "us",
                    "enabled": True,
                    "concurrent_call_limit": 100,
                    "whitelisted_destinations": ["US"],
                },
                timeout=15,
            )
            if rc.ok:
                connection_id = rc.json().get("data", {}).get("id", "")
                print(f"   Created | id={connection_id}")
            else:
                print(f"   Create failed: {rc.status_code} {rc.text[:200]}")
    else:
        print(f"   Error: {r2.status_code} {r2.text[:100]}")

    # 3. Match from_number and assign to connection
    print(f"\n3. Checking from_number {from_num}...")
    matched = [n for n in all_nums if n.get("phone_number") == from_num]
    if not matched and all_nums:
        # use first available number
        first = all_nums[0]
        print(f"   {from_num} not found — using {first.get('phone_number')} instead")
        from_num = first.get("phone_number", "")
        cfg["telnyx"]["from_number"] = from_num
        matched = [first]

    if matched and connection_id:
        num_id = matched[0].get("id", "")
        print(f"   Assigning {from_num} to outbound profile...")
        ra = requests.patch(
            f"https://api.telnyx.com/v2/phone_numbers/{num_id}",
            headers=headers,
            json={"connection_id": connection_id},
            timeout=15,
        )
        if ra.ok:
            print(f"   Assigned successfully")
        else:
            print(f"   Assignment failed: {ra.status_code} {ra.text[:150]}")
    elif matched:
        print(f"   Number found but no connection_id to assign")

    # 4. Save to config
    if connection_id:
        cfg["telnyx"]["connection_id"] = connection_id
    save_config(cfg)
    print(f"\n4. Config saved")
    print(f"   api_key:       {api_key[:20]}...")
    print(f"   from_number:   {from_num}")
    print(f"   connection_id: {connection_id or '(none)'}")
    print(f"   webhook:       {webhook or '(not set)'}")

    print("\n" + "=" * 60)
    print("Telnyx setup complete. Restart the API and run a campaign.")
    print("=" * 60)

if __name__ == "__main__":
    main()
