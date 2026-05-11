# 🏗️ System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Windows Machine                             │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │              Desktop Application (Python/Tkinter)             │ │
│  │                                                               │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │ │
│  │  │  Dashboard  │  │  Softphone  │  │  Contacts   │         │ │
│  │  │  • Start    │  │  • Agent 1  │  │  • Upload   │         │ │
│  │  │  • Stop     │  │  • Agent 2  │  │  • Manage   │         │ │
│  │  │  • Monitor  │  │  • Answer   │  │  • View     │         │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘         │ │
│  │                                                               │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │ │
│  │  │   Results   │  │  Settings   │  │   Agents    │         │ │
│  │  │  • Filter   │  │  • Twilio   │  │  • Status   │         │ │
│  │  │  • Export   │  │  • Config   │  │  • Config   │         │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘         │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    Background Services                        │ │
│  │                                                               │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │ │
│  │  │   Dialer     │  │   Webhook    │  │    Ngrok     │      │ │
│  │  │  dialer.py   │  │  webhook_    │  │  (Tunnel)    │      │ │
│  │  │              │  │  server.py   │  │              │      │ │
│  │  │  • Read CSV  │  │  • Port 5000 │  │  • Expose    │      │ │
│  │  │  • Call API  │  │  • Handle    │  │    webhook   │      │ │
│  │  │  • Track     │  │    callbacks │  │              │      │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │ │
│  │                                                               │ │
│  │  ┌──────────────┐  ┌──────────────┐                         │ │
│  │  │ Agent Router │  │  Voicemail   │                         │ │
│  │  │ agent_       │  │  voicemail_  │                         │ │
│  │  │ router.py    │  │  drop.py     │                         │ │
│  │  │              │  │              │                         │ │
│  │  │  • Track     │  │  • Drop VM   │                         │ │
│  │  │    agents    │  │  • Play MP3  │                         │ │
│  │  │  • Route     │  │              │                         │ │
│  │  └──────────────┘  └──────────────┘                         │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    WSL2 Ubuntu                                │ │
│  │                                                               │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │                  Asterisk PBX                           │ │ │
│  │  │                                                         │ │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │ │ │
│  │  │  │   PJSIP      │  │   Dialplan   │  │  Transports │ │ │ │
│  │  │  │              │  │              │  │             │ │ │ │
│  │  │  │  • Endpoint  │  │  • Route to  │  │  • TCP      │ │ │ │
│  │  │  │    101       │  │    agents    │  │    :5060    │ │ │ │
│  │  │  │  • Endpoint  │  │  • Handle    │  │  • UDP      │ │ │ │
│  │  │  │    102       │  │    calls     │  │    :5060    │ │ │ │
│  │  │  └──────────────┘  └──────────────┘  └─────────────┘ │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │ HTTPS (Webhooks)
                                │ SIP (Calls)
                                ▼
                    ┌───────────────────────┐
                    │       Twilio          │
                    │                       │
                    │  • Outbound Calls     │
                    │  • Inbound Calls      │
                    │  • SIP Trunk          │
                    │  • Webhooks           │
                    └───────────────────────┘
                                │
                                │ PSTN
                                ▼
                    ┌───────────────────────┐
                    │      Customers        │
                    │   (Phone Numbers)     │
                    └───────────────────────┘
```

---

## Component Details

### Desktop Application Layer

**Purpose:** User interface and campaign management

**Components:**
- **Dashboard Tab:** System status, campaign control, statistics
- **Softphone Tab:** Integrated SIP softphones for agents
- **Contacts Tab:** Upload and manage contact lists
- **Results Tab:** View and export call outcomes
- **Settings Tab:** Configure Twilio, voicemail, dialer
- **Agents Tab:** Agent configuration and status

**Technology:** Python, Tkinter

---

### Background Services Layer

**Purpose:** Handle calling logic and webhooks

#### 1. Dialer (dialer.py)

**Responsibilities:**
- Read contacts from CSV
- Check agent availability
- Make outbound calls via Twilio API
- Track call progress
- Handle call outcomes

**Flow:**
```
1. Load contacts from CSV
2. For each contact:
   a. Check if agent available
   b. If yes: Make call via Twilio
   c. If no: Wait for agent
3. Log result
4. Move to next contact
```

#### 2. Webhook Server (webhook_server.py)

**Responsibilities:**
- Listen on port 5000
- Handle Twilio callbacks
- Provide TwiML responses
- Track agent status
- Route calls to agents

**Endpoints:**
- `GET /status` - System status
- `POST /outbound-call` - Handle outbound call events
- `POST /connect-agent` - Connect call to agent
- `POST /agent-status` - Agent availability updates

#### 3. Agent Router (agent_router.py)

**Responsibilities:**
- Track agent availability
- Assign calls to agents
- Handle agent timeouts
- Implement waiting logic when all busy

**Logic:**
```python
if agent_available():
    assign_call_to_agent()
else:
    wait_for_agent_available()
