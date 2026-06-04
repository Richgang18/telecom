"""Test a call via SignalWire with the new number."""
import requests, configparser
from pathlib import Path

cfg = configparser.ConfigParser()
cfg.read_string(Path(__file__).parent.joinpath("config.ini").read_text(encoding="utf-8-sig"))

sid     = cfg["twilio"]["account_sid"]
tok     = cfg["twilio"]["auth_token"]
space   = "https://" + cfg["signalwire"]["space_url"].strip()
base    = f"{space}/api/laml/2010-04-01/Accounts/{sid}"
webhook = cfg["twilio"]["webhook_base_url"].strip().rstrip("/")
auth    = (sid, tok)
from_num = cfg["twilio"]["from_number"]
to_num   = cfg["agents"].get("agent_mobile_numbers", "").split(",")[0].strip()

print(f"From:    {from_num}")
print(f"To:      {to_num}")
print(f"Webhook: {webhook}")
print()

r = requests.post(f"{base}/Calls.json", data={
    "To":                         to_num,
    "From":                       from_num,
    "Url":                        f"{webhook}/ringing",
    "StatusCallback":             f"{webhook}/call-status",
    "StatusCallbackEvent":        ["initiated", "ringing", "answered", "completed"],
    "StatusCallbackMethod":       "POST",
    "Timeout":                    "20",
    "MachineDetection":           "DetectMessageEnd",
    "MachineDetectionTimeout":    "30",
    "AsyncAmd":                   "true",
    "AsyncAmdStatusCallback":     f"{webhook}/connect",
    "AsyncAmdStatusCallbackMethod": "POST",
}, auth=auth, timeout=15)

print(f"HTTP {r.status_code}")
d = r.json()
if r.ok:
    print(f"SID:    {d.get('sid')}")
    print(f"Status: {d.get('status')}")
    print("SUCCESS — call initiated with new number")
else:
    for e in d.get("errors", []):
        print(f"Error {e.get('code')}: {e.get('message')}")
    if not d.get("errors"):
        print(d)
