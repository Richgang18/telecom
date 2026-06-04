"""
cancel_queued_calls.py — Cancel all queued/in-progress outbound calls
on the SignalWire account to clear the outbound queue.

Run once: python cancel_queued_calls.py
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
    space_url   = cfg["signalwire"]["space_url"].strip()

    if not space_url.startswith("http"):
        space_url = f"https://{space_url}"
    base = f"{space_url.rstrip('/')}/api/laml/2010-04-01/Accounts/{account_sid}"
    auth = (account_sid, auth_token)

    print(f"Connecting to: {base}")

    # Fetch all calls with queued or in-progress status
    cancelled = 0
    failed    = 0
    page_url  = f"{base}/Calls.json?Status=queued&PageSize=100"

    while page_url:
        resp = requests.get(page_url, auth=auth, timeout=15)
        if not resp.ok:
            print(f"Error fetching calls: {resp.status_code} {resp.text}")
            break
        data = resp.json()
        calls = data.get("calls", [])
        print(f"Found {len(calls)} queued calls on this page...")

        for call in calls:
            sid = call.get("sid") or call.get("Sid", "")
            if not sid:
                continue
            # Cancel by setting status to "canceled"
            r = requests.post(
                f"{base}/Calls/{sid}.json",
                data={"Status": "canceled"},
                auth=auth,
                timeout=10,
            )
            if r.ok:
                cancelled += 1
                print(f"  Cancelled: {sid}")
            else:
                failed += 1
                print(f"  Failed to cancel {sid}: {r.status_code} {r.text[:100]}")

        # Follow pagination
        next_page = data.get("next_page_uri", "")
        if next_page:
            page_url = f"{space_url.rstrip('/')}{next_page}"
        else:
            page_url = None

    # Also cancel in-progress calls
    page_url = f"{base}/Calls.json?Status=in-progress&PageSize=100"
    while page_url:
        resp = requests.get(page_url, auth=auth, timeout=15)
        if not resp.ok:
            break
        data = resp.json()
        calls = data.get("calls", [])
        print(f"Found {len(calls)} in-progress calls on this page...")

        for call in calls:
            sid = call.get("sid") or call.get("Sid", "")
            if not sid:
                continue
            r = requests.post(
                f"{base}/Calls/{sid}.json",
                data={"Status": "completed"},
                auth=auth,
                timeout=10,
            )
            if r.ok:
                cancelled += 1
                print(f"  Completed: {sid}")
            else:
                failed += 1
                print(f"  Failed: {sid}: {r.status_code} {r.text[:100]}")

        next_page = data.get("next_page_uri", "")
        if next_page:
            page_url = f"{space_url.rstrip('/')}{next_page}"
        else:
            page_url = None

    print(f"\nDone. Cancelled/completed: {cancelled} | Failed: {failed}")
    print("Wait 30 seconds then try your campaign again.")

if __name__ == "__main__":
    main()