```

#### 4. Voicemail Drop (voicemail_drop.py)

**Responsibilities:**
- Play pre-recorded voicemail
- Handle voicemail timing
- Log voicemail drops

#### 5. Ngrok

**Responsibilities:**
- Create public HTTPS tunnel
- Expose webhook server to internet
- Provide URL for Twilio callbacks

---

### Asterisk PBX Layer

**Purpose:** SIP server and call routing

#### PJSIP Endpoints

**Configuration:**
```ini
[101]
type=endpoint
transport=transport-tcp
auth=auth101
aors=aor101
context=internal
allow=ulaw,alaw

[auth101]
type=auth
auth_type=userpass
username=101
password=ChangeMe101!

[aor101]
type=aor
max_contacts=5
```

#### Dialplan

**Configuration:**
```ini
[internal]
exten => 101,1,Answer()
same => n,Dial(PJSIP/101,20)
same => n,Hangup()

exten => 102,1,Answer()
same => n,Dial(PJSIP/102,20)
same => n,Hangup()
```

#### Transports

**Configuration:**
```ini
[transport-tcp]
type=transport
protocol=tcp
bind=0.0.0.0:5060

[transport-udp]
type=transport
protocol=udp
bind=0.0.0.0:5060
```

---

### Twilio Layer

**Purpose:** Phone service provider

**Services Used:**
- **Outbound Calling:** Make calls to customers
- **SIP Trunk:** Connect to Asterisk
- **Webhooks:** Notify system of call events
- **TwiML:** Control call flow

---

## Data Flow

### Outbound Call Flow

```
1. User clicks "Start Calling"
   │
   ▼
2. Dialer reads contacts.csv
   │
   ▼
3. For each contact:
   │
   ├─→ Check agent availability (agent_router.py)
   │   │
   │   ├─→ Agent available?
   │   │   │
   │   │   ├─→ YES: Continue
   │   │   │
   │   │   └─→ NO: Wait for agent
   │   │
   │   ▼
   ├─→ Make call via Twilio API
   │   │
   │   ▼
   ├─→ Twilio dials customer
   │   │
   │   ├─→ Customer answers?
   │   │   │
   │   │   ├─→ YES: Twilio sends webhook to /outbound-call
   │   │   │   │
   │   │   │   ▼
   │   │   │   Webhook server returns TwiML:
   │   │   │   <Dial><Sip>sip:101@asterisk</Sip></Dial>
   │   │   │   │
   │   │   │   ▼
   │   │   │   Twilio connects to Asterisk
   │   │   │   │
   │   │   │   ▼
   │   │   │   Asterisk routes to extension 101
   │   │   │   │
   │   │   │   ▼
   │   │   │   Softphone rings
   │   │   │   │
   │   │   │   ▼
   │   │   │   Agent clicks "Answer"
   │   │   │   │
   │   │   │   ▼
   │   │   │   Conversation starts
   │   │   │   │
   │   │   │   ▼
   │   │   │   Agent clicks "Hangup"
   │   │   │   │
   │   │   │   ▼
   │   │   │   Call ends, agent marked available
   │   │   │
   │   │   └─→ NO: Twilio sends webhook
   │   │       │
   │   │       ▼
   │   │       Webhook server returns TwiML:
   │   │       <Play>voicemail.mp3</Play>
   │   │       │
   │   │       ▼
   │   │       Voicemail dropped
   │   │
   │   ▼
   └─→ Log result to call_results.json
       │
       ▼
4. Move to next contact
```

---

## Network Architecture

### Port Usage

| Port | Service | Protocol | Direction |
|------|---------|----------|-----------|
| 5000 | Webhook Server | HTTP | Inbound (from Twilio via ngrok) |
| 5060 | Asterisk SIP | TCP/UDP | Bidirectional (softphone ↔ Asterisk) |
| 4040 | Ngrok Dashboard | HTTP | Local only |

### IP Addresses

| Component | IP Address | Notes |
|-----------|------------|-------|
| Windows | 10.0.0.216 | WiFi adapter |
| WSL2 | 172.25.17.93 | Dynamic (changes on reboot) |
| Tailscale | 100.67.48.22 | Static (if using Tailscale) |

### Network Flow

```
Internet
   │
   │ HTTPS
   ▼
