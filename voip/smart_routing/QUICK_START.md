# 🚀 Quick Start Guide - Desktop App

## 5-Minute Setup

### 1. Launch the App

**Windows:**
```
Double-click: launch_app.bat
```

**WSL2:**
```bash
cd /mnt/c/Users/Admin/SPdevTech/telecom/voip/smart_routing
python3 desktop_app.py
```

### 2. Configure Twilio (One-Time)

1. Click **⚙ Settings** tab
2. Fill in (already done for you):
   - Account SID: `ACcf15065d54bfedd91baec3cc1283561c`
   - Auth Token: `34677dad892d854fcf70b7b2a4003faf`
   - From Number: `+17868339866`
3. Click **💾 Save Settings**

### 3. Start Services

1. Go to **📊 Dashboard** tab
2. Click **🚀 Start Services**
3. Wait 5 seconds
4. Go to **⚙ Settings** tab
5. Click **🔄 Auto-detect Ngrok URL**
6. Click **💾 Save Settings**

### 4. Upload Contacts

1. Click **📋 Contacts** tab
2. Click **📁 Browse CSV File**
3. Select your CSV with columns:
   - Firstname, Lastname, Phone, City, Zip, etc.
4. Done! Contacts loaded automatically

### 5. Setup Agents (One-Time)

1. Install Linphone on 2 computers: https://www.linphone.org/
2. Configure each:

**Agent 1:**
- Username: `101`
- Password: `ChangeMe101!`
- Domain: `pbx.vouchersdept.com`
- Port: `5061`
- Transport: `TLS`

**Agent 2:**
- Username: `102`
- Password: `ChangeMe102!`
- Domain: `pbx.vouchersdept.com`
- Port: `5061`
- Transport: `TLS`

### 6. Start Calling!

1. Go to **📊 Dashboard** tab
2. Verify all lights are green ●
3. Click **▶ Start Calling**
4. Watch the magic happen!

### 7. View Results

1. Click **📞 Call Results** tab
2. See who answered, got voicemail, etc.
3. Click **📊 Export to CSV** to save results

---

## Daily Workflow

```
1. Open app (launch_app.bat)
2. Click "Start Services" (if not running)
3. Upload new contacts (if needed)
4. Click "Start Calling"
5. Monitor results
6. Export results when done
```

---

## Troubleshooting

**Services won't start?**
- Check if ports 5000/4040 are free
- Restart the app

**Calls not connecting?**
- Verify agents are logged into Linphone
- Check webhook URL is set (Settings tab)
- Ensure Asterisk is running (green ● on Dashboard)

**CSV upload fails?**
- Ensure CSV has "Phone" column
- Check phone numbers are valid

---

## Need Help?

1. Check **Activity Log** on Dashboard tab
2. Read full guide: `DESKTOP_APP_GUIDE.md`
3. Check `smart_routing.log` file

---

**That's it! You're ready to start calling! 🎉**
