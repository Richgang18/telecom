# 📘 Complete System Guide - Smart Outbound Dialer

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Using the System](#using-the-system)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Features](#advanced-features)
9. [FAQ](#faq)

---

## System Overview

The **Smart Outbound Dialer** is a complete VoIP calling system that:

- 📞 **Makes automated outbound calls** to a list of contacts
- 👥 **Routes calls to available agents** (2 agents supported)
- 🎙️ **Drops voicemail** if no one answers
- 📊 **Tracks call results** (answered, voicemail, no-answer)
- 🖥️ **Provides a desktop GUI** for easy management
- 📱 **Includes integrated softphone** - no external SIP client needed!

### Key Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Windows Machine                          │
│                                                             │
│  ┌───────────────────────────────────────────────────┐    │
│  │         Desktop Application (GUI)                 │    │
│  │  • Dashboard                                      │    │
│  │  • Integrated Softphone (Agent 1 & 2)            │    │
│  │  • Contact Management                             │    │
│  │  • Call Results                                   │    │
│  │  • Settings                                       │    │
│  └───────────────────────────────────────────────────┘    │
│                          │                                  │
│                          │                                  │
│  ┌───────────────────────────────────────────────────┐    │
│  │              WSL2 Ubuntu                          │    │
│  │                                                   │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │      Asterisk PBX                       │    │    │
│  │  │  • SIP Endpoints (101, 102)             │    │    │
│  │  │  • Dialplan                             │    │    │
│  │  │  • Call Routing                         │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └───────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ SIP Trunk
                          ▼
                  ┌───────────────┐
                  │    Twilio     │
                  │  • Inbound    │
                  │  • Outbound   │
                  └───────────────┘
```

---

## Architecture

### Call Flow

```
1. Desktop App starts dialing campaign
   └─> Reads contacts from CSV
       └─> For each contact:
           └─> Checks if agent available
               ├─> If available:
               │   └─> Twilio makes outbound call
               │       └─> Customer answers?
               │           ├─> YES: Connect to agent via Asterisk
               │           │   └─> Agent's softphone rings
               │           │       └─> Agent clicks "Answer"
               │           │           └─> Conversation starts
               │           └─> NO: Drop voicemail
               └─> If busy: Wait for agent to become available

2. Agent finishes call
   └─> Clicks "Hangup"
       └─> Agent marked as available
           └─> Next call can be routed to them
```

### Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **Desktop App** | GUI for managing campaigns | Windows |
| **Integrated Softphone** | Receive calls (replaces Linphone) | Windows |
| **Webhook Server** | Handle Twilio callbacks | Windows |
| **Dialer** | Make outbound calls | Windows |
| **Agent Router** | Route calls to agents | Windows |
| **Asterisk PBX** | SIP server & call routing | WSL2 Ubuntu |
| **Twilio** | Phone service (inbound/outbound) | Cloud |
| **Ngrok** | Expose webhook to internet | Windows |

---

## Prerequisites

### Required Software

1. **Windows 10/11** with WSL2
2. **Python 3.7+**
3. **Asterisk** (in WSL2)
4. **Twilio Account** (with phone number)
5. **Ngrok** (for webhook tunneling)

### Accounts Needed

- **Twilio Account**: https://www.twilio.com/
  - Account SID
  - Auth Token
  - Phone Number

- **Ngrok Account**: https://ngrok.com/
  - Auth Token

---

## Installation

### Step 1: Install System Prerequisites

#### Windows Side

```powershell
# Install Python (if not already installed)
# Download from: https://www.python.org/downloads/

# Verify Python
python --version

# Install pip packages
pip install requests twilio pyaudio
```

#### WSL2 Side

```bash
# Update system
sudo apt-get update

# Install Asterisk
sudo apt-get install -y asterisk

# Start Asterisk
sudo systemctl start asterisk
sudo systemctl enable asterisk

# Verify Asterisk is running
sudo systemctl status asterisk
```

### Step 2: Install Integrated Softphone

```powershell
cd voip/smart_routing

# Option 1: Automated installer
.\install_softphone.ps1

# Option 2: Manual
pip install pyaudio
pip install -r requirements_softphone.txt
```

### Step 3: Install Ngrok

```powershell
# Download ngrok
# Visit: https://ngrok.com/download

# Extract to a known location
# Example: C:\Users\Admin\Downloads\ngrok-v3-stable-windows-amd64\

# Configure ngrok with your auth token
.\ngrok.exe config add-authtoken YOUR_NGROK_TOKEN
```

### Step 4: Configure Asterisk

```bash
# In WSL2, run the Asterisk configuration script
cd /mnt/c/Users/Admin/SPdevTech/telecom/voip/smart_routing
sudo bash fix_asterisk.sh
```

This will:
- Configure SIP endpoints (101, 102)
- Set up transports (TCP on port 5060)
- Create dialplan
- Reload Asterisk

---

## Configuration

### Step 1: Configure Twilio

1. **Get Twilio Credentials:**
   - Login to https://www.twilio.com/console
   - Copy your **Account SID**
   - Copy your **Auth Token**
   - Note your **Phone Number** (in E.164 format: +1234567890)

2. **Update config.ini:**

```ini
[twilio]
account_sid = ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx
auth_token = your_auth_token_here
from_number = +17868339866
webhook_base_url = https://your-ngrok-url.ngrok-free.dev
```

### Step 2: Configure Agents

The system comes pre-configured with 2 agents:

| Agent | Extension | Password | Domain |
|-------|-----------|----------|--------|
| Agent 1 | 101 | ChangeMe101! | 172.25.17.93 |
| Agent 2 | 102 | ChangeMe102! | 172.25.17.93 |

**To change passwords:**

```bash
# Edit Asterisk config
wsl sudo nano /etc/asterisk/pjsip.conf

# Find [auth101] and [auth102] sections
# Change the password= line
# Save and reload
wsl sudo asterisk -rx "pjsip reload"
```

### Step 3: Prepare Contact List

Create a CSV file with your contacts:

**Format:** `contacts.csv`

```csv
Firstname,Lastname,Dob,Phone,Address1,Address2,City,Zip
John,Smith,1980-01-15,+14145551001,123 Main St,,Milwaukee,53202
Jane,Doe,1985-05-20,+14145551002,456 Oak Ave,,Madison,53703
```

**Required columns:**
- `Phone` - Must be in E.164 format (+1XXXXXXXXXX)

**Optional columns:**
- `Firstname`, `Lastname`, `Dob`, `Address1`, `Address2`, `City`, `Zip`

### Step 4: Record Voicemail Message

Record your voicemail message and save as `voicemail.mp3` in the `voip/smart_routing/` folder.

**Example script:**
> "Hi, this is [Your Name] from [Company]. I tried to reach you but you're unavailable. Please call us back at [Phone Number]. Thank you!"

---

## Using the System

### Complete Workflow (Start to Finish)

#### 1. Start Services

```powershell
# Navigate to project folder
cd voip\smart_routing

# Launch desktop app
python desktop_app.py
```

#### 2. Start Backend Services

In the Desktop App:

1. Go to **Dashboard** tab
2. Click **"🚀 Start Services"**
   - This starts the webhook server
   - This starts ngrok tunnel
3. Wait for status indicators to turn green:
   - ✅ Asterisk: Running
   - ✅ Webhook Server: Running on port 5000
   - ✅ Ngrok Tunnel: Active

#### 3. Update Webhook URL

1. Click **"🔄 Auto-detect Ngrok URL"** button
2. The webhook URL will be automatically filled
3. Click **"💾 Save Settings"**

**Or manually:**
- Copy the ngrok URL from the status (e.g., `https://abc123.ngrok-free.dev`)
- Paste into Settings → Webhook URL
- Save

#### 4. Launch Agent Softphones

1. Go to **"📞 Softphone"** tab
2. Click **"🚀 Launch Softphone"** for Agent 1
   - A new window opens
   - Wait for "✓ Registered" status
3. Click **"🚀 Launch Softphone"** for Agent 2
   - Another window opens
   - Wait for "✓ Registered" status

**Both agents are now ready to receive calls!**

#### 5. Upload Contacts

1. Go to **"📋 Contacts"** tab
2. Click **"📁 Browse CSV File"**
3. Select your `contacts.csv` file
4. Verify contacts are loaded in the table

#### 6. Start Calling Campaign

1. Go to **"📊 Dashboard"** tab
2. Click **"▶ Start Calling"**
3. Confirm the prompt
4. Watch the Activity Log for progress

**The system will:**
- Dial contacts one by one
- Route answered calls to available agents
- Drop voicemail for unanswered calls
- Wait when both agents are busy
- Resume when an agent becomes available

#### 7. Agent Receives Call

When a call comes in:

1. **Softphone window flashes**
2. **System beep sounds**
3. **Caller info displays**
4. **Agent clicks "📞 Answer"**
5. **Conversation starts**
6. **Agent clicks "📵 Hangup"** when done

#### 8. Monitor Results

1. Go to **"📞 Call Results"** tab
2. See all call outcomes:
   - ✅ Answered (green)
   - 📧 Voicemail (yellow)
   - ❌ No Answer (red)
3. Filter by status
4. Export to CSV

#### 9. Stop Campaign

1. Go to **"📊 Dashboard"** tab
2. Click **"⏹ Stop Calling"**
3. Confirm the prompt

#### 10. Shutdown

1. Close agent softphone windows
2. Click **"⏸ Stop Services"**
3. Close desktop app

---

## Desktop App Features

### Dashboard Tab

**System Status:**
- Asterisk status indicator
- Webhook server status
- Ngrok tunnel status

**Campaign Control:**
- Start/Stop calling buttons
- Start/Stop services buttons
- Refresh status button

**Statistics:**
- Total contacts
- Answered calls
- Voicemail drops
- No answers

**Activity Log:**
- Real-time event logging
- Call progress updates
- Error messages

### Softphone Tab

**Agent Softphones:**
- Launch buttons for Agent 1 & 2
- Status indicators (Running/Not Running)
- Instructions

**Features:**
- Automatic SIP registration
- Visual call display
- One-click answer/hangup
- Call duration timer
- Activity logging

### Contacts Tab

**Upload Contacts:**
- Browse CSV file
- Reload contacts
- Clear all contacts

**Contact Table:**
- View all loaded contacts
- Name, Phone, City, Zip columns
- Scrollable list

### Call Results Tab

**Filter Results:**
- Filter by status (All, Answered, Voicemail, No Answer, Busy, Failed)
- Refresh button
- Export to CSV

**Results Table:**
- Timestamp
- Name
- Phone
- Status
- Agent who handled the call

**Summary:**
- Total calls
- Breakdown by status

### Settings Tab

**Twilio Configuration:**
- Account SID
- Auth Token
- From Number
- Webhook URL (with auto-detect)

**Voicemail Configuration:**
- Voicemail file path
- Browse button

**Dialer Configuration:**
- Ring timeout (seconds)
- Batch delay (seconds)

**Save Button:**
- Save all settings to config.ini

### Agents Tab

**Agent Configuration:**
- Extension numbers
- Passwords
- Domain
- Port

**Agent Status:**
- Extension
- Name
- Status (Available/Busy/Unknown)
- Current call

**Refresh Button:**
- Update agent status from webhook server

---

## Troubleshooting

### Services Won't Start

**Problem:** Webhook server or ngrok fails to start

**Solutions:**

1. **Check if port 5000 is in use:**
   ```powershell
   netstat -ano | findstr :5000
   ```
   If in use, kill the process or change the port

2. **Check ngrok path:**
   - Verify ngrok.exe location
   - Update path in desktop_app.py if needed

3. **Check ngrok auth token:**
   ```powershell
   .\ngrok.exe config add-authtoken YOUR_TOKEN
   ```

### Softphone Won't Register

**Problem:** Softphone shows "Initializing..." forever

**Solutions:**

1. **Check Asterisk is running:**
   ```bash
   wsl sudo systemctl status asterisk
   ```

2. **Check Asterisk is listening:**
   ```bash
   wsl sudo ss -tulpn | grep 5060
   ```

3. **Verify endpoint configuration:**
   ```bash
   wsl sudo asterisk -rx "pjsip show endpoint 101"
   ```

4. **Check WSL2 IP:**
   ```bash
   wsl hostname -I
   ```
   Update domain in desktop_app.py if different

5. **Reload Asterisk:**
   ```bash
   wsl sudo asterisk -rx "pjsip reload"
   ```

### Calls Not Routing to Agents

**Problem:** Calls don't arrive at softphone

**Solutions:**

1. **Verify softphones are registered:**
   - Check status shows "✓ Registered"

2. **Check dialplan:**
   ```bash
   wsl sudo grep -A 10 "exten => 101" /etc/asterisk/extensions.conf
   ```

3. **Watch Asterisk console:**
   ```bash
   wsl sudo asterisk -rvvvvv
   ```
   Make a test call and watch for errors

4. **Verify agent_router.py configuration:**
   ```bash
   grep "agent_extensions" config.ini
   ```

### No Audio During Call

**Problem:** Can't hear or be heard

**Solutions:**

1. **Check microphone permissions:**
   - Windows Settings → Privacy → Microphone
   - Allow desktop apps to access microphone

2. **Check audio devices:**
   ```python
   import pyaudio
   p = pyaudio.PyAudio()
   for i in range(p.get_device_count()):
       print(p.get_device_info_by_index(i))
   ```

3. **Close other apps using microphone:**
   - Zoom, Teams, Discord, etc.

4. **Test audio device:**
   - Windows Sound Settings
   - Test microphone and speakers

### Twilio Errors

**Problem:** Calls fail with Twilio errors

**Solutions:**

1. **Verify Twilio credentials:**
   - Check Account SID and Auth Token
   - Test with Twilio Console

2. **Check phone number:**
   - Must be in E.164 format (+1XXXXXXXXXX)
   - Verify number is active in Twilio

3. **Check webhook URL:**
   - Must be publicly accessible
   - Test with: `curl https://your-ngrok-url.ngrok-free.dev/status`

4. **Check Twilio account balance:**
   - Ensure you have credits

### Ngrok Tunnel Issues

**Problem:** Ngrok tunnel disconnects or fails

**Solutions:**

1. **Check ngrok account:**
   - Free accounts have session limits
   - Upgrade to paid plan for stability

2. **Restart ngrok:**
   - Stop services
   - Start services again

3. **Use alternative tunneling:**
   - Tailscale (more stable)
   - Cloudflare Tunnel
   - Direct public IP (if available)

---

## Advanced Features

### Edge Case Handling

The system automatically handles:

- **Both agents busy:** Pauses dialing until one becomes available
- **Agent doesn't answer:** Marks agent as unavailable, tries next agent
- **Call fails:** Logs error and continues to next contact
- **Network issues:** Retries with exponential backoff

See `EDGE_CASE_HANDLING.md` for details.

### Custom Dialplan

Edit `/etc/asterisk/extensions.conf` in WSL2 to customize call routing:

```bash
wsl sudo nano /etc/asterisk/extensions.conf
```

### Multiple Campaigns

Run multiple campaigns by:

1. Creating separate contact CSV files
2. Loading different CSV for each campaign
3. Tracking results separately

### Call Recording

Enable call recording in Asterisk:

```bash
# Edit dialplan
wsl sudo nano /etc/asterisk/extensions.conf

# Add MixMonitor to dialplan
exten => 101,1,Answer()
same => n,MixMonitor(/var/spool/asterisk/monitor/${UNIQUEID}.wav)
same => n,Dial(PJSIP/101,20)
```

### Analytics

Export call results to CSV and analyze:

1. Go to Call Results tab
2. Click "Export to CSV"
3. Open in Excel/Google Sheets
4. Create pivot tables and charts

---

## FAQ

### Q: How many agents can I have?

**A:** Currently configured for 2 agents. You can add more by:
1. Configuring additional endpoints in Asterisk (103, 104, etc.)
2. Adding them to config.ini
3. Updating desktop_app.py to add more softphone launch buttons

### Q: Can agents work remotely?

**A:** The integrated softphone works best on the same machine as Asterisk. For remote agents:
- Use Linphone or another SIP client
- Configure Tailscale for secure remote access
- Or use a VPN

### Q: What's the call capacity?

**A:** Limited by:
- Number of agents (currently 2)
- Twilio account limits
- Asterisk server resources

For higher capacity, scale up Asterisk and add more agents.

### Q: Can I use a different phone provider?

**A:** Yes! The system uses standard SIP. You can replace Twilio with:
- Vonage
- Bandwidth
- Telnyx
- Any SIP trunk provider

Update the dialer.py to use their API instead of Twilio.

### Q: How do I backup my data?

**A:** Backup these files:
- `config.ini` - Configuration
- `contacts.csv` - Contact list
- `call_results.json` - Call results
- `smart_routing.log` - Activity log

### Q: Can I schedule campaigns?

**A:** Not built-in, but you can:
1. Use Windows Task Scheduler
2. Create a script to launch the app and start calling
3. Schedule the script to run at specific times

### Q: What about compliance (TCPA, DNC)?

**A:** You are responsible for compliance:
- Scrub your contact list against DNC registries
- Only call during allowed hours (8am-9pm local time)
- Maintain your own DNC list
- Honor opt-out requests immediately

### Q: Can I customize the voicemail message per contact?

**A:** Not currently, but you can modify `voicemail_drop.py` to:
1. Use text-to-speech (TTS) with contact name
2. Select different voicemail files based on contact attributes

---

## System Files Reference

### Configuration Files

- `config.ini` - Main configuration
- `contacts.csv` - Contact list
- `voicemail.mp3` - Voicemail audio

### Python Scripts

- `desktop_app.py` - Main GUI application
- `softphone.py` - Integrated SIP softphone
- `dialer.py` - Outbound dialing engine
- `agent_router.py` - Agent availability & routing
- `webhook_server.py` - Twilio webhook handler
- `voicemail_drop.py` - Voicemail dropping logic

### Data Files

- `call_results.json` - Call outcome tracking
- `smart_routing.log` - System activity log

### Documentation

- `COMPLETE_SYSTEM_GUIDE.md` - This file
- `INTEGRATED_SOFTPHONE_README.md` - Softphone documentation
- `SOFTPHONE_SETUP.md` - Softphone setup guide
- `QUICK_START_SOFTPHONE.md` - Quick start guide
- `EDGE_CASE_HANDLING.md` - Edge case documentation
- `LINPHONE_SETUP_GUIDE.md` - Legacy Linphone guide
- `README.md` - Project overview

---

## Quick Reference Commands

### Start System

```powershell
# Launch desktop app
python desktop_app.py

# In app:
# 1. Dashboard → Start Services
# 2. Softphone → Launch Softphone (both agents)
# 3. Contacts → Upload CSV
# 4. Dashboard → Start Calling
```

### Check Asterisk

```bash
# Status
wsl sudo systemctl status asterisk

# Console
wsl sudo asterisk -rvvvvv

# Show endpoints
wsl sudo asterisk -rx "pjsip show endpoints"

# Show transports
wsl sudo asterisk -rx "pjsip show transports"

# Reload config
wsl sudo asterisk -rx "pjsip reload"
```

### Check Services

```powershell
# Check webhook server
curl http://localhost:5000/status

# Check ngrok tunnel
curl http://localhost:4040/api/tunnels

# Check port 5000
netstat -ano | findstr :5000
```

### Logs

```powershell
# System log
type smart_routing.log

# Asterisk log
wsl sudo tail -f /var/log/asterisk/full

# Webhook server log (in Activity Log)
```

---

## Support & Resources

### Documentation

- **This Guide:** Complete system documentation
- **Softphone Guide:** `INTEGRATED_SOFTPHONE_README.md`
- **Quick Start:** `QUICK_START_SOFTPHONE.md`
- **Troubleshooting:** See Troubleshooting section above

### External Resources

- **Asterisk Documentation:** https://wiki.asterisk.org/
- **Twilio Documentation:** https://www.twilio.com/docs
- **Ngrok Documentation:** https://ngrok.com/docs
- **PyAudio Documentation:** https://people.csail.mit.edu/hubert/pyaudio/

### Getting Help

1. Check the Activity Log in the desktop app
2. Check Asterisk console: `wsl sudo asterisk -rvvvvv`
3. Review this guide's Troubleshooting section
4. Check the specific component documentation

---

## Summary

You now have a **complete outbound calling system** with:

✅ **Automated dialing** - Calls contacts from CSV  
✅ **Intelligent routing** - Routes to available agents  
✅ **Integrated softphone** - No external SIP client needed  
✅ **Voicemail dropping** - Leaves messages automatically  
✅ **Call tracking** - Records all outcomes  
✅ **Easy management** - Desktop GUI for everything  

**Start using it:**

1. Install PyAudio: `pip install pyaudio`
2. Launch app: `python desktop_app.py`
3. Start services
4. Launch softphones
5. Upload contacts
6. Start calling!

**That's it! You're ready to go!** 🚀

---

*Last Updated: 2026-05-07*
