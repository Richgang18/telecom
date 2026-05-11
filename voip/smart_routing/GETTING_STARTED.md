# 🚀 Getting Started - Smart Outbound Dialer

## Quick Start (3 Steps)

### 1. Run the Launcher

**Double-click the desktop shortcut:**
```
Smart Dialer (on your desktop)
```

**Or run the batch file:**
```
Launch_Dialer.bat
```

This automatically starts:
- ✅ WSL2 and Asterisk
- ✅ Webhook Server
- ✅ Ngrok Tunnel
- ✅ Desktop Application

### 2. Configure Mobile Agent

In the Desktop App:

1. Go to **Settings** tab
2. Enter your **Mobile Number**: `+14145551234`
3. Set **Agent Mode**: `mobile`
4. Enable **AMD** (Answering Machine Detection)
5. Click **Save Settings**

### 3. Start Calling

1. Go to **Contacts** tab → Upload CSV
2. Go to **Dashboard** tab → Click "Start Calling"
3. **Answer your phone** when it rings!

---

## 📱 Mobile Agent Mode (NEW!)

### What Is It?

Instead of using a softphone on your computer, the system **calls your cellphone directly** when a lead answers. This is the same workflow used by VICIdial and professional call centers.

### How It Works

```
Lead Answers → System Calls Your Mobile → You Answer → Calls Bridged
```

### Benefits

✅ **No softphone needed** - Use your regular phone  
✅ **Work from anywhere** - Answer calls on the go  
✅ **Professional workflow** - VICIdial-style bridging  
✅ **AMD included** - Only human-answered calls forwarded  
✅ **Easy setup** - Just enter your mobile number  

### Configuration

**config.ini:**
```ini
[agents]
agent_mode = mobile
agent_mobile_numbers = +14145551234
agent_timeout = 20
enable_amd = true
```

**See [MOBILE_AGENT_GUIDE.md](MOBILE_AGENT_GUIDE.md) for complete details.**

---

## 🎯 System Components

### Unified Launcher

**Launch_Dialer.bat** - One script that starts everything:

1. **WSL2 + Asterisk** - Starts automatically in background
2. **Webhook Server** - Handles Twilio callbacks
3. **Ngrok Tunnel** - Exposes webhook to internet
4. **Desktop App** - Main GUI interface

**No more running multiple scripts!** ✅

### Desktop Application

**Tabs:**
- **Dashboard** - Start/stop calling, view statistics
- **Softphone** - Launch softphones (if using softphone mode)
- **Contacts** - Upload and manage contact lists
- **Call Results** - View outcomes, export to CSV
- **Settings** - Configure Twilio, mobile number, etc.
- **Agents** - View agent status

---

## ⚙️ Configuration

### Twilio Settings

```ini
[twilio]
account_sid = ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx
auth_token = your_auth_token_here
from_number = +17868339866
webhook_base_url = https://your-ngrok-url.ngrok-free.dev
```

### Agent Settings (Mobile Mode)

```ini
[agents]
agent_mode = mobile
agent_mobile_numbers = +14145551234,+14145555678
agent_names = Agent 1,Agent 2
agent_timeout = 20
enable_amd = true
amd_timeout = 30
```

### Agent Settings (Softphone Mode)

```ini
[agents]
agent_mode = softphone
agent_extensions = 101,102
agent_names = Agent 1,Agent 2
agent_timeout = 20
```

---

## 📋 Contact List Format

**CSV Format:**
```csv
Firstname,Lastname,Dob,Phone,Address1,Address2,City,Zip
John,Smith,1980-01-15,+14145551001,123 Main St,,Milwaukee,53202
Jane,Doe,1985-05-20,+14145551002,456 Oak Ave,,Madison,53703
```

**Required:** `Phone` (E.164 format: +1XXXXXXXXXX)

---

## 🔧 Troubleshooting

### Launcher Issues

**Problem:** "WSL2 is not installed"

**Solution:**
```powershell
# Install WSL2
wsl --install
```

**Problem:** "Asterisk failed to start"

**Solution:**
```bash
# In WSL2
sudo systemctl start asterisk
sudo systemctl status asterisk
```

### Mobile Agent Issues

**Problem:** "Phone never rings"

**Solutions:**
1. Check mobile number format: `+1XXXXXXXXXX`
2. Check AMD settings (may be flagging as machine)
3. Check Twilio console for errors

