# Smart Outbound Routing System

Automated outbound calling with live agent connection and voicemail drop.

## How It Works

```
Contact list (CSV)
       ↓
   Dialer checks available agents (max 2 at a time)
       ↓
   Twilio dials contact
       ↓
   ┌─────────────────────────────────────┐
   │ Answered by human?                  │
   │   YES → /connect → bridge to agent  │
   │   NO  → /no-answer → voicemail drop │
   └─────────────────────────────────────┘
       ↓
   Agent completes call → marked available → next contact dialed
```

- **2 simultaneous calls** — one per agent, never more than available agents
- **Live agent connection** — answered calls bridge instantly to extension 101 or 102
- **Voicemail drop** — unanswered calls play your pre-recorded message
- **Answering machine detection** — Twilio detects machines and drops voicemail automatically

---

## Setup

### 1. Install dependencies

```bash
cd voip/smart_routing
pip3 install -r requirements.txt
```

### 2. Fill in config.ini

Open `config.ini` and fill in all values:

```ini
[twilio]
account_sid = ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx   # from twilio.com/console
auth_token  = your_auth_token                      # from twilio.com/console
from_number = +14145551000                         # your Twilio number
webhook_base_url = https://pbx.vouchersdept.com    # your public URL

[calley]
api_key = your_calley_api_key
team_id = your_calley_team_id

[agents]
max_concurrent_calls = 2
agent_extensions = 101,102
agent_names = Agent 1,Agent 2
```

### 3. Add your voicemail recording

Record a short voicemail message (MP3 or WAV) and save it as:
```
voip/smart_routing/voicemail.mp3
```

Keep it under 30 seconds. Example script:
> "Hi, this is [Your Name] from [Company]. I'm reaching out about [reason].
> Please call me back at [number]. Thank you!"

### 4. Add your contacts

Edit `contacts.csv`:
```csv
name,phone_number
John Smith,+14145551001
Jane Doe,+14145551002
```

All numbers must be in E.164 format (+1XXXXXXXXXX for US numbers).

### 5. Make sure agents are logged into Linphone

Both agents (extensions 101 and 102) must be registered on Linphone
before starting the dialer. Check status:
```bash
asterisk -rx "pjsip show registrations"
```

### 6. Start the webhook server

```bash
python3 webhook_server.py
```

The server runs on port 5000. Twilio must be able to reach it at the
`webhook_base_url` configured in config.ini.

### 7. Run the dialer

```bash
# Dial all contacts
python3 dialer.py

# Preview without making real calls
python3 dialer.py --dry-run

# Dial first 10 contacts only
python3 dialer.py --limit 10
```

---

## Monitoring

### Check agent availability (live)
```
GET http://localhost:5000/status
```
Returns JSON with agent status and available count.

### View call logs
```bash
tail -f smart_routing.log
```

### Check active calls in Asterisk
```bash
asterisk -rx "core show channels"
```

---

## File Structure

```
smart_routing/
├── config.ini          ← All credentials and settings go here
├── dialer.py           ← Outbound dialer (run this to start calling)
├── webhook_server.py   ← Flask server handling Twilio webhooks
├── agent_router.py     ← Agent availability tracking and TwiML generation
├── voicemail_drop.py   ← Voicemail drop TwiML generation
├── contacts.csv        ← Contact list (name, phone_number)
├── voicemail.mp3       ← Your pre-recorded voicemail (add this file)
├── requirements.txt    ← Python dependencies
└── smart_routing.log   ← Call logs (auto-created)
```

---

## Twilio Console Setup

1. Log into twilio.com/console
2. Go to **Phone Numbers → Manage → Active Numbers**
3. Click your number
4. Under **Voice Configuration**, set:
   - **A call comes in**: Webhook → `https://pbx.vouchersdept.com/connect`
   - **Call status changes**: `https://pbx.vouchersdept.com/no-answer`
5. Save

---

## Troubleshooting

**Calls not connecting to agents**
- Check agents are registered: `asterisk -rx "pjsip show registrations"`
- Check webhook server is running: `curl http://localhost:5000/status`
- Check Twilio webhook URL is correct in config.ini

**Voicemail not playing**
- Confirm `voicemail.mp3` exists in the smart_routing folder
- Check the file is accessible: `curl https://pbx.vouchersdept.com/voicemail-audio`

**All agents showing busy**
- Check `smart_routing.log` for agent-complete events
- Restart webhook_server.py to reset agent state
