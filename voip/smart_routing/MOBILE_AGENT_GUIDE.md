# 📱 Mobile Agent Guide - VICIdial-Style Call Bridging

## Overview

The system now supports **mobile agent mode** where calls are bridged directly to your cellphone instead of requiring a softphone. This is the same workflow used by VICIdial and other professional call centers.

---

## 🎯 How It Works

### Call Flow

```
1. System dials lead
   ↓
2. Lead answers
   ↓
3. AMD detects human (not machine)
   ↓
4. System dials YOUR MOBILE
   ↓
5. You answer your phone
   ↓
6. Both calls are BRIDGED together
   ↓
7. You talk to the lead
   ↓
8. You hang up
   ↓
9. System marks you available for next call
```

### What You Experience

**On your mobile phone:**
1. Phone rings showing the lead's number
2. You answer
3. You hear: "Connecting you to an agent. Please wait."
4. Call connects - you're now talking to the lead
5. You hang up when done

**No softphone needed!** ✅

---

## ⚙️ Configuration

### Step 1: Edit config.ini

```ini
[agents]
# Set mode to "mobile"
agent_mode = mobile

# Your mobile phone number(s) in E.164 format
agent_mobile_numbers = +14145551234,+14145555678

# Agent names
agent_names = John Doe,Jane Smith

# How long to wait for you to answer (seconds)
agent_timeout = 20

# Enable answering machine detection
enable_amd = true
amd_timeout = 30
```

### Step 2: Configure in Desktop App

1. Launch the desktop app
2. Go to **Settings** tab
3. Set **Agent Mode** to "Mobile"
4. Enter your **Mobile Number** (E.164 format: +1XXXXXXXXXX)
5. Set **Agent Timeout** (recommended: 20 seconds)
6. Enable **AMD** (Answering Machine Detection)
7. Click **Save Settings**

---

## 🚀 Usage

### Starting a Campaign

1. **Launch the system**
   - Double-click "Smart Dialer" shortcut on desktop
   - OR run `Launch_Dialer.bat`

2. **Upload contacts**
   - Go to Contacts tab
   - Upload your CSV file

3. **Start calling**
   - Go to Dashboard tab
   - Click "Start Calling"

4. **Answer your phone**
   - When a lead answers, your phone will ring
   - Answer it and talk to the lead
   - Hang up when done

### What Happens When Lead Answers

1. **Human answers:**
   - System calls your mobile
   - You answer
   - Call is bridged
   - You talk to lead

2. **Machine answers:**
   - AMD detects answering machine
   - System drops voicemail automatically
   - Your phone does NOT ring
   - System moves to next lead

3. **No answer:**
   - System drops voicemail
   - Your phone does NOT ring
   - System moves to next lead

---

## 💰 Cost Implications

### Twilio Pricing

With mobile agent mode, each answered call uses **2 call legs**:

| Call Leg | Cost (US) |
|----------|-----------|
| Twilio → Lead | ~$0.013/min |
| Twilio → Your Mobile | ~$0.013/min |
| **Total** | **~$0.026/min** |

**Example:**
- 10-minute call = $0.26
- 100 calls × 5 min avg = $13.00

### Comparison

| Mode | Cost per Minute | Notes |
|------|----------------|-------|
| Softphone | $0.013/min | Single leg (Twilio → Lead) |
| Mobile | $0.026/min | Double leg (Twilio → Lead + Twilio → Mobile) |

**Mobile mode costs 2x more** but provides much better flexibility!

---

## 🎛️ Advanced Settings

### Agent Timeout

How long the system waits for you to answer before going to voicemail:

```ini
agent_timeout = 20  # seconds
```

**Recommendations:**
- **20 seconds** - Standard (4-5 rings)
- **15 seconds** - Fast-paced (3-4 rings)
- **30 seconds** - Relaxed (6-7 rings)

### AMD (Answering Machine Detection)

Controls whether the system detects answering machines:

```ini
enable_amd = true
amd_timeout = 30
```

**When enabled:**
- ✅ Only human-answered calls forwarded to you
- ✅ Machines get voicemail automatically
- ✅ Saves your time

**When disabled:**
- ❌ ALL answered calls forwarded to you
- ❌ You may answer and hear a beep (answering machine)
- ❌ Wastes your time

**Recommendation:** Keep AMD enabled!

### Multiple Agents

You can configure multiple mobile agents:

```ini
agent_mobile_numbers = +14145551234,+14145555678
agent_names = Agent 1,Agent 2
max_concurrent_calls = 2
```

System will route calls to available agents automatically.

---

## 🔧 Troubleshooting

### "Your phone never rings"

**Possible causes:**
1. **AMD flagged call as machine**
   - Check Activity Log for "Answering machine detected"
   - AMD is ~95% accurate but not perfect
   - Try disabling AMD temporarily to test