Ngrok Tunnel (https://xxx.ngrok-free.dev)
   │
   │ HTTP
   ▼
Webhook Server (localhost:5000)
   │
   │ Python API calls
   ▼
Twilio API
   │
   │ SIP
   ▼
Asterisk (WSL2:5060)
   │
   │ SIP (localhost)
   ▼
Softphone (Windows)
```

---

## File System Architecture

```
voip/smart_routing/
│
├── Core Application
│   ├── desktop_app.py              # Main GUI
│   ├── softphone.py                # Integrated softphone
│   └── config_writer.py            # Config management
│
├── Calling Engine
│   ├── dialer.py                   # Outbound dialer
│   ├── agent_router.py             # Agent routing
│   ├── webhook_server.py           # Twilio webhooks
│   └── voicemail_drop.py           # Voicemail handling
│
├── Configuration
│   ├── config.ini                  # Main config
│   ├── contacts.csv                # Contact list
│   └── voicemail.mp3               # Voicemail audio
│
├── Data
│   ├── call_results.json           # Call outcomes
│   └── smart_routing.log           # Activity log
│
├── Installation
│   ├── install_softphone.ps1       # Windows installer
│   ├── requirements_softphone.txt  # Python deps
│   └── fix_asterisk.sh             # Asterisk setup
│
├── Testing
│   ├── test_softphone_standalone.py
│   ├── test_simple.py
│   └── test_edge_case.py
│
└── Documentation
    ├── COMPLETE_SYSTEM_GUIDE.md    # This file
    ├── INTEGRATED_SOFTPHONE_README.md
    ├── SOFTPHONE_SETUP.md
    ├── QUICK_START_SOFTPHONE.md
    ├── QUICK_REFERENCE.md
    ├── SYSTEM_ARCHITECTURE.md
    ├── EDGE_CASE_HANDLING.md
    └── README.md
```

---

## Technology Stack

### Frontend
- **Python 3.7+**
- **Tkinter** - GUI framework
- **PyAudio** - Audio handling

### Backend
- **Python 3.7+**
- **Flask** - Webhook server
- **Requests** - HTTP client
- **Twilio SDK** - Twilio API

### Infrastructure
- **Asterisk 20** - PBX server
- **PJSIP** - SIP stack
- **Ngrok** - Tunneling
- **WSL2** - Linux subsystem

### External Services
- **Twilio** - Phone service
- **Ngrok** - Public tunnel

---

## Security Considerations

### Credentials Storage

**Current:** Stored in `config.ini` (plaintext)

**Recommendation:** Use environment variables or encrypted storage

### Network Security

**Current:** 
- Webhook exposed via ngrok (HTTPS)
- SIP traffic on localhost (unencrypted)

**Recommendation:**
- Use TLS for SIP (port 5061)
- Implement webhook authentication
- Use VPN for remote agents

### Access Control

**Current:** No authentication on webhook server

**Recommendation:**
- Add API key authentication
- Implement rate limiting
- Log all access attempts

---

## Scalability

### Current Capacity

- **Agents:** 2 simultaneous
- **Calls:** 2 concurrent
- **Contacts:** Unlimited (CSV)

### Scaling Options

#### Horizontal Scaling
- Add more agent endpoints (103, 104, etc.)
- Run multiple dialer instances
- Use load balancer for webhooks

#### Vertical Scaling
- Upgrade Asterisk server resources
- Optimize database queries
- Use Redis for agent state

#### Cloud Scaling
- Move Asterisk to cloud (AWS, Azure)
- Use managed SIP service
- Implement auto-scaling

---

## Monitoring & Logging

### Application Logs

**Location:** `smart_routing.log`

**Contents:**
- Campaign start/stop
- Call attempts
- Call outcomes
- Errors and warnings

### Asterisk Logs

**Location:** `/var/log/asterisk/full`

**Contents:**
- SIP registration
- Call routing
- Dialplan execution
- Errors

### Webhook Logs

**Location:** Console output / Activity Log

**Contents:**
- Incoming webhooks
- TwiML responses
- Agent assignments

---

## Disaster Recovery

### Backup Strategy

**Daily Backups:**
- `config.ini`
- `contacts.csv`
- `call_results.json`
- `smart_routing.log`

**Weekly Backups:**
- Asterisk configuration files
- Voicemail recordings

### Recovery Procedures

**If Asterisk crashes:**
```bash
wsl sudo systemctl restart asterisk
```

**If webhook server crashes:**
```
Dashboard → Stop Services → Start Services
```

**If softphone disconnects:**
```
Close softphone window → Launch Softphone again
```

---

## Performance Optimization

### Current Performance

- **Call setup time:** ~2-3 seconds
- **Agent response time:** <1 second
- **Voicemail drop time:** ~5 seconds

### Optimization Tips

1. **Reduce batch delay** in config.ini
2. **Use SSD** for faster file I/O
3. **Increase Asterisk threads** in asterisk.conf
4. **Use CDN** for voicemail files
5. **Implement connection pooling** for Twilio API

---

## Future Enhancements

### Planned Features

- [ ] Web-based dashboard
- [ ] Real-time analytics
- [ ] CRM integration
- [ ] SMS follow-up
- [ ] Call recording
- [ ] Speech analytics
- [ ] Multi-language support
- [ ] Mobile app for agents

### Technical Improvements

- [ ] Database backend (PostgreSQL)
- [ ] Message queue (RabbitMQ)
- [ ] Containerization (Docker)
- [ ] CI/CD pipeline
- [ ] Automated testing
- [ ] Performance monitoring
- [ ] Error tracking (Sentry)

---

**This architecture provides a solid foundation for a scalable, reliable outbound calling system!** 🏗️
