# 📞 Smart Outbound Dialer

Professional VoIP call center system with mobile agent support.

## 🚀 Quick Start

### 1. Run the Launcher
```
Launch_Dialer.bat
```

This automatically starts everything:
- WSL2 + Asterisk
- Webhook Server
- Ngrok Tunnel
- Desktop Application

### 2. Configure Mobile Number

In the Desktop App:
1. Go to **Settings** tab
2. Enter your mobile number: `+14145551234`
3. Set agent mode: `mobile`
4. Enable AMD
5. Save

### 3. Start Calling

1. Upload contacts (CSV)
2. Click "Start Calling"
3. Answer your phone when it rings!

---

## 📱 Mobile Agent Mode

Calls bridge directly to your cellphone - no softphone needed!

**How it works:**
```
Lead Answers → System Calls Your Mobile → You Answer → Calls Bridged
```

**Benefits:**
- ✅ No softphone required
- ✅ Work from anywhere
- ✅ VICIdial-style workflow
- ✅ AMD (Answering Machine Detection)

---

## 📁 Files

### Essential Files
- `Launch_Dialer.bat` - Start everything
- `config.ini` - Configuration
- `contacts.csv` - Contact list
- `voicemail.mp3` - Voicemail audio

### Python Scripts
- `desktop_app.py` - Main GUI
- `webhook_server.py` - Twilio webhooks
- `dialer.py` - Outbound dialer
- `agent_router.py` - Agent routing
- `voicemail_drop.py` - Voicemail handler

### Documentation
- `GETTING_STARTED.md` - Quick start guide
- `MOBILE_AGENT_GUIDE.md` - Mobile agent details
- `QUICK_REFERENCE.md` - Command reference
- `COMPLETE_SYSTEM_GUIDE.md` - Full documentation
- `SYSTEM_ARCHITECTURE.md` - Technical details
- `IMPLEMENTATION_COMPLETE.md` - What's been implemented

---

## ⚙️ Configuration

**config.ini:**
```ini
[twilio]
account_sid = ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx
auth_token = your_auth_token
from_number = +17868339866
webhook_base_url = https://your-ngrok-url.ngrok-free.dev

[agents]
agent_mode = mobile
agent_mobile_numbers = +14145551234
agent_timeout = 20
enable_amd = true
```

---

## 📋 Contact List Format

**CSV Format:**
```csv
Firstname,Lastname,Dob,Phone,Address1,Address2,City,Zip
John,Smith,1980-01-15,+14145551001,123 Main St,,Milwaukee,53202
```

**Required:** Phone (E.164 format: +1XXXXXXXXXX)

---

## 🔧 Troubleshooting

### Phone doesn't ring
- Check mobile number format: `+1XXXXXXXXXX`
- Check AMD settings
- Check Twilio console

### Services won't start
```bash
# Check Asterisk
wsl sudo systemctl status asterisk

# Check ports
netstat -ano | findstr :5000
```

### No audio
- Check mobile signal
- Enable WiFi calling
- Check Twilio trunk

---

## 📚 Documentation

- **Quick Start:** [GETTING_STARTED.md](GETTING_STARTED.md)
- **Mobile Agent:** [MOBILE_AGENT_GUIDE.md](MOBILE_AGENT_GUIDE.md)
- **Commands:** [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **Complete Guide:** [COMPLETE_SYSTEM_GUIDE.md](COMPLETE_SYSTEM_GUIDE.md)

---

## 💰 Cost

**Mobile mode:** ~$0.026/min (2x softphone)
- Twilio → Lead: $0.013/min
- Twilio → Mobile: $0.013/min

---

## ✅ Features

- ✅ Mobile agent bridging (VICIdial-style)
- ✅ Answering machine detection
- ✅ Automatic voicemail drop
- ✅ Call tracking & reporting
- ✅ Agent routing
- ✅ One-click launcher
- ✅ Desktop GUI

---

**Ready to start?** Run `Launch_Dialer.bat` and start calling! 🚀
