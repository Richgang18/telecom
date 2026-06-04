import configparser, csv
from pathlib import Path

cfg = configparser.ConfigParser()
cfg.read_string(Path("voip/smart_routing/config.ini").read_text(encoding="utf-8-sig"))

print("=" * 50)
print("PRE-CAMPAIGN READINESS CHECK")
print("=" * 50)

# Provider
sw = cfg["signalwire"].get("space_url", "").strip() if cfg.has_section("signalwire") else ""
tx = cfg["telnyx"].get("api_key", "").strip() if cfg.has_section("telnyx") else ""
if tx:
    print(f"Provider:      Telnyx (KEY...{tx[-6:]})")
elif sw:
    print(f"Provider:      SignalWire ({sw})")
else:
    print("Provider:      Twilio")

print(f"From number:   {cfg['twilio']['from_number']}")
print(f"Webhook:       {cfg['twilio']['webhook_base_url']}")
print(f"Agent mode:    {cfg['agents']['agent_mode']}")
print(f"Concurrency:   {cfg['dialer']['concurrent_calls']} call(s) at a time")
print(f"Batch delay:   {cfg['dialer']['batch_delay']}s between batches")

# Voicemail
vm = Path("voip/smart_routing") / cfg["voicemail"]["voicemail_file"]
if vm.exists():
    print(f"Voicemail:     {vm.name} ({vm.stat().st_size:,} bytes) ✓")
else:
    print(f"Voicemail:     MISSING — upload via Settings")

# Contacts
contacts = Path("voip/smart_routing") / cfg["dialer"]["contact_list"]
if contacts.exists():
    with open(contacts, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("phone_number", "").strip()]
    print(f"Contacts:      {len(rows):,} ready to dial ✓")
    # Estimate time
    delay = float(cfg["dialer"]["batch_delay"])
    conc  = int(cfg["dialer"]["concurrent_calls"])
    est_mins = (len(rows) * delay / conc) / 60
    print(f"Est. duration: ~{est_mins:.0f} minutes at current settings")
else:
    print("Contacts:      NOT FOUND — upload via Contacts tab")

print("=" * 50)