2. **Wrong mobile number**
   - Verify number in config.ini
   - Must be E.164 format: +1XXXXXXXXXX
   - No spaces, dashes, or parentheses

3. **Twilio account issue**
   - Check Twilio console for errors
   - Verify account has credits
   - Check for any restrictions

### "Call connects but no audio"

**Possible causes:**
1. **Network issue**
   - Check your mobile signal strength
   - Try WiFi calling if available

2. **Twilio trunk issue**
   - Check Twilio console for errors
   - Verify SIP trunk is configured

### "System says 'All agents busy'"

**Cause:** You're already on a call

**Solution:** Hang up current call first, then system will dial next lead

### "Lead hears silence before I answer"

**This is normal!** The lead hears:
1. "Connecting you to an agent. Please wait." (while your phone rings)
2. Brief silence (while call bridges)
3. Your voice (when you start talking)

**To improve:**
- Answer quickly (within 2-3 rings)
- Start talking immediately: "Hello, this is [Your Name]..."

---

## 📊 Monitoring

### Activity Log

Watch the Activity Log in the Dashboard tab:

```
[10:30:15] Dialing John Smith (+14145551001)...
[10:30:18] Call answered by human
[10:30:18] Connecting call to mobile agent 0 (+14145551234)
[10:30:25] Mobile agent 0 answered
[10:30:25] Call bridged successfully
[10:32:45] Call ended - duration: 2m 20s
[10:32:45] ✅ Mobile agent 0 marked available
```

### Call Results

Go to **Call Results** tab to see:
- Which calls were answered
- Which went to voicemail
- Call duration
- Agent who handled each call

---

## 🔄 Switching Between Modes

### Mobile → Softphone

1. Edit config.ini:
   ```ini
   agent_mode = softphone
   ```

2. Restart the system

3. Launch softphones (Softphone tab)

### Softphone → Mobile

1. Edit config.ini:
   ```ini
   agent_mode = mobile
   agent_mobile_numbers = +14145551234
   ```

2. Restart the system

3. No softphone needed!

---

## 🎯 Best Practices

### 1. **Use a Dedicated Business Line**
- Don't use your personal cell number
- Get a separate business line
- Or use Google Voice / similar service

### 2. **Enable WiFi Calling**
- Better call quality
- More reliable
- Works indoors

### 3. **Keep Phone Charged**
- Use a charger during campaigns
- Don't let battery die mid-call

### 4. **Use Headset**
- Bluetooth or wired headset
- Hands-free operation
- Better audio quality

### 5. **Quiet Environment**
- Find a quiet place
- Minimize background noise
- Professional impression

### 6. **Answer Quickly**
- Answer within 2-3 rings
- Lead is waiting
- Better experience

### 7. **Have Script Ready**
- Know what to say
- Have talking points
- Be prepared

---

## 📋 Quick Reference

### Configuration File Location
```
voip/smart_routing/config.ini
```

### Key Settings
```ini
[agents]
agent_mode = mobile
agent_mobile_numbers = +14145551234
agent_timeout = 20
enable_amd = true
```

### Launcher
```
Double-click: Smart Dialer (desktop shortcut)
Or run: Launch_Dialer.bat
```

### Logs
```
Activity Log: Desktop App → Dashboard tab
System Log: smart_routing.log
Twilio Log: https://console.twilio.com/
```

---

## ❓ FAQ

### Q: Can I use my personal cell phone?

**A:** Yes, but not recommended. Use a dedicated business line for:
- Professionalism
- Separation of work/personal
- Better tracking

### Q: What if I miss a call?

**A:** The system will:
1. Wait for `agent_timeout` seconds
2. Drop voicemail if you don't answer
3. Move to next lead
4. Mark you as available again

### Q: Can I use this while traveling?

**A:** Yes! As long as you have:
- Mobile signal or WiFi
- Phone charged
- Quiet environment

### Q: Does the lead see my personal number?

**A:** No! The lead sees:
- Your Twilio number (caller ID)
- NOT your personal mobile number

### Q: Can I have multiple agents on mobile?

**A:** Yes! Configure multiple mobile numbers:
```ini
agent_mobile_numbers = +14145551234,+14145555678
```

### Q: What's the call quality like?

**A:** Excellent! Same quality as regular phone calls. Depends on:
- Your mobile carrier
- Signal strength
- WiFi calling (if enabled)

---

## 🎉 Summary

**Mobile agent mode gives you:**

✅ **Flexibility** - Answer calls anywhere  
✅ **No softphone** - Use your regular phone  
✅ **Professional** - VICIdial-style workflow  
✅ **AMD** - Only human-answered calls forwarded  
✅ **Easy setup** - Just configure your mobile number  
✅ **Cost-effective** - ~$0.026/min (2x softphone but worth it!)  

**Perfect for:**
- Remote agents
- On-the-go calling
- No desktop/computer needed
- Professional call centers

---

**Ready to start?** Configure your mobile number and launch the system! 🚀
