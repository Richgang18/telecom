# 🔄 System Reinstallation Guide

## Complete Fresh Installation Instructions

This guide will help you reinstall the Smart Outbound Dialer system from scratch.

---

## ✅ Current System Status

Based on your latest test (May 6, 2026 15:30):
- ✅ **Asterisk**: Running in WSL2
- ✅ **Webhook Server**: Running on port 5000
- ✅ **Ngrok**: Active at `https://deranged-cupped-bulk.ngrok-free.dev`
- ✅ **Twilio**: Successfully authenticated and making calls
- ✅ **Test Calls**: 3/3 contacts dialed successfully

**Your system is FULLY OPERATIONAL!** You may not need to reinstall.

---

## 🚨 When to Reinstall

Only reinstall if you experience:
- Corrupted configuration files
- Missing Python dependencies
- Need to move to a different machine
- Complete system reset required

---

## 📋 Prerequisites

### Windows Requirements
- Windows 10 or 11
- WSL2 Ubuntu 24.04 installed
- Python 3.10+ on Windows
- Python 3.10+ in WSL2

### Accounts Needed
- Twilio account with phone number
- Ngrok account (free tier works)
- Domain name (optional, for production)

---

## 🔧 Step-by-Step Reinstallation

### Step 1: Clean Up Old Installation (Optional)

If you want a completely fresh start:

```bash
# In Windows PowerShell
cd C:\Users\Admin\SPdevTech\telecom\voip\smart_routing

# Backup important files
mkdir backup
copy config.ini backup\
copy contacts.csv backup\
copy call_results.json backup\

# Remove old files (optional - only if you want fresh start)
del config.ini
del contacts.csv
del call_results.json
del smart_routing.log
```

### Step 2: Install Python Dependencies

**On Windows:**
```powershell
cd C:\Users\Admin\SPdevTech\telecom\voip\smart_routing
pip install -r requirements.txt
```

**In WSL2:**
```bash
cd /mnt/c/Users/Admin/SPdevTech/telecom/voip
pip3 install -r requirements.txt
```

### Step 3: Install and Configure Ngrok

**Download Ngrok:**
1. Go to https://ngrok.com/download
2. Download Windows version
3. Extract to: `C:\Users\Admin\Downloads\ngrok-v3-stable-windows-amd64\`

**Configure Authtoken:**
```powershell
cd C:\Users\Admin\Downloads\ngrok-v3-stable-windows-amd64
.\ngrok.exe config add-authtoken YOUR_NEW_TOKEN
```

⚠️ **SECURITY WARNING**: Your current token `3DLbHH7vD2q34hbmwpPPBBcELEb_44WsfZPoRUEEBZd9vKV1p` was exposed publicly. Get a new one from https://dashboard.ngrok.com/get-started/your-authtoken

### Step 4: Deploy Asterisk (If Not Already Running)

```bash
# In WSL2
cd /mnt/c/Users/Admin/SPdevTech/telecom/voip

# Set environment variables
export DOMAIN="pbx.vouchersdept.com"
export PUBLIC_IP="YOUR_PUBLIC_IP"
export TWILIO_TRUNK="dataism-voip.pstn.twilio.com"

# Run deployment
sudo -E python3 deploy.py
```

**Verify Asterisk:**
```bash
sudo systemctl status asterisk
asterisk -rx "pjsip show endpoints"
```

### Step 5: Configure Desktop Application

**Launch the app:**
```powershell
cd C:\Users\Admin\SPdevTech\telecom\voip\smart_routing
.\launch_app.bat
```

**Configure Settings (⚙ Settings Tab):**

1. **Twilio Configuration:**
   - Account SID: `ACcf15065d54bfedd91baec3cc1283561c`
   - Auth Token: Get NEW token from https://console.twilio.com
   - From Number: `+17868339866`
   - Webhook URL: (will auto-detect after starting ngrok)

2. **Click "💾 Save Settings"**

### Step 6: Start Services

1. Go to **📊 Dashboard** tab
2. Click **🚀 Start Services**
3. Wait 5 seconds for services to initialize
4. Go to **⚙ Settings** tab
5. Click **🔄 Auto-detect Ngrok URL**
6. Verify URL is detected (should be like `https://xxxxx.ngrok-free.dev`)
7. Click **💾 Save Settings**

