# 🚀 Quick Start - Integrated Softphone

## 3-Step Setup (Takes 2 Minutes)

### Step 1: Install PyAudio

**Windows:**
```powershell
pip install pyaudio
```

**If that fails, run:**
```powershell
.\install_softphone.ps1
```

### Step 2: Launch Desktop App

```bash
python desktop_app.py
```

### Step 3: Launch Softphones

1. Click **"📞 Softphone"** tab
2. Click **"🚀 Launch Softphone"** for Agent 1
3. Click **"🚀 Launch Softphone"** for Agent 2

**Done!** ✅

---

## What You Get

✅ **No Linphone needed** - Everything built-in  
✅ **No configuration** - Works automatically  
✅ **No network issues** - Runs on same machine  
✅ **Visual interface** - See calls, answer with one click  
✅ **Activity logs** - Track everything  

---

## Using It

### When a call comes in:
1. Softphone window flashes
2. You see caller info
3. Click **"📞 Answer"**
4. Talk to customer
5. Click **"📵 Hangup"** when done

### Running a campaign:
1. Launch both softphones (Agent 1 & 2)
2. Wait for "✓ Registered" status
3. Go to Dashboard tab
4. Click **"▶ Start Calling"**
5. Calls route to agents automatically

---

## Troubleshooting

### "Softphone module not available"
```bash
pip install pyaudio
```

### "Initializing..." never changes
```bash
# Check Asterisk is running
wsl sudo systemctl status asterisk

# Check it's listening on port 5060
wsl sudo ss -tulpn | grep 5060
```

### "Registration failed"
```bash
# Verify endpoint exists
wsl sudo asterisk -rx "pjsip show endpoint 101"

# Reload Asterisk
wsl sudo asterisk -rx "pjsip reload"
```

---

## Files Created

- `softphone.py` - SIP client implementation
- `desktop_app.py` - Updated with softphone tab
- `test_softphone_standalone.py` - Test script
- `install_softphone.ps1` - Windows installer
- `requirements_softphone.txt` - Dependencies
- `SOFTPHONE_SETUP.md` - Detailed guide
- `INTEGRATED_SOFTPHONE_README.md` - Complete documentation
- `QUICK_START_SOFTPHONE.md` - This file

---

## Need More Help?

- **Detailed setup:** See `SOFTPHONE_SETUP.md`
- **Full documentation:** See `INTEGRATED_SOFTPHONE_README.md`
- **Test standalone:** Run `python test_softphone_standalone.py`

---

**That's it! No more Linphone headaches!** 🎉
