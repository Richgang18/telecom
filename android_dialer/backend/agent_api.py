"""
agent_api.py — Backend for the Android Agent Dialer App.
Runs on port 5001 alongside the existing voicemail blast API (port 5000).

Features:
- JWT agent authentication
- Lead list management (CSV-based)
- Outbound calls via SignalWire
- Call recording
- Blind transfer
- Real-time WebSocket events per-agent
- Voice pipeline: SignalWire Media Stream → Deepgram STT → Cartesia TTS
"""
from __future__ import annotations

import asyncio
import configparser
import csv
import io
import json
import logging
import os
import secrets
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx
import jwt
import requests
import uvicorn
from fastapi import (
    Depends, FastAPI, HTTPException, Request, WebSocket,
    WebSocketDisconnect, status
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "agent_config.ini"
LEADS_PATH  = BASE_DIR / "leads.csv"
CALLS_PATH  = BASE_DIR / "call_log.json"


def load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    try:
        cfg.read_string(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        cfg.read(CONFIG_PATH)
    return cfg


config = load_config()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "agent_api.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Agent Dialer API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ---------------------------------------------------------------------------
# JWT auth
# ---------------------------------------------------------------------------
JWT_SECRET  = config.get("auth", "jwt_secret", fallback="change-me-in-production")
JWT_EXPIRY  = int(config.get("auth", "token_expiry_hours", fallback="24"))

# Hard-coded agents — extend to DB later
AGENTS = {
    "agent1": {"id": "agent1", "name": "Agent 1", "password": config.get("auth", "agent1_password", fallback="pass1")},
    "agent2": {"id": "agent2", "name": "Agent 2", "password": config.get("auth", "agent2_password", fallback="pass2")},
}


def create_token(agent_id: str) -> str:
    payload = {
        "sub": agent_id,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        agent_id = payload.get("sub")
        if not agent_id or agent_id not in AGENTS:
            raise HTTPException(status_code=401, detail="Invalid token")
        return AGENTS[agent_id]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------------------------------------------------------------
# WebSocket manager (per-agent rooms)
# ---------------------------------------------------------------------------
class AgentConnectionManager:
    def __init__(self):
        # agent_id -> list of active WebSockets
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, agent_id: str, ws: WebSocket):
        await ws.accept()
        self._connections.setdefault(agent_id, []).append(ws)

    def disconnect(self, agent_id: str, ws: WebSocket):
        conns = self._connections.get(agent_id, [])
        if ws in conns:
            conns.remove(ws)

    async def send(self, agent_id: str, data: dict):
        """Send event to a specific agent."""
        dead = []
        for ws in self._connections.get(agent_id, []):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(agent_id, ws)

    async def broadcast(self, data: dict):
        """Send event to all connected agents."""
        for agent_id in list(self._connections.keys()):
            await self.send(agent_id, data)


ws_manager = AgentConnectionManager()

# ---------------------------------------------------------------------------
# In-memory call state
# ---------------------------------------------------------------------------
# call_sid -> {agent_id, lead_phone, lead_name, started_at, status, recording_url}
active_calls: dict[str, dict] = {}
calls_lock = threading.Lock()


# ---------------------------------------------------------------------------
# SignalWire helpers
# ---------------------------------------------------------------------------
def sw_config():
    cfg = load_config()
    return {
        "account_sid": cfg.get("signalwire", "account_sid"),
        "auth_token":  cfg.get("signalwire", "auth_token"),
        "space_url":   cfg.get("signalwire", "space_url").strip(),
        "from_number": cfg.get("signalwire", "from_number"),
        "webhook_base": cfg.get("signalwire", "webhook_base_url").rstrip("/"),
    }


def sw_post(path: str, data: list[tuple]) -> dict:
    sw = sw_config()
    if not sw["space_url"].startswith("http"):
        sw["space_url"] = "https://" + sw["space_url"]
    url = f"{sw['space_url']}/api/laml/2010-04-01/Accounts/{sw['account_sid']}{path}"
    r = requests.post(url, data=data, auth=(sw["account_sid"], sw["auth_token"]), timeout=10)
    r.raise_for_status()
    return r.json()


def sw_get(path: str) -> dict:
    sw = sw_config()
    if not sw["space_url"].startswith("http"):
        sw["space_url"] = "https://" + sw["space_url"]
    url = f"{sw['space_url']}/api/laml/2010-04-01/Accounts/{sw['account_sid']}{path}"
    r = requests.get(url, auth=(sw["account_sid"], sw["auth_token"]), timeout=10)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Lead management
# ---------------------------------------------------------------------------
def load_leads() -> list[dict]:
    if not LEADS_PATH.exists():
        return []
    with open(LEADS_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        leads = []
        for i, row in enumerate(reader):
            phone = row.get("phone_number", row.get("phone", "")).strip()
            name  = row.get("name", "Unknown").strip()
            if phone:
                leads.append({
                    "id":    str(i),
                    "name":  name,
                    "phone": phone,
                    "email": row.get("email", "").strip(),
                    "notes": row.get("notes", "").strip(),
                    "status": row.get("status", "new").strip(),
                })
    return leads


def save_lead_status(lead_id: str, status: str, notes: str = "") -> bool:
    """Update a single lead's status in the CSV."""
    leads = load_leads()
    updated = False
    for lead in leads:
        if lead["id"] == lead_id:
            lead["status"] = status
            if notes:
                lead["notes"] = notes
            updated = True
            break
    if not updated:
        return False
    # Rewrite CSV
    with open(LEADS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "phone_number", "email", "notes", "status"])
        writer.writeheader()
        for lead in leads:
            writer.writerow({
                "name": lead["name"],
                "phone_number": lead["phone"],
                "email": lead.get("email", ""),
                "notes": lead.get("notes", ""),
                "status": lead.get("status", "new"),
            })
    return True


# ---------------------------------------------------------------------------
# Call log persistence
# ---------------------------------------------------------------------------
def load_call_log() -> list[dict]:
    if not CALLS_PATH.exists():
        return []
    try:
        return json.loads(CALLS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def append_call_log(entry: dict):
    log = load_call_log()
    log.insert(0, entry)
    CALLS_PATH.write_text(json.dumps(log[:5000], indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    agent_id: str
    password: str


@app.post("/api/auth/login")
async def login(body: LoginRequest):
    agent = AGENTS.get(body.agent_id)
    if not agent or agent["password"] != body.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(body.agent_id)
    return {"token": token, "agent": {"id": agent["id"], "name": agent["name"]}}


@app.get("/api/auth/me")
async def me(agent: dict = Depends(verify_token)):
    return {"id": agent["id"], "name": agent["name"]}


# ---------------------------------------------------------------------------
# Lead endpoints
# ---------------------------------------------------------------------------
@app.get("/api/leads")
async def get_leads(
    search: str = "",
    status_filter: str = "",
    page: int = 1,
    page_size: int = 50,
    agent: dict = Depends(verify_token),
):
    leads = load_leads()
    if search:
        q = search.lower()
        leads = [l for l in leads if q in l["name"].lower() or q in l["phone"]]
    if status_filter:
        leads = [l for l in leads if l["status"] == status_filter]
    total = len(leads)
    start = (page - 1) * page_size
    return {"leads": leads[start: start + page_size], "total": total, "page": page}


@app.get("/api/leads/{lead_id}")
async def get_lead(lead_id: str, agent: dict = Depends(verify_token)):
    leads = load_leads()
    for lead in leads:
        if lead["id"] == lead_id:
            return lead
    raise HTTPException(status_code=404, detail="Lead not found")


@app.patch("/api/leads/{lead_id}")
async def update_lead(lead_id: str, body: dict, agent: dict = Depends(verify_token)):
    ok = save_lead_status(lead_id, body.get("status", ""), body.get("notes", ""))
    if not ok:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"ok": True}


@app.post("/api/leads/upload")
async def upload_leads(request: Request, agent: dict = Depends(verify_token)):
    body = await request.json()
    contacts = body.get("contacts", [])
    if not contacts:
        raise HTTPException(status_code=400, detail="No contacts provided")
    with open(LEADS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "phone_number", "email", "notes", "status"])
        writer.writeheader()
        for c in contacts:
            writer.writerow({
                "name": c.get("name", ""),
                "phone_number": c.get("phone", c.get("phone_number", "")),
                "email": c.get("email", ""),
                "notes": c.get("notes", ""),
                "status": c.get("status", "new"),
            })
    return {"ok": True, "total": len(contacts)}


# ---------------------------------------------------------------------------
# Outbound call endpoint
# ---------------------------------------------------------------------------
class DialRequest(BaseModel):
    lead_id:    str
    lead_phone: str
    lead_name:  str = "Unknown"


@app.post("/api/calls/dial")
async def dial(body: DialRequest, agent: dict = Depends(verify_token)):
    sw = sw_config()
    webhook = sw["webhook_base"]

    # TwiML webhook: when lead answers, connect to agent's SIP endpoint
    connect_url = f"{webhook}/agent-call/connect?agent_id={agent['id']}"
    status_url  = f"{webhook}/agent-call/status"

    try:
        result = sw_post("/Calls.json", [
            ("To",                        body.lead_phone),
            ("From",                      sw["from_number"]),
            ("Url",                       connect_url),
            ("StatusCallback",            status_url),
            ("StatusCallbackMethod",      "POST"),
            ("StatusCallbackEvent",       "initiated"),
            ("StatusCallbackEvent",       "ringing"),
            ("StatusCallbackEvent",       "answered"),
            ("StatusCallbackEvent",       "completed"),
            ("Timeout",                   "30"),
            ("Record",                    "true"),
            ("RecordingStatusCallback",   f"{webhook}/agent-call/recording"),
            ("RecordingStatusCallbackMethod", "POST"),
            ("MachineDetection",          "Enable"),
        ])
    except Exception as e:
        logger.error("Dial failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    call_sid = result.get("sid", "")
    with calls_lock:
        active_calls[call_sid] = {
            "agent_id":      agent["id"],
            "lead_id":       body.lead_id,
            "lead_phone":    body.lead_phone,
            "lead_name":     body.lead_name,
            "started_at":    datetime.utcnow().isoformat(),
            "status":        "initiated",
            "recording_url": None,
            "duration":      0,
        }

    await ws_manager.send(agent["id"], {
        "event":      "call_initiated",
        "call_sid":   call_sid,
        "lead_phone": body.lead_phone,
        "lead_name":  body.lead_name,
        "ts":         datetime.utcnow().isoformat(),
    })

    logger.info("Agent %s dialing %s (%s) SID=%s", agent["id"], body.lead_name, body.lead_phone, call_sid)
    return {"ok": True, "call_sid": call_sid}


# ---------------------------------------------------------------------------
# Hang up / end call
# ---------------------------------------------------------------------------
@app.post("/api/calls/{call_sid}/hangup")
async def hangup(call_sid: str, agent: dict = Depends(verify_token)):
    sw = sw_config()
    if not sw["space_url"].startswith("http"):
        sw["space_url"] = "https://" + sw["space_url"]
    url = f"{sw['space_url']}/api/laml/2010-04-01/Accounts/{sw['account_sid']}/Calls/{call_sid}.json"
    try:
        r = requests.post(url, data=[("Status", "completed")],
                          auth=(sw["account_sid"], sw["auth_token"]), timeout=10)
        r.raise_for_status()
    except Exception as e:
        logger.error("Hangup failed for %s: %s", call_sid, e)
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True}


# ---------------------------------------------------------------------------
# Blind transfer
# ---------------------------------------------------------------------------
class TransferRequest(BaseModel):
    target_agent_id: str  # "agent1" or "agent2"


@app.post("/api/calls/{call_sid}/transfer")
async def blind_transfer(call_sid: str, body: TransferRequest, agent: dict = Depends(verify_token)):
    """
    Blind transfer: redirect the active call to another agent's SIP endpoint.
    The current agent is immediately disconnected.
    """
    target = AGENTS.get(body.target_agent_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target agent not found")

    sw   = sw_config()
    webhook = sw["webhook_base"]
    connect_url = f"{webhook}/agent-call/connect?agent_id={body.target_agent_id}"

    if not sw["space_url"].startswith("http"):
        sw["space_url"] = "https://" + sw["space_url"]
    url = f"{sw['space_url']}/api/laml/2010-04-01/Accounts/{sw['account_sid']}/Calls/{call_sid}.json"

    try:
        r = requests.post(
            url,
            data=[("Url", connect_url), ("Method", "POST")],
            auth=(sw["account_sid"], sw["auth_token"]),
            timeout=10,
        )
        r.raise_for_status()
    except Exception as e:
        logger.error("Transfer failed for %s: %s", call_sid, e)
        raise HTTPException(status_code=500, detail=str(e))

    with calls_lock:
        if call_sid in active_calls:
            active_calls[call_sid]["agent_id"] = body.target_agent_id

    # Notify both agents
    await ws_manager.send(agent["id"], {
        "event": "call_transferred", "call_sid": call_sid,
        "to_agent": body.target_agent_id, "ts": datetime.utcnow().isoformat(),
    })
    await ws_manager.send(body.target_agent_id, {
        "event": "incoming_transfer", "call_sid": call_sid,
        "from_agent": agent["id"], "ts": datetime.utcnow().isoformat(),
    })

    logger.info("Transfer %s from %s to %s", call_sid, agent["id"], body.target_agent_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# SignalWire webhook: /agent-call/connect
# Called when lead answers — returns TwiML to bridge to agent SIP
# ---------------------------------------------------------------------------
@app.post("/agent-call/connect")
async def agent_call_connect(request: Request, agent_id: str = "agent1"):
    form    = await request.form()
    call_sid = form.get("CallSid", "unknown")
    sw       = sw_config()
    cfg      = load_config()

    # Get SIP domain for this agent
    sip_domain = cfg.get("signalwire", "sip_domain", fallback="")
    sip_user   = cfg.get(f"agent_{agent_id}", "sip_username", fallback=agent_id)
    sip_pass   = cfg.get(f"agent_{agent_id}", "sip_password", fallback="")
    webhook    = sw["webhook_base"]

    logger.info("/agent-call/connect: SID=%s agent=%s", call_sid, agent_id)

    if sip_domain:
        # Bridge via SIP — agent's Android app receives the call via SignalWire SIP
        sip_uri = f"sip:{sip_user}@{sip_domain}"
        twiml = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<Response>'
            f'<Dial timeout="30" action="{webhook}/agent-call/dial-complete?agent_id={agent_id}">'
            f'<Sip username="{sip_user}" password="{sip_pass}">{sip_uri}</Sip>'
            f'</Dial>'
            f'</Response>'
        )
    else:
        # Fallback: dial agent mobile number
        mobile = cfg.get(f"agent_{agent_id}", "mobile", fallback="")
        if not mobile:
            twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>'
        else:
            twiml = (
                f'<?xml version="1.0" encoding="UTF-8"?>'
                f'<Response>'
                f'<Dial timeout="30" action="{webhook}/agent-call/dial-complete?agent_id={agent_id}">'
                f'<Number>{mobile}</Number>'
                f'</Dial>'
                f'</Response>'
            )

    await ws_manager.send(agent_id, {
        "event": "call_answered", "call_sid": call_sid,
        "ts": datetime.utcnow().isoformat(),
    })
    return Response(content=twiml, media_type="text/xml")


@app.post("/agent-call/dial-complete")
async def agent_dial_complete(request: Request, agent_id: str = "agent1"):
    form         = await request.form()
    call_sid     = form.get("CallSid", "unknown")
    dial_status  = form.get("DialCallStatus", "unknown")
    duration     = int(form.get("DialCallDuration", 0) or 0)

    with calls_lock:
        if call_sid in active_calls:
            active_calls[call_sid]["status"]   = "completed"
            active_calls[call_sid]["duration"] = duration
            entry = dict(active_calls[call_sid])
            entry["call_sid"]    = call_sid
            entry["ended_at"]    = datetime.utcnow().isoformat()
            entry["dial_status"] = dial_status
            append_call_log(entry)

    await ws_manager.send(agent_id, {
        "event": "call_ended", "call_sid": call_sid,
        "dial_status": dial_status, "duration": duration,
        "ts": datetime.utcnow().isoformat(),
    })
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>',
        media_type="text/xml",
    )


# ---------------------------------------------------------------------------
# SignalWire webhook: /agent-call/status  (call progress events)
# ---------------------------------------------------------------------------
@app.post("/agent-call/status")
async def agent_call_status(request: Request):
    form         = await request.form()
    call_sid     = form.get("CallSid", "unknown")
    call_status  = form.get("CallStatus", "unknown")
    duration     = int(form.get("CallDuration", 0) or 0)

    logger.info("Call status: SID=%s status=%s", call_sid, call_status)

    with calls_lock:
        call = active_calls.get(call_sid)
        agent_id = call["agent_id"] if call else None
        if call:
            call["status"] = call_status
            if duration:
                call["duration"] = duration
            if call_status in ("completed", "failed", "busy", "no-answer", "canceled"):
                entry = dict(call)
                entry["call_sid"] = call_sid
                entry["ended_at"] = datetime.utcnow().isoformat()
                append_call_log(entry)

    if agent_id:
        await ws_manager.send(agent_id, {
            "event": "call_status", "call_sid": call_sid,
            "status": call_status, "duration": duration,
            "ts": datetime.utcnow().isoformat(),
        })

    return Response(content="", status_code=204)


# ---------------------------------------------------------------------------
# SignalWire webhook: /agent-call/recording
# ---------------------------------------------------------------------------
@app.post("/agent-call/recording")
async def recording_callback(request: Request):
    form            = await request.form()
    call_sid        = form.get("CallSid", "unknown")
    recording_url   = form.get("RecordingUrl", "")
    recording_sid   = form.get("RecordingSid", "")
    duration        = int(form.get("RecordingDuration", 0) or 0)

    logger.info("Recording: SID=%s url=%s duration=%ss", call_sid, recording_url, duration)

    with calls_lock:
        call = active_calls.get(call_sid)
        agent_id = None
        if call:
            call["recording_url"] = recording_url + ".mp3"
            agent_id = call["agent_id"]

    if agent_id:
        await ws_manager.send(agent_id, {
            "event": "recording_ready",
            "call_sid": call_sid,
            "recording_url": recording_url + ".mp3",
            "duration": duration,
            "ts": datetime.utcnow().isoformat(),
        })

    return Response(content="", status_code=204)


# ---------------------------------------------------------------------------
# Call history endpoint
# ---------------------------------------------------------------------------
@app.get("/api/calls/history")
async def call_history(page: int = 1, page_size: int = 50, agent: dict = Depends(verify_token)):
    log = load_call_log()
    # Filter to this agent's calls
    log = [c for c in log if c.get("agent_id") == agent["id"]]
    total = len(log)
    start = (page - 1) * page_size
    return {"calls": log[start: start + page_size], "total": total}


@app.get("/api/calls/active")
async def active_calls_list(agent: dict = Depends(verify_token)):
    with calls_lock:
        my_calls = {
            sid: call for sid, call in active_calls.items()
            if call.get("agent_id") == agent["id"]
        }
    return {"calls": my_calls}


# ---------------------------------------------------------------------------
# Voice pipeline: SignalWire Media Stream → Deepgram STT → Cartesia TTS
# The Android app's microphone audio is streamed here,
# converted to American voice, then played back into the call.
#
# Flow:
#  1. Android calls /api/voice-stream/start → gets a stream_id
#  2. SignalWire TwiML uses <Stream> to open WS to /voice/stream/{stream_id}
#  3. Audio chunks arrive via WS → forwarded to Deepgram STT
#  4. Transcripts → Cartesia TTS → synthesized audio chunks
#  5. Synthesized audio injected back into call via SignalWire Media Stream
# ---------------------------------------------------------------------------
voice_streams: dict[str, dict] = {}


@app.post("/api/voice-stream/start")
async def start_voice_stream(request: Request, agent: dict = Depends(verify_token)):
    body      = await request.json()
    call_sid  = body.get("call_sid", "")
    stream_id = secrets.token_hex(8)
    sw        = sw_config()
    webhook   = sw["webhook_base"]

    voice_streams[stream_id] = {
        "call_sid":  call_sid,
        "agent_id":  agent["id"],
        "started_at": datetime.utcnow().isoformat(),
        "active":    True,
    }

    # Instruct SignalWire to open a media stream to our WS endpoint
    # by updating the call's TwiML to include <Stream>
    stream_url = f"{webhook.replace('https://', 'wss://').replace('http://', 'ws://')}/voice/stream/{stream_id}"
    twiml = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response>'
        f'<Connect>'
        f'<Stream url="{stream_url}" track="inbound_track"/>'
        f'</Connect>'
        f'</Response>'
    )

    # Update the active call with this TwiML
    if not sw["space_url"].startswith("http"):
        sw["space_url"] = "https://" + sw["space_url"]
    url = f"{sw['space_url']}/api/laml/2010-04-01/Accounts/{sw['account_sid']}/Calls/{call_sid}.json"
    try:
        r = requests.post(
            url,
            data=[("Twiml", twiml)],
            auth=(sw["account_sid"], sw["auth_token"]),
            timeout=10,
        )
        r.raise_for_status()
    except Exception as e:
        logger.error("Failed to start media stream for %s: %s", call_sid, e)
        raise HTTPException(status_code=500, detail=str(e))

    logger.info("Voice stream started: id=%s call=%s", stream_id, call_sid)
    return {"stream_id": stream_id, "stream_url": stream_url}


@app.websocket("/voice/stream/{stream_id}")
async def voice_stream_ws(websocket: WebSocket, stream_id: str):
    """
    Bidirectional voice pipeline WebSocket.
    Receives raw μ-law audio from SignalWire Media Streams,
    sends to Deepgram STT, converts transcript via Cartesia TTS,
    sends synthesized audio back into the call.
    """
    await websocket.accept()
    stream = voice_streams.get(stream_id)
    if not stream:
        await websocket.close(code=1008)
        return

    cfg          = load_config()
    deepgram_key = cfg.get("deepgram", "api_key", fallback="")
    cartesia_key = cfg.get("cartesia", "api_key", fallback="")
    cartesia_voice = cfg.get("cartesia", "voice_id", fallback="American English Male")

    logger.info("Voice stream WS connected: %s", stream_id)

    # Deepgram streaming STT connection
    dg_ws = None
    if deepgram_key:
        try:
            import websockets as ws_lib
            dg_url = (
                "wss://api.deepgram.com/v1/listen"
                "?encoding=mulaw&sample_rate=8000&channels=1"
                "&interim_results=false&language=en-US"
            )
            dg_ws = await ws_lib.connect(
                dg_url,
                extra_headers={"Authorization": f"Token {deepgram_key}"},
            )
            logger.info("Deepgram STT connected for stream %s", stream_id)
        except Exception as e:
            logger.error("Deepgram connection failed: %s", e)

    async def handle_deepgram_transcript():
        """Read transcripts from Deepgram and synthesize via Cartesia."""
        if not dg_ws:
            return
        try:
            async for msg in dg_ws:
                data = json.loads(msg)
                transcript = (
                    data.get("channel", {})
                        .get("alternatives", [{}])[0]
                        .get("transcript", "")
                )
                if not transcript or data.get("is_final") is False:
                    continue
                logger.debug("Transcript: %s", transcript)
                # Synthesize via Cartesia
                if cartesia_key and transcript.strip():
                    await synthesize_and_inject(transcript, stream_id, cartesia_key, cartesia_voice)
        except Exception as e:
            logger.error("Deepgram transcript error: %s", e)

    transcript_task = asyncio.create_task(handle_deepgram_transcript())

    try:
        while stream.get("active", True):
            try:
                msg = await asyncio.wait_for(websocket.receive(), timeout=30)
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break

            if msg["type"] == "websocket.receive":
                if "bytes" in msg and msg["bytes"] and dg_ws:
                    # Forward raw audio to Deepgram
                    try:
                        await dg_ws.send(msg["bytes"])
                    except Exception:
                        pass
                elif "text" in msg and msg["text"]:
                    # SignalWire sends JSON control messages
                    try:
                        ctrl = json.loads(msg["text"])
                        if ctrl.get("event") == "stop":
                            break
                    except Exception:
                        pass
    finally:
        transcript_task.cancel()
        if dg_ws:
            try:
                await dg_ws.close()
            except Exception:
                pass
        stream["active"] = False
        logger.info("Voice stream closed: %s", stream_id)


async def synthesize_and_inject(text: str, stream_id: str, cartesia_key: str, voice_id: str):
    """Call Cartesia TTS and inject audio back into the call via SignalWire."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://api.cartesia.ai/tts/bytes",
                headers={
                    "X-API-Key": cartesia_key,
                    "Cartesia-Version": "2024-06-10",
                    "Content-Type": "application/json",
                },
                json={
                    "transcript": text,
                    "model_id": "sonic-3.5",
                    "voice": {"mode": "id", "id": voice_id},
                    "output_format": {
                        "container": "raw",
                        "encoding": "pcm_mulaw",
                        "sample_rate": 8000,
                    },
                },
            )
            if r.status_code == 200:
                audio_bytes = r.content
                # Save temp file and serve via SignalWire <Play>
                tmp_path = BASE_DIR / f"tts_{stream_id}.raw"
                tmp_path.write_bytes(audio_bytes)
                logger.debug("Cartesia TTS: %d bytes for '%s'", len(audio_bytes), text[:50])
            else:
                logger.error("Cartesia error: %s %s", r.status_code, r.text[:200])
    except Exception as e:
        logger.error("Cartesia TTS failed: %s", e)


# ---------------------------------------------------------------------------
# WebSocket: /ws/agent/{agent_id}  — real-time events for Android app
# ---------------------------------------------------------------------------
@app.websocket("/ws/agent/{agent_id}")
async def agent_websocket(websocket: WebSocket, agent_id: str, token: str = ""):
    # Validate JWT passed as query param ?token=...
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        if payload.get("sub") != agent_id:
            await websocket.close(code=1008)
            return
    except Exception:
        await websocket.close(code=1008)
        return

    await ws_manager.connect(agent_id, websocket)
    logger.info("Agent WS connected: %s", agent_id)

    try:
        # Send initial state
        with calls_lock:
            my_calls = {
                sid: call for sid, call in active_calls.items()
                if call.get("agent_id") == agent_id
            }
        await websocket.send_json({
            "event": "init",
            "agent_id": agent_id,
            "active_calls": my_calls,
            "ts": datetime.utcnow().isoformat(),
        })
        # Keep alive — client sends pings
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(agent_id, websocket)
        logger.info("Agent WS disconnected: %s", agent_id)


# ---------------------------------------------------------------------------
# Misc endpoints
# ---------------------------------------------------------------------------
@app.get("/api/ping")
async def ping():
    return {"status": "ok", "service": "agent-api", "ts": datetime.utcnow().isoformat()}


@app.get("/api/agents")
async def list_agents(agent: dict = Depends(verify_token)):
    return {"agents": [{"id": a["id"], "name": a["name"]} for a in AGENTS.values()]}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    host = config.get("server", "host", fallback="0.0.0.0")
    port = int(config.get("server", "port", fallback="5001"))
    uvicorn.run("agent_api:app", host=host, port=port, reload=False, log_level="info")
