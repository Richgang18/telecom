# 📦 Installation Guide

## Prerequisites

- Windows 10/11 with WSL2 Ubuntu 24.04
- Python 3.8 or higher
- Asterisk already deployed (via deploy.py)
- Twilio account with phone number

## Installation Steps

### 1. Verify Python Installation

```bash
python3 --version
# Should show Python 3.8 or higher
```

If not installed:
```bash
sudo apt update
sudo apt install python3 python3-pip
```

### 2. Install Dependencies

```bash
cd /mnt/c/Users/Admin/SPdevTech/telecom/voip/smart_routing
pip3 install -r requirements.txt --break-system-packages
```

### 3. Verify Voicemail File

Ensure `voicemail.mp3` exists:
```bash
ls -lh voicemail.mp3
```

If missing, record and place your voicemail file here.

### 4. Install Ngrok (Optional but Recommended)

```bash
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update
sudo apt install ngrok
```

Verify:
```bash
ngrok version
```

### 5. Launch Desktop App

**From Windows:**
```
Navigate to: D:\telecom\voip\smart_routing
Double-click: launch_app.bat
```

**From WSL2:**
```bash
cd /mnt/c/Users/Admin/SPdevTech/telecom/voip/smart_routing
python3 desktop_app.py
```

### 6. First-Time Configuration

1. **Settings Tab:**
   - Twilio Account SID: `ACcf15065d54bfedd91baec3cc1283561c`
   - Twilio Auth Token: `34677dad892d854fcf70b7b2a4003faf`
   - From Number: `+17868339866`
   - Click **Save Settings**

2. **Start Services:**
   - Go to Dashboard tab
   - Click **Start Services**
   - Wait 5 seconds
   - Go to Settings tab
   - Click **Auto-detect Ngrok URL**
   - Click **Save Settings**

3. **Upload Contacts:**
   - Go to Contacts tab
   - Click **Browse CSV File**
   - Select your CSV file
   - Verify contacts loaded

4. **Configure Agents:**
   - Install Linphone on 2 devices
   - Configure as shown in Agents tab
   - Verify registration

### 7. Test the System

1. Upload a small test CSV (2-3 contacts)
2. Click **Start Calling**
3. Monitor Activity Log
4. Check Call Results tab
5. Export results to verify

## Verification Checklist

- [ ] Python 3.8+ installed
- [ ] Dependencies installed (twilio, flask)
- [ ] Voicemail.mp3 file exists
- [ ] Ngrok installed (optional)
- [ ] Desktop app launches
- [ ] Settings saved
- [ ] Services start (green indicators)
- [ ] Contacts upload successfully
- [ ] Agents registered in Linphone
- [ ] Test call completes successfully

## Troubleshooting

### App Won't Launch

**Error:** `ModuleNotFoundError: No module named 'tkinter'`

**Solution:**
```bash
sudo apt install python3-tk
```

### Dependencies Won't Install

**Error:** `error: externally-managed-environment`

**Solution:**
```bash
pip3 install -r requirements.txt --break-system-packages
```

### Ngrok Not Found

**Error:** `ngrok: command not found`

**Solution:**
- Follow step 4 above to install ngrok
- OR configure manual port forwarding
- OR use Tailscale/other tunnel

### Services Won't Start

**Error:** Port already in use

**Solution:**
```bash
# Check what's using port 5000
netstat -ano | findstr :5000

# Kill the process or use different port
```

## Uninstallation

To remove the application:

```bash
cd /mnt/c/Users/Admin/SPdevTech/telecom/voip/smart_routing

# Remove Python packages
pip3 uninstall twilio flask -y

# Remove ngrok (optional)
sudo apt remove ngrok -y

# Remove application files (optional)
cd ..
rm -rf smart_routing
```

## Updating

To update the application:

```bash
cd /mnt/c/Users/Admin/SPdevTech/telecom/voip/smart_routing

# Pull latest code (if using git)
git pull

# Update dependencies
pip3 install -r requirements.txt --upgrade --break-system-packages

# Restart app
python3 desktop_app.py
```

## Support

For issues:
1. Check Activity Log in app
2. Review `smart_routing.log`
3. Check `DESKTOP_APP_GUIDE.md`
4. Verify Asterisk: `asterisk -rx "core show version"`

---

**Installation complete! Ready to start calling! 🎉**
