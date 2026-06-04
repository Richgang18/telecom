"""
check_account_status.py — Check SignalWire account and number status
Run: python check_account_status.py
"""
import configparser
import requests
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.ini"

def load_config():
    cfg = configparser.ConfigParser()
    text = CONFIG_PATH.read_text(encoding="utf-8-sig")
    cfg.read_string(text)
    return cfg

def main():
    cfg = load_config()
    account_sid = cfg["twilio"]["account_sid"]
    auth_token  = cfg["twilio"]["auth_token"]
    from_number = cfg["twilio"]["from_number"]
    space_url   = cfg["signalwire"]["space_url"].strip()

    if not space_url.startswith("http"):
        space_url = f"https://{space_url}"
    base = f"{space_url.rstrip('/')}/api/laml/2010-04-01/Accounts/{account_sid}"
    auth = (account_sid, auth_token)

    print("=" * 60)
    print("SIGNALWIRE ACCOUNT STATUS CHECK")
    print("=" * 60)

    # 1. Account status
    resp = requests.get(f"{base}.json", auth=auth, timeout=10)
    if resp.ok:
        acct = resp.json()
        print(f"\nAccount SID : {acct.get('sid', 'N/A')}")
        print(f"Status      : {acct.get('status', 'N/A')}")
        print(f"Type        : {acct.get('type', 'N/A')}")
        print(f"Friendly    : {acct.get('friendly_name', 'N/A')}")
    else:
        print(f"\nFailed to fetch account: {resp.status_code} {resp.text[:200]}")

    # 2. Phone number status
    print(f"\nChecking number: {from_number}")
    num_clean = from_number.replace("+", "")
    resp2 = requests.get(
        f"{base}/IncomingPhoneNumbers.json?PhoneNumber={from_number}",
        auth=auth, timeout=10
    )
    if resp2.ok:
        data = resp2.json()
        numbers = data.get("incoming_phone_numbers", [])
        if numbers:
            n = numbers[0]
            print(f"  SID         : {n.get('sid', 'N/A')}")
            print(f"  Phone       : {n.get('phone_number', 'N/A')}")
            print(f"  Capabilities: {n.get('capabilities', {})}")
            print(f"  Status      : {n.get('status', 'active')}")
        else:
            print(f"  Number {from_number} not found in account")
    else:
        print(f"  Failed: {resp2.status_code} {resp2.text[:200]}")

    # 3. Try a test call to see exact error
    print(f"\nAttempting test call to verify queue status...")
    # Use a dummy URL that will immediately hang up
    test_resp = requests.post(
        f"{base}/Calls.json",
        data={
            "To": from_number,   # call the from number itself as a test
            "From": from_number,
            "Url": "http://twimlets.com/holdmusic?Bucket=com.twilio.music.ambient",
            "Timeout": "5",
        },
        auth=auth,
        timeout=10,
    )
    print(f"  HTTP {test_resp.status_code}")
    try:
        body = test_resp.json()
        print(f"  Code    : {body.get('code', 'N/A')}")
        print(f"  Message : {body.get('message', 'N/A')}")
        print(f"  Status  : {body.get('status', 'N/A')}")
    except Exception:
        print(f"  Body: {test_resp.text[:300]}")

    print("\n" + "=" * 60)
    print("If status shows 'suspended' or error code 20003/21611,")
    print("the account/number is restricted by SignalWire.")
    print("Reply to ticket #49383 via the SignalWire support portal.")
    print("=" * 60)

if __name__ == "__main__":
    main()
