# 📱 Linphone Setup Guide for Agents

## Complete Setup Instructions for PC and Mobile

This guide will help your agents set up Linphone softphone on their devices to receive calls from the outbound dialing system.

---

## 📋 What You'll Need

### Agent 1 Credentials
- **Username:** `101`
- **Password:** `ChangeMe101!`
- **Domain:** `pbx.vouchersdept.com`
- **Port:** `5061`
- **Transport:** `TLS`

### Agent 2 Credentials
- **Username:** `102`
- **Password:** `ChangeMe102!`
- **Domain:** `pbx.vouchersdept.com`
- **Port:** `5061`
- **Transport:** `TLS`

---

## 💻 PC Setup (Windows/Mac/Linux)

### Step 1: Download Linphone

**Windows:**
1. Go to https://www.linphone.org/releases/windows/app/
2. Download the latest version (e.g., `Linphone-5.2.0-win32.exe`)
3. Run the installer
4. Follow the installation wizard
5. Launch Linphone

**Mac:**
1. Go to https://www.linphone.org/releases/macosx/app/
2. Download the latest `.dmg` file
3. Open the `.dmg` and drag Linphone to Applications
4. Launch Linphone from Applications

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install linphone

# Fedora
sudo dnf install linphone

# Or download from: https://www.linphone.org/releases/linux/app/
```

### Step 2: Initial Setup

1. **Launch Linphone**
2. **Skip the welcome wizard** (click "Skip" or "Use SIP Account")
3. You'll see the main Linphone interface

### Step 3: Configure SIP Account

#### For Agent 1:

1. Click the **☰ Menu** (hamburger icon) in the top-left
2. Select **Settings** or **Preferences**
3. Go to **Accounts** or **SIP Accounts**
4. Click **+ Add Account** or **Create**

5. **Fill in the details:**
   ```
   Username:     101
   Password:     ChangeMe101!
   Domain:       pbx.vouchersdept.com
   Display Name: Agent 1 (optional)
   ```

6. Click **Advanced Settings** or **Show Advanced**

7. **Configure Transport:**
   ```
   Transport:    TLS
   Port:         5061
   ```

8. **Optional Settings:**
   ```
   Enable:       ✓ (checked)
   Register:     ✓ (checked)
   ```

9. Click **Save** or **Add**

#### For Agent 2:

Follow the same steps but use:
```
Username:     102
Password:     ChangeMe102!
Domain:       pbx.vouchersdept.com
Display Name: Agent 2 (optional)
Transport:    TLS
Port:         5061
```

### Step 4: Verify Registration

1. Look for a **green indicator** or **"Registered"** status next to your account
2. If you see **red** or **"Not Registered"**:
   - Check your internet connection
   - Verify credentials are correct
   - Check firewall settings (allow port 5061)
   - Contact your system administrator

### Step 5: Test Audio

1. Go to **Settings** → **Audio**
2. Select your **microphone** and **speakers/headset**
3. Click **Test** to verify audio works
4. Adjust volume levels as needed

### Step 6: Ready to Receive Calls!

✅ You're all set! When the dialer system calls a contact:
1. Your Linphone will ring
2. Click **Answer** to connect
3. Talk to the customer
4. Click **Hang Up** when done

---

## 📱 Mobile Setup (Android/iOS)

### Step 1: Download Linphone App

**Android:**
1. Open **Google Play Store**
2. Search for **"Linphone"**
3. Install **Linphone - open source SIP client**
4. Open the app

**iOS:**
1. Open **App Store**
2. Search for **"Linphone"**
3. Install **Linphone**
4. Open the app

### Step 2: Initial Setup

1. **Launch Linphone**
2. Tap **"Use SIP Account"** or **"Skip"** the wizard
3. You'll see the main dialer screen

### Step 3: Configure SIP Account

#### For Agent 1:

1. Tap the **☰ Menu** icon (three lines) in the top-left
2. Tap **Settings** or **Preferences**
3. Tap **Accounts** or **SIP Accounts**
4. Tap **+ Add Account** or the **+** button

5. **Select "Use SIP Account"** or **"Advanced"**

6. **Fill in the details:**
   ```
   Username:     101
   Password:     ChangeMe101!
   Domain:       pbx.vouchersdept.com
   Display Name: Agent 1 (optional)
   ```

7. **Tap "Advanced" or "Transport Settings":**
   ```
   Transport:    TLS
   Port:         5061
   ```

8. **Enable the account:**
   - Toggle **"Enable"** to ON
   - Toggle **"Register"** to ON (if available)

9. Tap **Save** or **Done**

#### For Agent 2:

Follow the same steps but use:
```
Username:     102
Password:     ChangeMe102!
Domain:       pbx.vouchersdept.com
Display Name: Agent 2 (optional)
Transport:    TLS
Port:         5061
```

### Step 4: Verify Registration

1. Go back to **Accounts** screen
2. Look for **green dot** or **"Registered"** status
3. If **red** or **"Not Registered"**:
   - Check mobile data or WiFi connection
   - Verify credentials
   - Try toggling airplane mode on/off
   - Restart the app

### Step 5: Configure Permissions

**Android:**
1. Go to phone **Settings** → **Apps** → **Linphone**
2. Enable permissions:
   - ✓ Microphone
   - ✓ Phone
   - ✓ Notifications
   - ✓ Run in background

**iOS:**
1. Go to **Settings** → **Linphone**
2. Enable permissions:
   - ✓ Microphone
   - ✓ Notifications
   - ✓ Background App Refresh

### Step 6: Test Audio

1. In Linphone, go to **Settings** → **Audio**
2. Test your microphone and speaker
3. Adjust volume if needed
4. Use headphones/earbuds for better quality

### Step 7: Keep App Running

**Important:** For incoming calls to work:

**Android:**
- Keep Linphone running in the background
- Disable battery optimization for Linphone:
  - Settings → Battery → Battery Optimization
  - Find Linphone → Select "Don't optimize"

**iOS:**
- Enable Background App Refresh
- Keep notifications enabled
- App will wake up for incoming calls

### Step 8: Ready to Receive Calls!

✅ You're all set! When a call comes in:
1. You'll get a notification
2. Swipe to answer
3. Talk to the customer
4. Tap hang up when done

---

## 🔧 Detailed Configuration Screenshots

### Windows Configuration

```
┌─────────────────────────────────────────┐
│  Linphone - Account Settings            │
├─────────────────────────────────────────┤
│                                         │
│  Username:     [101                  ]  │
│  Password:     [••••••••••••         ]  │
│  Domain:       [pbx.vouchersdept.com ]  │
│  Display Name: [Agent 1              ]  │
│                                         │
│  ▼ Advanced Settings                    │
│                                         │
│  Transport:    [TLS              ▼]     │
│  Port:         [5061                ]   │
│  Proxy:        [                    ]   │
│                                         │
│  ☑ Enable this account                  │
│  ☑ Register on startup                  │
│                                         │
│         [Cancel]  [Save Account]        │
│                                         │
└─────────────────────────────────────────┘
```

### Mobile Configuration

```
┌─────────────────────────────┐
│  ☰  Linphone                │
├─────────────────────────────┤
│                             │
│  SIP Account Setup          │
│                             │
│  Username                   │
│  ┌─────────────────────┐   │
│  │ 101                 │   │
│  └─────────────────────┘   │
│                             │
│  Password                   │
│  ┌─────────────────────┐   │
│  │ ••••••••••••        │   │
│  └─────────────────────┘   │
│                             │
│  Domain                     │
│  ┌─────────────────────┐   │
│  │ pbx.vouchersdept.com│   │
│  └─────────────────────┘   │
│                             │
│  Transport: TLS             │
│  Port: 5061                 │
│                             │
│  ☑ Enable                   │
│  ☑ Register                 │
│                             │
│      [Cancel]  [Save]       │
│                             │
└─────────────────────────────┘
```

---

## 🎧 Best Practices for Agents

### Audio Quality

1. **Use a headset** - Better than phone speaker/mic
2. **Wired is better** - More reliable than Bluetooth
3. **Quiet environment** - Minimize background noise
4. **Test before shift** - Make a test call first

### Recommended Headsets

**Budget ($20-50):**
- Logitech H390 USB Headset
- Jabra Evolve 20
- Plantronics Blackwire C3220

**Professional ($50-150):**
- Jabra Evolve 40
- Plantronics Voyager Focus UC
- Sennheiser SC 160 USB

**Mobile:**
- Any wired earbuds with mic
- Apple EarPods
- Samsung AKG earbuds

### Connection Tips

1. **WiFi preferred** - More stable than mobile data
2. **Strong signal** - Stay near router
3. **Avoid VPN** - Can cause audio issues
4. **Close other apps** - Reduce bandwidth usage

### During Calls

1. **Answer quickly** - Customer is waiting
2. **Speak clearly** - Good microphone technique
3. **Take notes** - Use CRM or notepad
4. **Professional greeting** - "Hello, this is [Name]"
5. **End politely** - "Thank you for your time"

---

## 🔍 Troubleshooting

### Problem: Not Registered

**Symptoms:** Red indicator, "Not Registered" status

**Solutions:**
1. Check internet connection
2. Verify credentials (username, password, domain)
3. Check transport is set to **TLS**
4. Check port is set to **5061**
5. Restart Linphone
6. Check firewall (allow port 5061)
7. Contact system administrator

### Problem: Can't Hear Caller

**Symptoms:** Call connects but no audio

**Solutions:**
1. Check speaker volume
2. Select correct audio device (Settings → Audio)
3. Test audio in Linphone settings
4. Check system volume
5. Try different headset
6. Restart Linphone

### Problem: Caller Can't Hear You

**Symptoms:** You can hear them, they can't hear you

**Solutions:**
1. Check microphone is not muted
2. Select correct microphone (Settings → Audio)
3. Test microphone in Linphone settings
4. Check system microphone permissions
5. Try different headset
6. Restart Linphone

### Problem: Calls Not Coming Through

**Symptoms:** No incoming calls, no ringing

**Solutions:**
1. Verify registration status (should be green)
2. Check notifications are enabled
3. Check app is running (not force-closed)
4. Disable battery optimization (Android)
5. Enable background app refresh (iOS)
6. Check Do Not Disturb is off
7. Restart Linphone

### Problem: Poor Audio Quality

**Symptoms:** Choppy, robotic, or distorted audio

**Solutions:**
1. Check internet speed (need 100+ kbps)
2. Close bandwidth-heavy apps
3. Move closer to WiFi router
4. Switch from mobile data to WiFi
5. Disable VPN
6. Use wired headset instead of Bluetooth
7. Lower audio quality in settings (if available)

### Problem: Echo or Feedback

**Symptoms:** Hearing your own voice back

**Solutions:**
1. Use headset instead of speaker
2. Lower speaker volume
3. Enable echo cancellation (Settings → Audio)
4. Move microphone away from speaker
5. Check other person isn't on speaker

---

## 📊 Quick Reference Card

Print this for your agents:

```
╔═══════════════════════════════════════════════════════════╗
║           LINPHONE QUICK REFERENCE - AGENT 1              ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  Username:     101                                        ║
║  Password:     ChangeMe101!                               ║
║  Domain:       pbx.vouchersdept.com                       ║
║  Transport:    TLS                                        ║
║  Port:         5061                                       ║
║                                                           ║
║  Status:       Must show GREEN or "Registered"            ║
║                                                           ║
║  Download:     https://www.linphone.org/                  ║
║                                                           ║
║  Support:      Contact your system administrator          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════╗
║           LINPHONE QUICK REFERENCE - AGENT 2              ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  Username:     102                                        ║
║  Password:     ChangeMe102!                               ║
║  Domain:       pbx.vouchersdept.com                       ║
║  Transport:    TLS                                        ║
║  Port:         5061                                       ║
║                                                           ║
║  Status:       Must show GREEN or "Registered"            ║
║                                                           ║
║  Download:     https://www.linphone.org/                  ║
║                                                           ║
║  Support:      Contact your system administrator          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```

---

## 🎯 Pre-Shift Checklist

Before starting your shift, verify:

- [ ] Linphone is running
- [ ] Status shows **GREEN** or **"Registered"**
- [ ] Headset is connected and working
- [ ] Microphone test passes
- [ ] Speaker test passes
- [ ] Internet connection is stable
- [ ] Notifications are enabled
- [ ] Battery is charged (mobile)
- [ ] Quiet environment
- [ ] CRM/notes ready

---

## 📞 Call Flow for Agents

### When a Call Comes In:

1. **Linphone rings** 🔔
2. **Answer the call** (click Answer button)
3. **Greet the customer** professionally
4. **Handle the conversation** (sales pitch, survey, etc.)
5. **Take notes** in your CRM
6. **End the call** politely
7. **Hang up** (click Hang Up button)
8. **Update CRM** with call outcome
9. **Ready for next call** 🔄

### Call Outcomes:

- ✅ **Answered** - Customer engaged, conversation happened
- 📧 **Voicemail** - Went to voicemail, message dropped
- ❌ **No Answer** - Customer didn't pick up
- 🚫 **Busy** - Line was busy
- ⚠️ **Failed** - Technical issue

---

## 🔐 Security Notes

### Password Security

- **Don't share** your credentials
- **Don't write down** passwords in plain text
- **Change password** if compromised
- **Use secure connection** (TLS enabled)

### Privacy

- **Don't record calls** without consent
- **Follow company policy** on data handling
- **Secure your device** with PIN/password
- **Log out** when not working

---

## 📱 Alternative Softphones

If Linphone doesn't work for you, try these alternatives:

### PC Alternatives:
1. **Zoiper** - https://www.zoiper.com/
2. **MicroSIP** - https://www.microsip.org/ (Windows only)
3. **Bria** - https://www.counterpath.com/bria/

### Mobile Alternatives:
1. **Zoiper** - Available on Play Store / App Store
2. **Bria Mobile** - Available on Play Store / App Store
3. **Grandstream Wave** - Available on Play Store / App Store

**Note:** Configuration is similar - use the same credentials and settings.

---

## 🆘 Getting Help

### Self-Help Resources

1. **Linphone Documentation:** https://wiki.linphone.org/
2. **Video Tutorials:** Search "Linphone setup" on YouTube
3. **This Guide:** Keep it handy for reference

### Contact Support

If you still have issues:

1. **Check this guide first** - Most issues are covered
2. **Contact your supervisor** - They can help with basic issues
3. **Contact IT/System Admin** - For technical problems
4. **Provide details:**
   - What's the problem?
   - What have you tried?
   - Screenshots if possible
   - Error messages

---

## ✅ Success Checklist

You're ready when:

- ✅ Linphone installed on your device
- ✅ Account configured with correct credentials
- ✅ Status shows GREEN / "Registered"
- ✅ Audio test passed (mic and speaker work)
- ✅ Headset connected and comfortable
- ✅ Internet connection stable
- ✅ Notifications enabled
- ✅ You understand the call flow
- ✅ You know how to troubleshoot basic issues
- ✅ You have this guide saved for reference

---

## 🎉 You're All Set!

Welcome to the team! You're now ready to receive calls and help customers. Remember:

- **Stay professional** on every call
- **Be patient** with customers
- **Ask for help** when needed
- **Keep learning** and improving

**Good luck and happy calling!** 📞✨

---

**Document Version:** 1.0  
**Last Updated:** May 7, 2026  
**For:** VoIP Outbound Calling System  
**Support:** Contact your system administrator
