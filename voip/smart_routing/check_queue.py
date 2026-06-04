"""Check all active calls for the from number and cancel them."""
import configparser, requests
from pathlib import Path

cfg = configparser.ConfigParser()
cfg.read_string(Path("config.ini").read_text(encoding="utf-8-sig"))
sid      = cfg["twilio"]["account_sid"]
tok      = cfg["twilio"]["auth_token"]
space    = "https://" + cfg["signalwire"]["space_url"].strip()
base     = f"{space}/api/laml/2010-04-01/Accounts/{sid}"
auth     = (sid, tok)
from_num = cfg["twilio"]["from_number"]

print(f"Checking calls from {from_num}...")
total_found = 0
total_cancelled = 0

for status in ["queued", "ringing", "in-progress", "initiated"]:
    r = requests.get(
        f"{base}/Calls.json",
        params={"From": from_num, "Status": status, "PageSize": 100},
        auth=auth, timeout=10
    )
    if not r.ok:
        print(f"  {status}: error {r.status_code}")
        continue
    calls = r.json().get("calls", [])
    print(f"  {status}: {len(calls)} calls")
    total_found += len(calls)
    for c in calls:
        call_sid = c.get("sid", "")
        cancel_status = "canceled" if status in ("queued", "initiated") else "completed"
        cr = requests.post(
            f"{base}/Calls/{call_sid}.json",
            data={"Status": cancel_status},
            auth=auth, timeout=10
        )
        if cr.ok:
            total_cancelled += 1
            print(f"    Cancelled {call_sid}")
        else:
            print(f"    Failed to cancel {call_sid}: {cr.status_code}")

# Also check without status filter — gets everything
print("\nChecking recent calls (no status filter, last 50)...")
r = requests.get(
    f"{base}/Calls.json",
    params={"From": from_num, "PageSize": 50},
    auth=auth, timeout=10
)
if r.ok:
    calls = r.json().get("calls", [])
    active = [c for c in calls if c.get("status") in ("queued", "ringing", "in-progress", "initiated")]
    print(f"  Total recent: {len(calls)} | Still active: {len(active)}")
    for c in active:
        print(f"    SID={c.get('sid')} status={c.get('status')} created={c.get('date_created')}")

print(f"\nTotal found: {total_found} | Cancelled: {total_cancelled}")
if total_found == 0:
    print("\nQueue appears empty. The 21611 limit may be a hard cap set by SignalWire.")
    print("This requires SignalWire support to increase the queue size for your number.")
    print("Reply to ticket #49383 and specifically request: 'Please increase the")
    print("outbound call queue size for number +12392941998'")