**Problem:** "No audio during call"

**Solutions:**
1. Check mobile signal strength
2. Enable WiFi calling
3. Check Twilio trunk configuration

### Webhook Issues

**Problem:** "Ngrok not found"

**Solution:**
```
Download ngrok from: https://ngrok.com/download
Place in: C:\Users\Admin\Downloads\
```

**Problem:** "Webhook URL not updating"

**Solution:**
1. Click "Auto-detect Ngrok URL" in Settings
2. Or manually copy from ngrok window
3. Save settings

---

## 📚 Documentation

### Quick Guides
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - This file
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Command reference
- **[MOBILE_AGENT_GUIDE.md](MOBILE_AGENT_GUIDE.md)** - Mobile agent details

### Complete Guides
- **[COMPLETE_SYSTEM_GUIDE.md](COMPLETE_SYSTEM_GUIDE.md)** - Full documentation
- **[SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)** - Technical details
- **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** - All docs index

### Legacy (Not Recommended)
- **[LINPHONE_SETUP_GUIDE.md](LINPHONE_SETUP_GUIDE.md)** - Old softphone setup
- **[INTEGRATED_SOFTPHONE_README.md](INTEGRATED_SOFTPHONE_README.md)** - Old softphone docs

**Use mobile agent mode instead!** ✅

---

## 🎯 Workflow

### Daily Usage

**Morning:**
1. Double-click "Smart Dialer" shortcut
2. Wait for system to start (30 seconds)
3. Upload today's contact list
4. Click "Start Calling"

**During Campaign:**
1. Answer your phone when it rings
2. Talk to leads
3. Hang up when done
4. System automatically dials next lead

**Evening:**
1. Click "Stop Calling"
2. Export call results to CSV
3. Close desktop app
4. System shuts down automatically

---

## 💡 Tips

### For Best Results

1. **Use WiFi Calling** - Better quality, more reliable
2. **Quiet Environment** - Professional impression
3. **Headset** - Hands-free, better audio
4. **Dedicated Line** - Separate business number
5. **Answer Quickly** - Within 2-3 rings
6. **Have Script Ready** - Know what to say

### Cost Optimization

**Mobile mode costs 2x softphone mode:**
- Softphone: $0.013/min
- Mobile: $0.026/min

**But mobile mode is worth it for:**
- Flexibility (work anywhere)
- No computer needed
- Professional workflow

---

## 🆘 Getting Help

### Step 1: Check Logs

1. **Activity Log** - Desktop App → Dashboard tab
2. **System Log** - `smart_routing.log`
3. **Asterisk Log** - `wsl sudo tail -f /var/log/asterisk/full`

### Step 2: Check Documentation

1. **Quick issue?** → [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
2. **Mobile agent?** → [MOBILE_AGENT_GUIDE.md](MOBILE_AGENT_GUIDE.md)
3. **General issue?** → [COMPLETE_SYSTEM_GUIDE.md](COMPLETE_SYSTEM_GUIDE.md)

### Step 3: Common Solutions

| Issue | Solution |
|-------|----------|
| Phone doesn't ring | Check mobile number format |
| No audio | Check signal strength, enable WiFi calling |
| Services won't start | Run `Launch_Dialer.bat` as administrator |
| Asterisk not running | `wsl sudo systemctl start asterisk` |

---

## ✅ Checklist

Before starting your first campaign:

- [ ] Ran `Launch_Dialer.bat` successfully
- [ ] Configured Twilio credentials
- [ ] Entered mobile number (E.164 format)
- [ ] Set agent mode to "mobile"
- [ ] Enabled AMD
- [ ] Uploaded contact list
- [ ] Recorded voicemail message
- [ ] Tested with 1-2 contacts first

---

## 🎉 You're Ready!

**Everything is set up and ready to go!**

1. Double-click "Smart Dialer" on desktop
2. Upload contacts
3. Start calling
4. Answer your phone
5. Talk to leads!

**That's it!** 🚀

---

**For detailed information, see:**
- [MOBILE_AGENT_GUIDE.md](MOBILE_AGENT_GUIDE.md) - Mobile agent complete guide
- [COMPLETE_SYSTEM_GUIDE.md](COMPLETE_SYSTEM_GUIDE.md) - Full system documentation