### Step 7: Configure Linphone Agents

**Install Linphone on 2 devices:**
- Download from: https://www.linphone.org/

**Agent 1 Configuration:**
```
Username: 101
Password: ChangeMe101!
Domain: pbx.vouchersdept.com
Port: 5061
Transport: TLS
```

**Agent 2 Configuration:**
```
Username: 102
Password: ChangeMe102!
Domain: pbx.vouchersdept.com
Port: 5061
Transport: TLS
```

**Verify Registration:**
```bash
# In WSL2
asterisk -rx "pjsip show endpoints"
```

You should see:
```
101/101    Not in use    0 of inf
102/102    Not in use    0 of inf
```

### Step 8: Upload Contacts

1. Click **📋 Contacts** tab
2. Click **📁 Browse CSV File**
3. Select your CSV with columns:
   - Firstname, Lastname, Phone, City, Zip, etc.
4. Verify contacts loaded successfully

### Step 9: Test the System

**Small Test:**
1. Create a test CSV with 2-3 contacts
2. Upload to the app
3. Click **▶ Start Calling**
4. Monitor the **Activity Log**
5. Check **📞 Call Results** tab

**Verify:**
- Calls are initiated (check Activity Log)
- Agents receive calls in Linphone
- Voicemail drops work
- Results are recorded

---

## 🔍 Verification Checklist

After reinstallation, verify each component:

### ✅ Asterisk
```bash
# In WSL2
sudo systemctl status asterisk
asterisk -rx "core show version"
asterisk -rx "pjsip show endpoints"
```

Expected:
- Service: active (running)
- Version: Asterisk 20.6.0
- Endpoints: 101, 102 registered

### ✅ Webhook Server
```powershell
# In Windows PowerShell
curl http://localhost:5000/status
```

Expected:
```json
{
  "status": "ok",
  "agents": [...]
}
```

### ✅ Ngrok
```powershell
curl http://localhost:4040/api/tunnels
```

Expected:
```json
{
  "tunnels": [
    {
      "public_url": "https://xxxxx.ngrok-free.dev",
      ...
    }
  ]
}
```

### ✅ Twilio Authentication
```powershell
$accountSid = "ACcf15065d54bfedd91baec3cc1283561c"
$authToken = "YOUR_NEW_AUTH_TOKEN"
$base64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${accountSid}:${authToken}"))
$headers = @{Authorization = "Basic $base64"}
Invoke-RestMethod -Uri "https://api.twilio.com/2010-04-01/Accounts/$accountSid.json" -Headers $headers
```

Expected: Account details (not 401 error)

### ✅ Desktop App
- Launch app successfully
- All status indicators green ●
- Can upload contacts
- Can start/stop services
- Can initiate calls

---

## 🐛 Common Issues After Reinstall

### Issue 1: "Module not found" errors

**Solution:**
```powershell
# On Windows
pip install flask twilio requests configparser

# In WSL2
pip3 install flask twilio requests configparser
```

### Issue 2: Ngrok not found

**Solution:**
```powershell
# Verify ngrok location
dir C:\Users\Admin\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe

# If not found, download again from https://ngrok.com/download
```

### Issue 3: Asterisk not starting

**Solution:**
```bash
# In WSL2
sudo systemctl stop asterisk
sudo systemctl start asterisk
sudo systemctl status asterisk

# Check logs
sudo tail -f /var/log/asterisk/messages
```

### Issue 4: Webhook server fails to start

**Solution:**
```powershell
# Check if port 5000 is in use
netstat -ano | findstr :5000

# Kill process using port 5000
taskkill /PID <PID> /F

# Restart webhook server from app
```

### Issue 5: Agents not registering

**Solution:**
1. Verify domain resolves: `ping pbx.vouchersdept.com`
2. Check firewall allows port 5061
3. Verify TLS certificate is valid
4. Check Linphone configuration exactly matches
5. Check Asterisk logs: `sudo tail -f /var/log/asterisk/messages`

### Issue 6: Calls not connecting

**Solution:**
1. Verify webhook URL is publicly accessible
2. Test: `curl https://your-ngrok-url.ngrok-free.dev/status`
3. Check Twilio console for webhook errors
4. Verify agents are registered in Linphone
5. Check Activity Log in desktop app

