# Integrated Softphone Setup Guide

## Overview

The integrated softphone allows agents to receive calls **directly in the desktop application** without needing Linphone or any external SIP client. This eliminates all the configuration headaches!

## Features

✅ **No External Software Needed** - Everything runs in the desktop app  
✅ **Automatic Registration** - Connects to Asterisk automatically  
✅ **Visual Call Interface** - See incoming calls with caller info  
✅ **One-Click Answer/Hangup** - Simple call controls  
✅ **Activity Logging** - Track all call events  
✅ **Multiple Agents** - Run softphones for both agents simultaneously  

## Installation

### Step 1: Install PyAudio

PyAudio is required for audio handling.

#### Windows:

```powershell
# Option 1: Using pip (recommended)
pip install pyaudio

# Option 2: If pip fails, download pre-built wheel
# Visit: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
# Download the appropriate .whl file for your Python version
# Then install: pip install PyAudio-0.2.11-cp39-cp39-win_amd64.whl
```

#### Linux (WSL2):

```bash
# Install PortAudio first
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-pyaudio

# Then install PyAudio
pip3 install pyaudio
```

#### macOS:

```bash
# Install PortAudio first
brew install portaudio

# Then install PyAudio
pip3 install pyaudio
```

### Step 2: Install All Requirements

```bash
cd voip/smart_routing
pip install -r requirements_softphone.txt
```

### Step 3: Verify Installation

```bash
python -c "import pyaudio; print('PyAudio installed successfully!')"
```

## Usage

### Launching the Softphone

1. **Open the Desktop App**
   ```bash
   python desktop_app.py
   ```

2. **Go to the "📞 Softphone" Tab**

3. **Click "🚀 Launch Softphone"** for Agent 1 or Agent 2

4. **A new window will open** showing the softphone interface

### Softphone Window

The softphone window shows:

- **Extension Number** - Your agent extension (101 or 102)
- **Status** - Registration status with Asterisk
- **Call Display** - Shows caller information when a call comes in
- **Answer Button** - Click to answer incoming calls
- **Hangup Button** - Click to end the call
- **Activity Log** - Shows all events (registration, calls, etc.)

### Receiving Calls

1. **Softphone must be running** - Keep the softphone window open
2. **When a call comes in:**
   - The window will flash to get your attention
   - You'll see the caller's extension/number
   - A system beep will sound
3. **Click "📞 Answer"** to accept the call
4. **Click "📵 Hangup"** to end the call

### Multiple Agents

You can run softphones for both agents simultaneously:

1. Launch softphone for Agent 1 (Extension 101)
2. Launch softphone for Agent 2 (Extension 102)
3. Both will register independently
4. Calls will be routed to available agents

## Configuration

### Default Settings

- **Domain:** `172.25.17.93` (WSL2 Asterisk IP)
- **Port:** `5060` (TCP)
- **Extension 101:** Password `ChangeMe101!`
- **Extension 102:** Password `ChangeMe102!`

### Changing Settings

Edit `desktop_app.py` in the `launch_softphone()` method:

```python
def launch_softphone(self, extension: int):
    # Change these values
    domain = "172.25.17.93"  # Your Asterisk IP
    port = 5060              # Your SIP port
    
    passwords = {
        101: "ChangeMe101!",  # Agent 1 password
        102: "ChangeMe102!"   # Agent 2 password
    }
```

## Troubleshooting

### "Softphone module not available"

**Problem:** PyAudio is not installed

**Solution:**
```bash
pip install pyaudio
```

If that fails on Windows:
```powershell
# Download pre-built wheel from:
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
pip install PyAudio-0.2.11-cp39-cp39-win_amd64.whl
```

### "Initializing..." never changes

**Problem:** Cannot connect to Asterisk

**Solutions:**
1. Check Asterisk is running:
   ```bash
   wsl sudo systemctl status asterisk
   ```

2. Check Asterisk is listening on port 5060:
   ```bash
   wsl sudo ss -tulpn | grep 5060
   ```

3. Verify the domain IP is correct (should be WSL2 IP):
   ```bash
   wsl hostname -I
   ```

4. Check Windows firewall allows port 5060

### "Registration failed"

**Problem:** Authentication or network issue

**Solutions:**
1. Verify credentials in Asterisk:
   ```bash
   wsl sudo grep -A 10 "^\[101\]" /etc/asterisk/pjsip.conf
   ```

2. Check Asterisk logs:
   ```bash
   wsl sudo asterisk -rvvvvv
   ```

3. Verify endpoint is loaded:
   ```bash
   wsl sudo asterisk -rx "pjsip show endpoint 101"
   ```

### No audio during call

**Problem:** Audio device not accessible

**Solutions:**
1. Check audio devices are available:
   ```python
   import pyaudio
   p = pyaudio.PyAudio()
   for i in range(p.get_device_count()):
       print(p.get_device_info_by_index(i))
   ```

2. Make sure no other application is using the microphone

3. Check Windows audio settings - ensure microphone is not muted

### Call doesn't ring

**Problem:** Softphone not registered or Asterisk routing issue

**Solutions:**
1. Check softphone status shows "✓ Registered"

2. Verify Asterisk can reach the extension:
   ```bash
   wsl sudo asterisk -rx "pjsip show endpoint 101"
   ```

3. Check dialplan routes calls to the extension:
   ```bash
   wsl sudo grep -A 5 "Dial(PJSIP/101" /etc/asterisk/extensions.conf
   ```

## Advantages Over Linphone

| Feature | Integrated Softphone | Linphone |
|---------|---------------------|----------|
| Installation | One pip command | Download, install, configure |
| Configuration | Automatic | Manual (domain, port, auth, etc.) |
| Integration | Built into app | Separate application |
| Troubleshooting | Logs in app | Separate logs |
| User Experience | Seamless | Context switching |
| Network Issues | Fewer (same machine) | More (mobile/remote) |

## Architecture

```
┌─────────────────────────────────────────┐
│         Desktop Application             │
│  ┌───────────────────────────────────┐  │
│  │     Softphone Tab                 │  │
│  │  ┌─────────────┐ ┌─────────────┐ │  │
│  │  │  Agent 1    │ │  Agent 2    │ │  │
│  │  │  Ext 101    │ │  Ext 102    │ │  │
│  │  └─────────────┘ └─────────────┘ │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                  │
                  │ SIP (UDP/TCP)
                  │ Port 5060
                  ▼
┌─────────────────────────────────────────┐
│         Asterisk PBX (WSL2)             │
│  ┌───────────────────────────────────┐  │
│  │     PJSIP Endpoints               │  │
│  │  • 101 (Agent 1)                  │  │
│  │  • 102 (Agent 2)                  │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │     Dialplan                      │  │
│  │  • Routes calls to agents         │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                  │
                  │ SIP Trunk
                  ▼
┌─────────────────────────────────────────┐
│              Twilio                     │
│  • Receives inbound calls               │
│  • Makes outbound calls                 │
└─────────────────────────────────────────┘
```

## Next Steps

1. **Install PyAudio** (see Step 1 above)
2. **Launch the desktop app**
3. **Open the Softphone tab**
4. **Click "Launch Softphone" for each agent**
5. **Start your calling campaign!**

## Support

If you encounter issues:

1. Check the Activity Log in the softphone window
2. Check the Activity Log in the main dashboard
3. Check Asterisk console: `wsl sudo asterisk -rvvvvv`
4. Review this troubleshooting guide

---

**You're all set!** No more Linphone configuration headaches. Just launch and go! 🚀
