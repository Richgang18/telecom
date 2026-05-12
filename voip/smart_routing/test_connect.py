"""
Test script - simulates exactly what Twilio sends to /connect
Run: python test_connect.py
"""
import urllib.request
import urllib.parse

data = urllib.parse.urlencode({
    "CallSid": "CA_TEST_123456",
    "AnsweredBy": "unknown",
    "CallStatus": "in-progress",
    "To": "+19124971682",
    "From": "+17868339866",
    "AccountSid": "ACcf15065d54bfedd91baec3cc1283561c",
    "Direction": "outbound-api",
}).encode()

req = urllib.request.Request(
    "http://localhost:5000/connect",
    data=data,
    method="POST",
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode()
        print(f"Status: {resp.status}")
        print(f"Response:\n{body}")
except Exception as e:
    print(f"ERROR: {e}")