---

## 🔐 Security: Reset Exposed Credentials

⚠️ **CRITICAL**: Your credentials were exposed publicly. Reset them immediately:

### Reset Ngrok Authtoken
1. Go to https://dashboard.ngrok.com/get-started/your-authtoken
2. Click "Reset Authtoken"
3. Copy new token
4. Run: `ngrok config add-authtoken NEW_TOKEN`

### Reset Twilio Auth Token
1. Go to https://console.twilio.com
2. Navigate to Account > API Keys & Tokens
3. Click "Create new Auth Token" or reset existing
4. Update in desktop app Settings tab
5. Save settings

### Update Config File
```ini
# voip/smart_routing/config.ini
[twilio]
account_sid = ACcf15065d54bfedd91baec3cc1283561c
auth_token = YOUR_NEW_AUTH_TOKEN_HERE
from_number = +17868339866
webhook_base_url = https://your-new-ngrok-url.ngrok-free.dev
```

---

## 📁 File Structure Reference

After reinstallation, you should have:

```
C:\Users\Admin\SPdevTech\telecom\voip\smart_routing\
├── desktop_app.py              ← Main desktop application
├── launch_app.bat              ← Windows launcher
├── launch_app.sh               ← Linux launcher
├── config.ini                  ← Configuration (auto-created)
├── contacts.csv                ← Contact list (auto-created)
├── call_results.json           ← Call results database
├── smart_routing.log           ← Activity log
├── voicemail.mp3               ← Your voicemail recording
├── dialer.py                   ← Background dialer script
├── webhook_server.py           ← Webhook server
├── agent_router.py             ← Agent routing logic
├── voicemail_drop.py           ← Voicemail drop logic
├── requirements.txt            ← Python dependencies
├── DESKTOP_APP_GUIDE.md        ← Full user guide
├── QUICK_START.md              ← Quick start guide
└── REINSTALL_GUIDE.md          ← This file
```

---

## 🎯 Post-Installation Testing

### Test 1: Service Status
```powershell
# Launch app
.\launch_app.bat

# Check Dashboard tab
# All indicators should be green ●
```

### Test 2: Small Call Campaign
```powershell
# Create test_contacts.csv with 2 contacts
# Upload via Contacts tab
# Click "Start Calling"
# Monitor Activity Log
```

### Test 3: Agent Connection
```powershell
# Have agents log into Linphone
# Initiate test call
# Verify agent receives call
# Verify voicemail drops work
```

### Test 4: Results Export
```powershell
# After test calls complete
# Go to Call Results tab
# Click "Export to CSV"
# Verify file contains call data
```

---

## 📞 Support Resources

**Documentation:**
- Full Guide: `DESKTOP_APP_GUIDE.md`
- Quick Start: `QUICK_START.md`
- This Guide: `REINSTALL_GUIDE.md`

**Logs to Check:**
- Desktop App: Activity Log in Dashboard tab
- System Log: `smart_routing.log`
- Asterisk: `/var/log/asterisk/messages` (in WSL2)
- Webhook: Console output when running

**Useful Commands:**
```bash
# Check Asterisk status
sudo systemctl status asterisk

# View Asterisk logs
sudo tail -f /var/log/asterisk/messages

# Check registered endpoints
asterisk -rx "pjsip show endpoints"

# Check active calls
asterisk -rx "core show channels"

# Test webhook
curl http://localhost:5000/status

# Test ngrok
curl http://localhost:4040/api/tunnels
```

---

## ✅ Installation Complete!

After following this guide, your system should be:
- ✅ Fully installed and configured
- ✅ All services running
- ✅ Agents registered
- ✅ Ready to make calls

**Next Steps:**
1. Upload your real contact list
2. Brief your agents on the system
3. Start your first campaign
4. Monitor results in real-time
5. Export results for analysis

---

## 🎉 You're Ready to Go!

Your Smart Outbound Dialer is now fully operational. Start calling and watch your productivity soar!

**Questions?** Check the Activity Log in the Dashboard tab or review the logs mentioned above.

---

**Version:** 1.0.0  
**Last Updated:** May 7, 2026  
**Platform:** Windows 10/11 with WSL2 Ubuntu 24.04
