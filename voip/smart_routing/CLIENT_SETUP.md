# Smart Outbound Dialer - Client Setup Guide

## What You Need

- Windows 10/11 (64-bit)
- Internet connection
- Twilio account with a phone number
- Your mobile phone number (for receiving calls)

---

## Step 1: First-Time Installation

**Right-click `INSTALL_ON_CLIENT.bat` → Run as Administrator**

This will automatically:
- Install Python (if not installed)
- Install Node.js (if not installed)
- Install all required packages
- Set up WSL2 and Asterisk
- Create a desktop shortcut

> If it asks you to restart, restart and run it again.

---

## Step 2: Launch the System

**Double-click "Smart Dialer" on your desktop**

Or run `Launch_Dialer.bat`

The browser will open automatically at `http://localhost:3000`

---

## Step 3: Configure Settings

In the browser, go to **Settings** tab:

1. **WSL2 Password** — Enter your WSL2 user password (set during Ubuntu install)
2. **Twilio Account SID** — From https://console.twilio.com
3. **Twilio Auth Token** — From https://console.twilio.com
4. **From Number** — Your Twilio phone number (e.g. +17868339866)
5. **Agent Mode** — Select "Mobile"
6. **Mobile Number** — Your cellphone number (e.g. +14145551234)
7. Click **Save Settings**

---

## Step 4: Start a Campaign

1. Go to **Contacts** tab → drag & drop your CSV file
2. Go to **Dashboard** tab → click **Start Services** (starts Ngrok)
3. Click **Detect Ngrok** to auto-fill the webhook URL
4. Click **Start Campaign**
5. **Answer your phone** when it rings — you'll be connected to leads!

---

## How Calls Work

```
System dials lead → Lead answers → Your mobile rings → You answer → Calls bridged
```

Your personal number is never shown to leads. They see your Twilio number.

---

## Troubleshooting

### Browser doesn't open
- Open Chrome/Edge manually
- Go to: http://localhost:3000

### "API not connected" in top bar
- Make sure `Launch_Dialer.bat` is running
- Check `api.log` in the Smart Dialer folder

### Asterisk won't start
- Open WSL2 terminal
- Run: `sudo systemctl start asterisk`
- Enter your WSL2 password when prompted

### Phone doesn't ring
- Check mobile number format: +1XXXXXXXXXX (no spaces or dashes)
- Check Twilio account has credits
- Make sure Ngrok is running (click "Detect Ngrok" in dashboard)

---

## Files in This Folder

| File | Purpose |
|------|---------|
| `Launch_Dialer.bat` | Start the system (use this daily) |
| `INSTALL_ON_CLIENT.bat` | First-time setup only |
| `config.ini` | All settings (also editable in UI) |
| `contacts.csv` | Your contact list |
| `voicemail.mp3` | Pre-recorded voicemail message |
| `api.log` | Backend error log |
| `ui.log` | Frontend error log |

---

## Daily Usage

1. Double-click **Smart Dialer** on desktop
2. Upload contacts
3. Click **Start Campaign**
4. Answer your phone!
