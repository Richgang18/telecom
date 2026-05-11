# 📞 How Calls Work - Mobile Agent Mode

## Important: Calls Go to Your Mobile Phone!

With **mobile agent mode**, calls do NOT ring on your computer. They ring on your **mobile phone** directly.

---

## 🎯 Call Flow

```
1. System dials lead
   ↓
2. Lead answers
   ↓
3. AMD detects human (not machine)
   ↓
4. System dials YOUR MOBILE PHONE
   ↓
5. YOUR PHONE RINGS ← You answer here!
   ↓
6. Both calls bridged together
   ↓
7. You talk to the lead
```

---

## 📱 Where You Receive Calls

### Mobile Agent Mode (Current Setup)
**Calls ring on:** Your mobile phone (configured in Settings)

**What you need:**
- ✅ Your mobile phone
- ✅ Mobile signal or WiFi
- ✅ Phone charged

**What you DON'T need:**
- ❌ Computer (except to start the system)
- ❌ Softphone
- ❌ Headset connected to computer

### Example:
```
You configure: agent_mobile_numbers = +14145551234

When lead answers:
→ Your mobile phone (+14145551234) rings
→ You answer your phone
→ You talk to the lead
```

---

## 🖥️ What the Computer Does

The computer (client system) is used for:

1. **Running the dialer** - Makes outbound calls
2. **Managing the campaign** - Tracks results
3. **Routing calls** - Decides which agent to call
4. **Dropping voicemail** - When no one answers

**The computer does NOT:**
- ❌ Ring when a call comes in
- ❌ Handle audio
- ❌ Act as a phone

---

## 🔄 If You Want Calls on the Computer

If you want to receive calls on the computer instead of mobile, you need to:

### Option 1: Use Softphone Mode

**Change config.ini:**
```ini
[agents]
agent_mode = softphone  # Change from "mobile" to "softphone"
agent_extensions = 101,102
```

**Then:**
1. Go to Desktop App → Softphone tab
2. Click "Launch Softphone" for Agent 1
3. Softphone window will open on your computer
4. Calls will ring in the softphone window
5. Click "Answer" to take the call

**Requirements:**
- Computer must stay on
- Softphone must be running
- Microphone/speakers connected

### Option 2: Use Both (Hybrid)

You can switch between modes:

**For office work:**
```ini
agent_mode = softphone
```
Launch softphone, receive calls on computer

**For remote work:**
```ini
agent_mode = mobile
agent_mobile_numbers = +14145551234
```
Receive calls on mobile phone

---

## 💡 Why Mobile Mode is Better

### Mobile Mode Advantages:
✅ **Work from anywhere** - Not tied to computer  
✅ **Better mobility** - Walk around while talking  
✅ **No softphone setup** - Just use your phone  
✅ **More reliable** - Mobile networks are stable  
✅ **Professional** - Same as VICIdial call centers  

### Softphone Mode Advantages:
✅ **No mobile needed** - Use computer only  
✅ **Lower cost** - Single call leg ($0.013/min vs $0.026/min)  
✅ **Recording easier** - Can record on computer  
✅ **Headset use** - Professional USB headset  

---

## 🎯 Current Configuration

**Your system is configured for:**
```
Mobile Agent Mode
```

**This means:**
- Calls ring on your mobile phone
- You answer your mobile phone
- You talk to leads on your mobile phone
- Computer manages the campaign

**To change this:**
1. Edit `config.ini`
2. Change `agent_mode = mobile` to `agent_mode = softphone`
3. Restart the system
4. Launch softphone from Desktop App

---

## 📋 Quick Reference

| Mode | Where Calls Ring | What You Need |
|------|------------------|---------------|
| **Mobile** | Your mobile phone | Mobile phone, signal |
| **Softphone** | Computer softphone window | Computer, microphone, speakers |

---

## ❓ FAQ

### Q: Why doesn't my computer ring when a call comes in?

**A:** Because you're using **mobile agent mode**. Calls go to your mobile phone, not your computer.

### Q: How do I make calls ring on my computer?

**A:** Change to **softphone mode**:
1. Edit `config.ini`
2. Set `agent_mode = softphone`
3. Restart system
4. Launch softphone

### Q: Can I use both mobile and computer?

**A:** Yes! Switch between modes by changing `agent_mode` in config.ini

### Q: Which mode is better?

**A:** 
- **Mobile mode** - Better for flexibility, working remotely
- **Softphone mode** - Better for office work, lower cost

### Q: Do I need the computer running during calls?

**A:** 
- **Mobile mode** - Computer must run the dialer, but you can walk away with your phone
- **Softphone mode** - Computer must stay on and softphone must be running

---

## 🚀 Summary

**Current Setup (Mobile Agent Mode):**

1. Computer runs the dialer
2. System calls leads
3. When lead answers, system calls YOUR MOBILE
4. Your mobile phone rings
5. You answer your phone
6. You talk to the lead

**Your computer does NOT ring. Your mobile phone rings.** ✅

---

**Need to change this?** See [MOBILE_AGENT_GUIDE.md](MOBILE_AGENT_GUIDE.md) for details.
