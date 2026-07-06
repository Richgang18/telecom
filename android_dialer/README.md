# Smart Dialer — Android Agent App

Outbound dialer Android app with live agent calling, blind transfer,
call recording, and real-time voice conversion (Deepgram STT → Cartesia TTS).

---

## Project Structure

```
android_dialer/
├── backend/           ← Python FastAPI backend (runs on port 5001)
│   ├── agent_api.py
│   ├── agent_config.ini
│   ├── requirements.txt
│   └── start.bat
└── app/               ← Android app (Kotlin)
    ├── build.gradle
    └── src/main/
        ├── AndroidManifest.xml
        ├── kotlin/com/smartdialer/agent/
        │   ├── MainActivity.kt
        │   ├── SmartDialerApp.kt
        │   ├── data/          ← API, WebSocket, Session
        │   ├── service/       ← Foreground call service
        │   └── ui/            ← Fragments + ViewModels
        └── res/               ← Layouts, navigation, themes
```

---

## What I Need From You

### 1. New SignalWire Account
Create a **new** SignalWire project at https://signalwire.com:
- Project ID (goes in `account_sid`)
- API Token (goes in `auth_token`)
- Space URL (e.g. `myspace.signalwire.com`)
- Buy a phone number for outbound calls
- **SIP Domain**: go to Integrations → SIP → create a SIP endpoint
  - Create 2 SIP credentials: `agent1` and `agent2` with passwords
  - Note the SIP domain (e.g. `myspace.sip.signalwire.com`)

### 2. Deepgram API Key (free tier — 200hrs/month)
- Sign up at https://console.deepgram.com
- Create an API key
- Free tier is enough for 2 agents

### 3. Cartesia API Key (voice conversion)
- Sign up at https://cartesia.ai
- Get API key
- Find an American English voice ID at https://app.cartesia.ai/voices
  - Recommended: search "American" and pick a neutral male/female voice

### 4. Ngrok (or fixed domain) for the backend
The backend must be reachable from the internet (SignalWire webhooks).
Either:
- Use ngrok: `ngrok http 5001`
- Or deploy backend to a VPS/cloud server

### 5. Agent passwords
Decide passwords for `agent1` and `agent2` — update in `agent_config.ini`

---

## Backend Setup

1. Fill in `backend/agent_config.ini` with all values above
2. Run `backend/start.bat` (Windows) or:
   ```bash
   pip install -r requirements.txt
   python agent_api.py
   ```
3. Start ngrok: `ngrok http 5001`
4. Update `webhook_base_url` in config with the ngrok URL

---

## Android App Setup

1. Open `android_dialer/` folder in **Android Studio Hedgehog** or newer
2. Wait for Gradle sync to complete
3. In the app's login screen, enter:
   - **Server URL**: your ngrok URL (e.g. `https://abc123.ngrok-free.app`)
   - **Agent ID**: `agent1` or `agent2`
   - **Password**: as set in config

---

## Voice Conversion Flow

```
Agent speaks → Android mic → WebSocket → Deepgram STT
                                              ↓ transcript
                                         Cartesia TTS
                                              ↓ American voice audio
                                    Played into the phone call
```

Latency: ~200ms (Deepgram ~100ms + Cartesia ~80ms + network ~20ms)

---

## Features

- ✅ Lead list with search and status filter
- ✅ Lead detail with notes
- ✅ One-tap outbound calling
- ✅ Live call screen with timer
- ✅ Call recording (automatic via SignalWire)
- ✅ Blind transfer to another agent
- ✅ Real-time WebSocket events
- ✅ Foreground service (call stays alive when app backgrounded)
- ✅ Voice conversion: any accent → American English
- ✅ JWT authentication per agent
- ✅ CSV lead import via API
