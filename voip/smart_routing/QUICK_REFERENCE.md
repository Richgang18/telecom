# 🚀 Quick Reference Card

## Start System (5 Steps)

```powershell
# 1. Launch app
python desktop_app.py

# 2. Start services (in app)
Dashboard → "🚀 Start Services"

# 3. Launch softphones (in app)
Softphone → "🚀 Launch Softphone" (Agent 1)
Softphone → "🚀 Launch Softphone" (Agent 2)

# 4. Upload contacts (in app)
Contacts → "📁 Browse CSV File"

# 5. Start calling (in app)
Dashboard → "▶ Start Calling"
```

---

## Common Commands

### Asterisk

```bash
# Status
wsl sudo systemctl status asterisk

# Console
wsl sudo asterisk -rvvvvv

# Show endpoints
wsl sudo asterisk -rx "pjsip show endpoints"

# Reload
wsl sudo asterisk -rx "pjsip reload"
```

### Services

```powershell
# Check webhook
curl http://localhost:5000/status

# Check ngrok
curl http://localhost:4040/api/tunnels
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Softphone won't register | `wsl sudo systemctl restart asterisk` |
| Services won't start | Check port 5000: `netstat -ano \| findstr :5000` |
| No audio | Check Windows microphone permissions |
| Calls don't route | Verify softphones show "✓ Registered" |

---

## File Locations

```
voip/smart_routing/
├── desktop_app.py          # Main app
├── softphone.py            # Integrated softphone
├── config.ini              # Configuration
├── contacts.csv            # Contact list
├── voicemail.mp3           # Voicemail audio
├── call_results.json       # Call outcomes
└── smart_routing.log       # Activity log
```

---

## Agent Credentials

| Agent | Extension | Password | Domain |
|-------|-----------|----------|--------|
| Agent 1 | 101 | ChangeMe101! | 172.25.17.93 |
| Agent 2 | 102 | ChangeMe102! | 172.25.17.93 |

---

## Contact CSV Format

```csv
Firstname,Lastname,Dob,Phone,Address1,Address2,City,Zip
John,Smith,1980-01-15,+14145551001,123 Main St,,Milwaukee,53202
```

**Required:** `Phone` (E.164 format: +1XXXXXXXXXX)

---

## Status Indicators

| Color | Meaning |
|-------|---------|
| 🟢 Green | Running/Registered |
| 🟡 Yellow | Starting/Warning |
| 🔴 Red | Stopped/Error |
| ⚪ Gray | Unknown/Not configured |

---

## Call Flow

```
1. System dials contact
2. Customer answers?
   ├─ YES → Route to available agent
   │         └─ Agent softphone rings
   │             └─ Agent clicks "Answer"
   │                 └─ Conversation
   └─ NO → Drop voicemail
3. Agent clicks "Hangup"
4. Next call
```

---

## Emergency Stop

```
Dashboard → "⏹ Stop Calling"
Dashboard → "⏸ Stop Services"
Close softphone windows
Close desktop app
```

---

## Getting Help

1. **Activity Log** - Check in Dashboard tab
2. **Asterisk Console** - `wsl sudo asterisk -rvvvvv`
3. **Complete Guide** - See `COMPLETE_SYSTEM_GUIDE.md`
4. **Softphone Guide** - See `INTEGRATED_SOFTPHONE_README.md`

---

## Quick Install

```powershell
# Install softphone
pip install pyaudio

# Or use automated installer
.\install_softphone.ps1
```

---

**Need detailed help?** See `COMPLETE_SYSTEM_GUIDE.md`
