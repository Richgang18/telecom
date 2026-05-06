# 🌐 Ngrok Setup Guide

## Quick Fix (Easiest!)

You have ngrok.exe in your Downloads folder. Just run this:

```
Double-click: setup_ngrok.bat
```

This will copy ngrok.exe to the app folder, and the app will find it automatically!

---

## What Happened

When you clicked "Start Services", the app looked for ngrok but couldn't find it because:
- Ngrok is in Downloads folder
- Not in system PATH
- App couldn't locate it automatically

---

## Solution Options

### Option 1: Copy to App Folder (EASIEST)

**Steps:**
1. Double-click: `setup_ngrok.bat`
2. It copies ngrok.exe from Downloads to app folder
3. Done! App will now find it

**Result:**
- Ngrok located at: `D:\telecom\voip\smart_routing\ngrok.exe`
- App automatically detects it
- No PATH configuration needed

### Option 2: Manual Copy

**Steps:**
1. Open Downloads folder: `C:\Users\Admin\Downloads`
2. Find `ngrok.exe`
3. Copy it
4. Paste into: `D:\telecom\voip\smart_routing\`
5. Done!

### Option 3: Add to System PATH

**Steps:**
1. Double-click: `install_ngrok.bat` (requires admin)
2. It copies ngrok to `C:\ngrok\`
3. Adds to system PATH
4. Restart the app

### Option 4: Browse in App

**Steps:**
1. In the app, click "Start Services"
2. When prompted "Ngrok Not Found", click YES
3. Browse to: `C:\Users\Admin\Downloads\ngrok.exe`
4. Select it
5. Done!

---

## Verification

After setup, verify ngrok is working:

1. Open the desktop app
2. Click "Start Services"
3. Check Activity Log - should say "Ngrok tunnel started"
4. Go to Settings tab
5. Click "Auto-detect Ngrok URL"
6. Should show a URL like: `https://abc123.ngrok-free.app`

---

## Troubleshooting

### "Ngrok Not Found" Still Appears

**Solution:**
1. Check if ngrok.exe exists in app folder:
   ```
   D:\telecom\voip\smart_routing\ngrok.exe
   ```
2. If not, run `setup_ngrok.bat` again
3. Restart the desktop app

### Ngrok Starts But No URL Detected

**Solution:**
1. Wait 5-10 seconds after starting services
2. Click "Auto-detect Ngrok URL" again
3. Check Activity Log for errors

### "Access Denied" Error

**Solution:**
1. Close the desktop app
2. Right-click `setup_ngrok.bat`
3. Select "Run as administrator"
4. Restart the app

---

## Alternative: Skip Ngrok

If you don't want to use ngrok, you can:

1. **Configure Port Forwarding** on your router:
   - Forward port 5000 from public IP to your machine
   - Use webhook URL: `http://YOUR_PUBLIC_IP:5000`

2. **Use Tailscale** (already installed):
   - Configure Tailscale Funnel
   - Use Tailscale URL as webhook

3. **Use Another Tunnel Service**:
   - LocalTunnel
   - Serveo
   - Cloudflare Tunnel

---

## What Ngrok Does

Ngrok creates a public URL that forwards to your local webhook server:

```
Internet (Twilio)
    ↓
https://abc123.ngrok-free.app (public)
    ↓
localhost:5000 (your webhook server)
    ↓
Your Asterisk PBX
```

Without ngrok, Twilio can't reach your webhook server to route calls.

---

## Recommended Setup

**For Testing:**
- Use ngrok (easiest)
- Run `setup_ngrok.bat`
- Free tier is fine

**For Production:**
- Configure proper port forwarding
- Use your domain: `https://pbx.vouchersdept.com:5000`
- Or use Tailscale Funnel

---

## Quick Commands

**Copy ngrok to app folder:**
```batch
setup_ngrok.bat
```

**Install ngrok system-wide:**
```batch
install_ngrok.bat
```

**Check if ngrok is working:**
```batch
ngrok version
```

**Start ngrok manually:**
```batch
ngrok http 5000
```

---

## Summary

**Problem:** Ngrok in Downloads, app can't find it  
**Solution:** Run `setup_ngrok.bat` to copy it to app folder  
**Result:** App finds ngrok automatically  
**Time:** 10 seconds  

---

**Just run setup_ngrok.bat and you're done! 🚀**
