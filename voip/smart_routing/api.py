"""
api.py — FastAPI backend for the Smart Outbound Dialer
REST + WebSocket API consumed by the Next.js UI.
"""
from __future__ import annotations

import asyncio
import configparser
import json
import logging
import mimetypes
import subprocess
import threading
import urllib.request
from datetime import datetime
from pathlib import Path

campaign_lock = threading.Lock()

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

from agent_router import AgentRouter
from voicemail_drop import generate_no_answer_twiml

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.ini"


def load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH)
    return cfg


config = load_config()

logging.basicConfig(
    level=getattr(logging, config["logging"].get("log_level", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / config["logging"].get("log_file", "smart_routing.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Smart Dialer API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = AgentRouter(config)

# ---------------------------------------------------------------------------
# WebSocket manager
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
        # Never raise — broadcast is fire-and-forget


manager = ConnectionManager()
call_log: list[dict] = []
dialer_process: subprocess.Popen | None = None
ngrok_process: subprocess.Popen | None = None

# Track when each agent was marked busy (for timeout-based release)
agent_busy_since: dict[str, datetime] = {}

# Track calls already connected to an agent (prevents double-bridging from async AMD)
connected_calls: set[str] = set()

# ---------------------------------------------------------------------------
# Campaign tracking
# ---------------------------------------------------------------------------
CAMPAIGNS_DIR = BASE_DIR / "campaigns"
CAMPAIGNS_DIR.mkdir(exist_ok=True)

current_campaign: dict | None = None


def _campaign_path(campaign_id: str) -> Path:
    return CAMPAIGNS_DIR / f"{campaign_id}.json"


def _save_campaign(campaign: dict) -> None:
    """Persist campaign dict to disk as JSON."""
    try:
        with open(_campaign_path(campaign["id"]), "w", encoding="utf-8") as f:
            json.dump(campaign, f, indent=2, default=str)
    except Exception as e:
        logger.error("Failed to save campaign %s: %s", campaign.get("id"), e)


def _load_campaign(campaign_id: str) -> dict | None:
    """Load a campaign from disk. Returns None if not found."""
    path = _campaign_path(campaign_id)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to load campaign %s: %s", campaign_id, e)
        return None


def _list_campaigns() -> list[dict]:
    """Return summary list of all campaigns, newest first."""
    summaries = []
    for p in sorted(CAMPAIGNS_DIR.glob("*.json"), reverse=True):
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            # Auto-fix stuck "running" campaigns older than 1 hour
            if data.get("status") == "running" and data.get("ended_at") is None:
                try:
                    started = datetime.fromisoformat(data["started_at"])
                    if (datetime.utcnow() - started).total_seconds() > 3600:
                        data["status"] = "completed"
                        data["ended_at"] = data["started_at"]  # approximate
                        with open(p, "w", encoding="utf-8") as fw:
                            json.dump(data, fw, indent=2)
                except Exception:
                    pass
            # Return summary without the full calls list
            summaries.append({k: v for k, v in data.items() if k != "calls"})
        except Exception:
            pass
    return summaries


def _new_campaign(total_contacts: int) -> dict:
    """Create a fresh campaign record."""
    now = datetime.utcnow()
    campaign_id = f"campaign_{now.strftime('%Y%m%d_%H%M%S')}"
    return {
        "id": campaign_id,
        "started_at": now.isoformat(),
        "ended_at": None,
        "status": "running",
        "total_contacts": total_contacts,
        "dialed": 0,
        "answered": 0,
        "voicemail_dropped": 0,
        "no_answer": 0,
        "failed": 0,
        "calls": [],
    }


def _update_campaign_call(
    campaign: dict,
    call_sid: str,
    name: str,
    phone: str,
    status: str,
    answered_by: str = "",
    duration: int = 0,
) -> None:
    """Add or update a call entry in the campaign record. Must be called with campaign_lock held."""
    # Check if call already exists
    for call in campaign["calls"]:
        if call["call_sid"] == call_sid:
            call["status"] = status
            if answered_by:
                call["answered_by"] = answered_by
            if duration:
                call["duration"] = duration
            return
    # New call entry
    campaign["calls"].append({
        "call_sid": call_sid,
        "name": name,
        "phone": phone,
        "status": status,
        "answered_by": answered_by,
        "timestamp": datetime.utcnow().isoformat(),
        "duration": duration,
    })
    campaign["dialed"] = len(campaign["calls"])
    # Recount stats
    campaign["answered"] = sum(1 for c in campaign["calls"] if c["status"] == "answered")
    campaign["voicemail_dropped"] = sum(1 for c in campaign["calls"] if c["status"] == "voicemail_dropped")
    campaign["no_answer"] = sum(1 for c in campaign["calls"] if c["status"] == "no_answer")
    campaign["failed"] = sum(1 for c in campaign["calls"] if c["status"] == "failed")


def _reload_config():
    """Reload config.ini values only. Does NOT reset the router/agent state."""
    global config
    config = load_config()


async def _stuck_call_watchdog():
    """
    Background task: auto-release agents stuck busy for longer than
    agent_timeout + 60s safety buffer.
    NOTE: Does NOT reload config/router — that would reset agent state.
    """
    while True:
        await asyncio.sleep(30)
        try:
            max_busy = int(config["agents"].get("agent_timeout", "20")) + 90
            now = datetime.utcnow()
            status = router.status()
            for key, info in status.items():
                if info.get("status") == "busy" and key in agent_busy_since:
                    elapsed = (now - agent_busy_since[key]).total_seconds()
                    if elapsed > max_busy:
                        logger.warning(
                            "Stuck call detected: agent %s busy for %.0fs — force releasing",
                            key, elapsed
                        )
                        try:
                            router.mark_available_by_index(int(key))
                        except (ValueError, AttributeError):
                            router.mark_available(key)
                        agent_busy_since.pop(key, None)
                        await manager.broadcast({
                            "event": "agent_available",
                            "agent": key,
                            "reason": "stuck_call_timeout",
                            "ts": now.isoformat()
                        })
        except Exception as e:
            logger.error("Watchdog error: %s", e)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(_stuck_call_watchdog())


def _get_ngrok_url() -> str:
    """Return current ngrok tunnel URL or empty string. Non-blocking."""
    try:
        with urllib.request.urlopen("http://localhost:4040/api/tunnels", timeout=1) as r:
            data = json.loads(r.read())
        tunnels = data.get("tunnels", [])
        if tunnels:
            return tunnels[0]["public_url"]
    except Exception:
        pass
    return ""


# Cache the ngrok URL so we don't block on every call
_cached_ngrok_url: str = ""

def _get_webhook_base() -> str:
    """Get webhook base URL — uses cached ngrok URL or config fallback. Never blocks."""
    global _cached_ngrok_url
    # Try to get live URL (fast, 1s timeout)
    live = _get_ngrok_url()
    if live:
        _cached_ngrok_url = live
        return live.rstrip("/")
    # Fall back to cached or config
    if _cached_ngrok_url:
        return _cached_ngrok_url.rstrip("/")
    return config["twilio"].get("webhook_base_url", "").rstrip("/")


@app.get("/ping")
async def ping():
    """Simple test endpoint — verify ngrok can reach the API."""
    live_url = _get_ngrok_url()
    _reload_config()
    vm_file = BASE_DIR / config["voicemail"].get("voicemail_file", "voicemail.mp3")
    return {
        "status": "ok",
        "live_ngrok_url": live_url,
        "config_webhook_url": config["twilio"].get("webhook_base_url", ""),
        "agent_mobile": config["agents"].get("agent_mobile_numbers", ""),
        "agent_mode": config["agents"].get("agent_mode", ""),
        "agents": router.status(),
        "voicemail_file": str(vm_file),
        "voicemail_exists": vm_file.exists(),
        "voicemail_size_bytes": vm_file.stat().st_size if vm_file.exists() else 0,
        "voicemail_url": f"{live_url}/voicemail-audio" if live_url else "ngrok not running",
    }


# ---------------------------------------------------------------------------
# Twilio Webhook endpoints
# ---------------------------------------------------------------------------

@app.post("/connect")
async def connect_call(request: Request):
    # Log EVERYTHING from Twilio immediately before any processing
    try:
        body = await request.body()
        logger.info("=== /connect HIT === raw body: %s", body.decode("utf-8", errors="replace"))
    except Exception as raw_err:
        logger.error("=== /connect HIT but failed to read body: %s", raw_err)

    try:
        form = await request.form()
    except Exception as form_err:
        logger.error("/connect form parse error: %s", form_err)
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>',
            media_type="text/xml"
        )

    call_sid    = form.get("CallSid", "unknown")
    answered_by = form.get("AnsweredBy", "unknown")
    call_status = form.get("CallStatus", "unknown")

    logger.info("/connect: SID=%s answered_by=%s call_status=%s", call_sid, answered_by, call_status)

    try:
        # Machine detected in LIVE AGENT mode only — skip for voicemail_blast
        _reload_config()
        agent_mode = config["agents"].get("agent_mode", "softphone")
        logger.info("Agent mode: %s", agent_mode)

        if agent_mode != "voicemail_blast" and answered_by in (
            "machine_start", "machine_end", "machine_end_beep",
            "machine_end_silence", "machine_end_other", "fax"
        ):
            logger.info("AMD machine detected (%s) for call %s — dropping voicemail", answered_by, call_sid)
            if call_sid in connected_calls:
                return Response(
                    content='<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>',
                    media_type="text/xml"
                )
            try:
                await manager.broadcast({"event": "amd_machine", "call_sid": call_sid, "ts": datetime.utcnow().isoformat()})
            except Exception:
                pass
            return Response(content=generate_no_answer_twiml(config), media_type="text/xml")

        # ── Voicemail blast mode — play MP3 to everyone, no live agent ──
        if agent_mode == "voicemail_blast":
            webhook_base = config["twilio"].get("webhook_base_url", "").rstrip("/")
            logger.info("Voicemail blast: playing voicemail to call %s (answered_by=%s)", call_sid, answered_by)

            # Play voicemail for ALL answer types:
            # - human / unknown = person answered, play message directly
            # - machine_end_beep = voicemail beep detected, play after beep
            # - machine_end_silence / machine_end_other = play anyway
            if answered_by == "machine_start":
                # AMD still detecting — wait, don't play yet (async callback will fire again)
                logger.info("AMD still detecting for call %s — waiting for machine_end callback", call_sid)
                return Response(
                    content='<?xml version="1.0" encoding="UTF-8"?><Response><Pause length="30"/></Response>',
                    media_type="text/xml"
                )

            # For human answers add 1s pause, for machine answers no pause (beep already happened)
            pause = "1" if answered_by in ("human", "unknown") else "0"

            twiml = (
                f'<?xml version="1.0" encoding="UTF-8"?>'
                f'<Response>'
                f'<Pause length="{pause}"/>'
                f'<Play>{webhook_base}/voicemail-audio</Play>'
                f'<Hangup/>'
                f'</Response>'
            )
            logger.info("Voicemail TwiML: %s", twiml)
            try:
                await manager.broadcast({
                    "event": "voicemail_dropped",
                    "call_sid": call_sid,
                    "answered_by": answered_by,
                    "ts": datetime.utcnow().isoformat()
                })
            except Exception:
                pass
            # Record voicemail drop in campaign
            with campaign_lock:
                if current_campaign is not None:
                    _update_campaign_call(
                        current_campaign,
                        call_sid=call_sid,
                        name="",
                        phone=form.get("To", ""),
                        status="voicemail_dropped",
                        answered_by=answered_by,
                    )
                    _save_campaign(current_campaign)
            return Response(content=twiml, media_type="text/xml")

        if agent_mode == "mobile":
            agent_index = router.get_available_agent_index()
            logger.info("Available agent index: %s", agent_index)

            if agent_index is None:
                logger.warning("No agents available for call %s", call_sid)
                await manager.broadcast({"event": "no_agent", "call_sid": call_sid, "ts": datetime.utcnow().isoformat()})
                return Response(content=router.generate_busy_twiml(), media_type="text/xml")

            mobile_numbers_raw = config["agents"].get("agent_mobile_numbers", "")
            mobile_numbers = [n.strip() for n in mobile_numbers_raw.split(",")]
            logger.info("Mobile numbers configured: %s", mobile_numbers)

            if agent_index >= len(mobile_numbers) or not mobile_numbers[agent_index]:
                logger.error("No mobile number for agent index %d (configured: %s)", agent_index, mobile_numbers_raw)
                return Response(content=generate_no_answer_twiml(config), media_type="text/xml")

            mobile  = mobile_numbers[agent_index]
            timeout = int(config["agents"].get("agent_timeout", "20"))

            router.mark_busy_by_index(agent_index, call_sid)
            print("DEBUG1: mark_busy done", flush=True)
            agent_busy_since[str(agent_index)] = datetime.utcnow()
            print("DEBUG2: agent_busy_since done", flush=True)
            connected_calls.add(call_sid)
            print("DEBUG3: connected_calls done", flush=True)

            # Use config value directly — never block the event loop checking ngrok
            webhook_base = config["twilio"].get("webhook_base_url", "").rstrip("/")
            print(f"DEBUG4: webhook_base={webhook_base}", flush=True)

            logger.info("BRIDGING: call=%s mobile=%s webhook=%s timeout=%s",
                        call_sid, mobile, webhook_base, timeout)
            print("DEBUG5: about to build twiml", flush=True)

            twiml = (
                f'<?xml version="1.0" encoding="UTF-8"?>'
                f'<Response>'
                f'<Dial timeout="{timeout}" action="{webhook_base}/agent-complete?agent={agent_index}">'
                f'<Number>{mobile}</Number>'
                f'</Dial>'
                f'<Play>{webhook_base}/voicemail-audio</Play>'
                f'</Response>'
            )
            logger.info("TwiML response: %s", twiml)

            # Broadcast non-blocking — never let this crash the response
            try:
                await manager.broadcast({
                    "event": "call_connected", "call_sid": call_sid,
                    "agent": agent_index, "mobile": mobile,
                    "ts": datetime.utcnow().isoformat()
                })
            except Exception as broadcast_err:
                logger.warning("Broadcast failed (non-fatal): %s", broadcast_err)

            logger.info("Returning TwiML to Twilio for call %s", call_sid)
            return Response(content=twiml, media_type="text/xml")

        else:
            ext = router.get_available_agent()
            if ext is None:
                return Response(content=router.generate_busy_twiml(), media_type="text/xml")
            router.mark_busy(ext, call_sid)
            agent_busy_since[ext] = datetime.utcnow()
            connected_calls.add(call_sid)
            webhook_base = config["twilio"].get("webhook_base_url", "").rstrip("/")
            twiml = router.generate_connect_twiml(ext, webhook_base)
            logger.info("Softphone TwiML: %s", twiml)
            await manager.broadcast({
                "event": "call_connected", "call_sid": call_sid,
                "agent": ext, "ts": datetime.utcnow().isoformat()
            })
            return Response(content=twiml, media_type="text/xml")

    except Exception as e:
        logger.error("CRITICAL ERROR in /connect for call %s: %s", call_sid, str(e), exc_info=True)
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>',
            media_type="text/xml"
        )
async def connect_call(request: Request):
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    answered_by = form.get("AnsweredBy", "unknown")

    logger.info("Call answered: SID=%s answered_by=%s", call_sid, answered_by)

    # ── Machine detected → drop voicemail, never bridge ──────────
    if answered_by in ("machine_start", "machine_end", "machine_end_beep",
                       "machine_end_silence", "machine_end_other", "fax"):
        logger.info("AMD: machine detected (%s) — dropping voicemail", answered_by)
        # If we already bridged this call (answered_by=unknown first), hang up the agent leg
        if call_sid in connected_calls:
            logger.info("Call %s was already bridged — ignoring machine AMD callback", call_sid)
            return Response(
                content='<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>',
                media_type="text/xml"
            )
        await manager.broadcast({"event": "amd_machine", "call_sid": call_sid, "ts": datetime.utcnow().isoformat()})
        return Response(content=generate_no_answer_twiml(config), media_type="text/xml")

    # ── Already connected (async AMD second callback) → do nothing ─
    if call_sid in connected_calls:
        logger.info("Call %s already connected — ignoring duplicate /connect callback", call_sid)
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>',
            media_type="text/xml"
        )

    # ── Human answered (or unknown = connect immediately) ─────────
    _reload_config()
    agent_mode = config["agents"].get("agent_mode", "softphone")

    if agent_mode == "mobile":
        agent_index = router.get_available_agent_index()
        if agent_index is None:
            logger.warning("No agents available for call %s", call_sid)
            await manager.broadcast({"event": "no_agent", "call_sid": call_sid, "ts": datetime.utcnow().isoformat()})
            return Response(content=router.generate_busy_twiml(), media_type="text/xml")

        mobile_numbers = [n.strip() for n in config["agents"].get("agent_mobile_numbers", "").split(",")]
        mobile = mobile_numbers[agent_index]
        timeout = int(config["agents"].get("agent_timeout", "20"))

        router.mark_busy_by_index(agent_index, call_sid)
        agent_busy_since[str(agent_index)] = datetime.utcnow()
        connected_calls.add(call_sid)

        # Always use the LIVE ngrok URL, not the stale one from config
        live_url = _get_ngrok_url()
        webhook_base = (live_url or config["twilio"]["webhook_base_url"]).rstrip("/")
        logger.info("Bridging call %s to mobile agent %d: %s (webhook: %s)", call_sid, agent_index, mobile, webhook_base)

        twiml = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<Response>'
            f'<Dial timeout="{timeout}" action="{webhook_base}/agent-complete?agent={agent_index}">'
            f'<Number>{mobile}</Number>'
            f'</Dial>'
            f'<Play>{webhook_base}/voicemail-audio</Play>'
            f'</Response>'
        )
        await manager.broadcast({
            "event": "call_connected", "call_sid": call_sid,
            "agent": agent_index, "mobile": mobile,
            "ts": datetime.utcnow().isoformat()
        })
        return Response(content=twiml, media_type="text/xml")

    else:
        ext = router.get_available_agent()
        if ext is None:
            return Response(content=router.generate_busy_twiml(), media_type="text/xml")
        router.mark_busy(ext, call_sid)
        agent_busy_since[ext] = datetime.utcnow()
        connected_calls.add(call_sid)
        webhook_base = config["twilio"]["webhook_base_url"].rstrip("/")
        twiml = router.generate_connect_twiml(ext, webhook_base)
        await manager.broadcast({
            "event": "call_connected", "call_sid": call_sid,
            "agent": ext, "ts": datetime.utcnow().isoformat()
        })
        return Response(content=twiml, media_type="text/xml")


@app.post("/inbound")
async def inbound_call(request: Request):
    """
    Handle inbound calls — when a lead calls back after hearing the voicemail.
    Forwards the call to the first available agent mobile number.
    """
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    from_number = form.get("From", "unknown")
    logger.info("Inbound callback: SID=%s from=%s", call_sid, from_number)

    _reload_config()
    mobile_numbers_raw = config["agents"].get("agent_mobile_numbers", "")
    mobile_numbers = [n.strip() for n in mobile_numbers_raw.split(",") if n.strip()]
    agent_timeout = int(config["agents"].get("agent_timeout", "20"))

    if not mobile_numbers:
        logger.error("No agent mobile numbers configured for inbound callback")
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response><Say>Sorry, no agents are available. Please try again later.</Say><Hangup/></Response>'
        )
        return Response(content=twiml, media_type="text/xml")

    # Dial all agent numbers simultaneously — first to answer gets the call
    dial_numbers = "".join(f"<Number>{n}</Number>" for n in mobile_numbers)
    twiml = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response>'
        f'<Say voice="alice">Please hold while we connect you to an agent.</Say>'
        f'<Dial timeout="{agent_timeout}" answerOnBridge="true">'
        f'{dial_numbers}'
        f'</Dial>'
        f'<Say voice="alice">Sorry, no agents are available right now. Please call back later.</Say>'
        f'</Response>'
    )

    await manager.broadcast({
        "event": "inbound_callback",
        "call_sid": call_sid,
        "from": from_number,
        "ts": datetime.utcnow().isoformat()
    })
    logger.info("Inbound callback from %s — forwarding to agents: %s", from_number, mobile_numbers)
    return Response(content=twiml, media_type="text/xml")


@app.post("/no-answer")
async def no_answer(request: Request):
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    status = form.get("CallStatus", "unknown")
    to_number = form.get("To", "unknown")
    try:
        await manager.broadcast({"event": "no_answer", "call_sid": call_sid, "status": status, "to": to_number, "ts": datetime.utcnow().isoformat()})
    except Exception:
        pass
    return Response(content=generate_no_answer_twiml(config), media_type="text/xml")


@app.post("/agent-complete")
async def agent_complete(request: Request, ext: str = "", agent: str = ""):
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    dial_status = form.get("DialCallStatus", "unknown")
    logger.info("Agent complete: SID=%s status=%s agent=%s ext=%s", call_sid, dial_status, agent, ext)

    if agent:
        try:
            router.mark_available_by_index(int(agent))
            agent_busy_since.pop(agent, None)
            logger.info("Mobile agent %s marked available after call %s", agent, call_sid)
        except ValueError:
            pass
    elif ext:
        router.mark_available(ext)
        agent_busy_since.pop(ext, None)
        logger.info("Softphone agent %s marked available after call %s", ext, call_sid)

    await manager.broadcast({
        "event": "agent_available",
        "agent": agent or ext,
        "call_sid": call_sid,
        "dial_status": dial_status,
        "ts": datetime.utcnow().isoformat()
    })
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>',
        media_type="text/xml"
    )


@app.post("/call-status")
async def call_status(request: Request):
    """
    Twilio calls this for ALL call status updates (initiated, ringing, answered, completed).
    Use this as a safety net to release agents when calls complete,
    even if /agent-complete was never called.
    """
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    call_status_val = form.get("CallStatus", "unknown")
    to_number = form.get("To", "")
    call_duration = int(form.get("CallDuration", 0) or 0)
    answered_by = form.get("AnsweredBy", "")
    logger.info("Call status update: SID=%s status=%s", call_sid, call_status_val)

    # If call is terminal, make sure agent is freed
    if call_status_val in ("completed", "failed", "busy", "no-answer", "canceled"):
        # Clean up connected_calls tracking
        connected_calls.discard(call_sid)

        # Find and release any agent holding this call
        status = router.status()
        for key, info in status.items():
            if info.get("call_sid") == call_sid:
                try:
                    router.mark_available_by_index(int(key))
                except (ValueError, AttributeError):
                    router.mark_available(key)
                logger.info("Safety release: agent %s freed after call %s (%s)", key, call_sid, call_status_val)
                await manager.broadcast({
                    "event": "agent_available",
                    "agent": key,
                    "call_sid": call_sid,
                    "reason": f"safety_release_{call_status_val}",
                    "ts": datetime.utcnow().isoformat()
                })
                break

        # Update campaign record with terminal call status
        with campaign_lock:
            if current_campaign is not None:
                status_map = {
                    "completed": "answered",
                    "no-answer": "no_answer",
                    "busy": "no_answer",
                    "failed": "failed",
                    "canceled": "failed",
                }
                mapped_status = status_map.get(call_status_val, call_status_val)
                _update_campaign_call(
                    current_campaign,
                    call_sid=call_sid,
                    name="",
                    phone=to_number,
                    status=mapped_status,
                    answered_by=answered_by,
                    duration=call_duration,
                )
                _save_campaign(current_campaign)

    await manager.broadcast({
        "event": "call_status",
        "call_sid": call_sid,
        "status": call_status_val,
        "ts": datetime.utcnow().isoformat()
    })
    return Response(content="", status_code=204)


@app.get("/voicemail-audio")
async def voicemail_audio():
    vm_file = config["voicemail"].get("voicemail_file", "voicemail.mp3")
    path = BASE_DIR / vm_file
    if not path.exists():
        return JSONResponse({"error": "Voicemail file not found"}, status_code=404)
    mime, _ = mimetypes.guess_type(str(path))
    return FileResponse(str(path), media_type=mime or "audio/mpeg")


@app.post("/api/voicemail/upload")
async def upload_voicemail(request: Request):
    """Upload a new voicemail.mp3 file."""
    import shutil
    content_type = request.headers.get("content-type", "")
    body = await request.body()
    if not body:
        return JSONResponse({"ok": False, "error": "No file data received"}, status_code=400)
    vm_path = BASE_DIR / "voicemail.mp3"
    with open(vm_path, "wb") as f:
        f.write(body)
    size = vm_path.stat().st_size
    logger.info("Voicemail uploaded: %d bytes", size)
    return {"ok": True, "size_bytes": size, "path": str(vm_path)}


# ---------------------------------------------------------------------------
# REST API — consumed by Next.js UI
# ---------------------------------------------------------------------------
@app.get("/api/status")
async def api_status():
    _reload_config()
    return {
        "agents": router.status(),
        "available": router.available_count(),
        "mode": config["agents"].get("agent_mode", "softphone"),
        "dialer_running": dialer_process is not None and dialer_process.poll() is None,
        "ngrok_url": config["twilio"].get("webhook_base_url", ""),
    }


@app.get("/api/services/status")
async def services_status():
    """Check all services — polled by the loading screen."""
    # Asterisk
    asterisk_ok = False
    try:
        result = subprocess.run(
            ["wsl", "-e", "bash", "-c", "systemctl is-active asterisk 2>/dev/null"],
            capture_output=True, text=True, timeout=4
        )
        asterisk_ok = "active" in result.stdout
    except Exception:
        pass

    # Ngrok
    ngrok_url = _get_ngrok_url()
    ngrok_ok = bool(ngrok_url)

    return {
        "asterisk": asterisk_ok,
        "api": True,
        "ngrok": ngrok_ok,
        "ngrok_url": ngrok_url,
    }


@app.post("/api/services/start-ngrok")
async def start_ngrok_service():
    """Start ngrok - called by the loading screen."""
    global ngrok_process

    # Already running?
    existing_url = _get_ngrok_url()
    if existing_url:
        _reload_config()
        config["twilio"]["webhook_base_url"] = existing_url
        with open(CONFIG_PATH, "w") as f:
            config.write(f)
        return {"ok": True, "url": existing_url, "already_running": True}

    # Find ngrok - check same folder first (highest priority)
    ngrok_paths = [
        str(BASE_DIR / "ngrok.exe"),
        str(BASE_DIR / "ngrok"),
        r"C:\Users\Admin\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe",
        r"C:\Users\Admin\Downloads\ngrok.exe",
        "ngrok",
    ]
    ngrok_exe = None
    for p in ngrok_paths:
        try:
            r = subprocess.run([p, "version"], capture_output=True, timeout=3)
            if r.returncode == 0:
                ngrok_exe = p
                logger.info("Found ngrok at: %s", p)
                break
        except Exception:
            continue

    if not ngrok_exe:
        return {
            "ok": False,
            "error": "ngrok.exe not found. Place ngrok.exe in the Smart Dialer folder."
        }

    # Configure authtoken if set in config
    if config.has_section("system"):
        ngrok_token = config["system"].get("ngrok_authtoken", "").strip()
        if ngrok_token:
            logger.info("Configuring ngrok authtoken...")
            subprocess.run(
                [ngrok_exe, "config", "add-authtoken", ngrok_token],
                capture_output=True, timeout=5
            )

    # Start ngrok with config file to bypass browser warning
    logger.info("Starting ngrok tunnel on port 5000...")
    ngrok_args = [ngrok_exe, "http", "5000", "--request-header-add", "ngrok-skip-browser-warning:true"]

    # Use config file if it exists
    ngrok_config = BASE_DIR / "ngrok.yml"
    if ngrok_config.exists():
        # Update authtoken in config file first
        if config.has_section("system"):
            token = config["system"].get("ngrok_authtoken", "").strip()
            if token:
                content = ngrok_config.read_text()
                content = content.replace("YOUR_NGROK_TOKEN_HERE", token)
                ngrok_config.write_text(content)
        ngrok_args = [ngrok_exe, "start", "smart-dialer", "--config", str(ngrok_config)]

    ngrok_process = subprocess.Popen(
        ngrok_args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait up to 12s for tunnel
    for i in range(12):
        await asyncio.sleep(1)
        url = _get_ngrok_url()
        if url:
            _reload_config()
            config["twilio"]["webhook_base_url"] = url
            with open(CONFIG_PATH, "w") as f:
                config.write(f)
            await manager.broadcast({"event": "ngrok_ready", "url": url, "ts": datetime.utcnow().isoformat()})
            logger.info("Ngrok tunnel ready: %s", url)
            return {"ok": True, "url": url}
        logger.info("Waiting for ngrok tunnel... (%d/12)", i + 1)

    # Check if ngrok process died immediately
    if ngrok_process.poll() is not None:
        return {
            "ok": False,
            "error": "Ngrok exited immediately. It needs an authtoken. Add ngrok_authtoken = YOUR_TOKEN to config.ini [system] section."
        }

    return {"ok": False, "error": "Ngrok started but tunnel not ready. Check http://localhost:4040"}


@app.get("/api/config")
async def get_config():
    _reload_config()
    return {
        "twilio": {
            "account_sid": config["twilio"].get("account_sid", ""),
            "auth_token": "***hidden***",
            "from_number": config["twilio"].get("from_number", ""),
            "webhook_base_url": config["twilio"].get("webhook_base_url", ""),
        },
        "signalwire": {
            "space_url": config["signalwire"].get("space_url", "") if config.has_section("signalwire") else "",
        },
        "agents": {
            "mode": config["agents"].get("agent_mode", "softphone"),
            "mobile_numbers": config["agents"].get("agent_mobile_numbers", ""),
            "names": config["agents"].get("agent_names", ""),
            "timeout": config["agents"].get("agent_timeout", "20"),
            "max_concurrent": config["agents"].get("max_concurrent_calls", "2"),
            "enable_amd": config["agents"].get("enable_amd", "true"),
            "amd_timeout": config["agents"].get("amd_timeout", "30"),
            "extensions": config["agents"].get("agent_extensions", "101,102"),
        },
        "dialer": {
            "ring_timeout":     config["dialer"].get("ring_timeout", "20"),
            "batch_delay":      config["dialer"].get("batch_delay", "1"),
            "concurrent_calls": config["dialer"].get("concurrent_calls", "5"),
        },
        "voicemail": {
            "file": config["voicemail"].get("voicemail_file", "voicemail.mp3"),
        },
        "system": {
            "wsl_sudo_password": config["system"].get("wsl_sudo_password", "8898") if config.has_section("system") else "8898",
            "ngrok_authtoken":   config["system"].get("ngrok_authtoken", "")   if config.has_section("system") else "",
        },
    }


@app.post("/api/config")
async def save_config(request: Request):
    body = await request.json()
    _reload_config()

    if "twilio" in body:
        t = body["twilio"]
        if t.get("account_sid"): config["twilio"]["account_sid"] = t["account_sid"]
        if t.get("auth_token") and t["auth_token"] != "***hidden***":
            config["twilio"]["auth_token"] = t["auth_token"]
        if t.get("from_number"): config["twilio"]["from_number"] = t["from_number"]
        if t.get("webhook_base_url"): config["twilio"]["webhook_base_url"] = t["webhook_base_url"]

    if "signalwire" in body:
        if not config.has_section("signalwire"):
            config.add_section("signalwire")
        sw = body["signalwire"]
        # space_url can be empty string (means use Twilio)
        config["signalwire"]["space_url"] = sw.get("space_url", "").strip()

    if "agents" in body:
        a = body["agents"]
        if a.get("mode"): config["agents"]["agent_mode"] = a["mode"]
        if a.get("mobile_numbers"): config["agents"]["agent_mobile_numbers"] = a["mobile_numbers"]
        if a.get("names"): config["agents"]["agent_names"] = a["names"]
        if a.get("timeout"): config["agents"]["agent_timeout"] = str(a["timeout"])
        if a.get("max_concurrent"): config["agents"]["max_concurrent_calls"] = str(a["max_concurrent"])
        if a.get("enable_amd") is not None: config["agents"]["enable_amd"] = str(a["enable_amd"]).lower()
        if a.get("extensions"): config["agents"]["agent_extensions"] = a["extensions"]

    if "dialer" in body:
        d = body["dialer"]
        if d.get("ring_timeout"):    config["dialer"]["ring_timeout"]    = str(d["ring_timeout"])
        if d.get("batch_delay"):     config["dialer"]["batch_delay"]     = str(d["batch_delay"])
        if d.get("concurrent_calls"): config["dialer"]["concurrent_calls"] = str(d["concurrent_calls"])

    if "system" in body:
        if not config.has_section("system"):
            config.add_section("system")
        s = body["system"]
        if s.get("wsl_sudo_password"):
            config["system"]["wsl_sudo_password"] = s["wsl_sudo_password"]
        if s.get("ngrok_authtoken") is not None:
            config["system"]["ngrok_authtoken"] = s["ngrok_authtoken"]

    with open(CONFIG_PATH, "w") as f:
        config.write(f)
    _reload_config()
    return {"ok": True}


@app.get("/api/contacts")
async def get_contacts():
    """Return contacts currently saved on disk."""
    csv_path = BASE_DIR / config["dialer"].get("contact_list", "contacts.csv")
    if not csv_path.exists():
        return {"contacts": [], "total": 0}
    import csv as csv_mod
    contacts = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv_mod.DictReader(f)
        for row in reader:
            name  = row.get("name", "").strip()
            phone = row.get("phone_number", "").strip()
            if phone:
                contacts.append({"name": name, "phone": phone})
    return {"contacts": contacts[:200], "total": len(contacts)}


@app.post("/api/contacts/upload")
async def upload_contacts(request: Request):
    """
    Receive contacts JSON from the UI and write them to contacts.csv on disk.
    The dialer reads from this file when a campaign starts.
    """
    body = await request.json()
    contacts = body.get("contacts", [])
    if not contacts:
        return JSONResponse({"ok": False, "error": "No contacts provided"}, status_code=400)

    csv_path = BASE_DIR / config["dialer"].get("contact_list", "contacts.csv")
    import csv as csv_mod
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv_mod.DictWriter(f, fieldnames=["name", "phone_number"])
        writer.writeheader()
        for c in contacts:
            writer.writerow({"name": c.get("name", ""), "phone_number": c.get("phone", "")})

    logger.info("Contacts uploaded: %d records saved to %s", len(contacts), csv_path)
    await manager.broadcast({"event": "log", "msg": f"Contacts saved: {len(contacts)} records", "ts": datetime.utcnow().isoformat()})
    return {"ok": True, "total": len(contacts)}


async def _finalize_campaign_async():
    """Auto-finalize campaign when dialer process exits naturally."""
    global current_campaign
    with campaign_lock:
        if current_campaign is not None:
            current_campaign["ended_at"] = datetime.utcnow().isoformat()
            current_campaign["status"] = "completed"
            _save_campaign(current_campaign)
            logger.info("Campaign auto-finalized: %s", current_campaign["id"])
            current_campaign = None


@app.post("/api/dialer/start")
async def start_dialer():
    global dialer_process, current_campaign
    if dialer_process and dialer_process.poll() is None:
        return {"ok": False, "error": "Dialer already running"}

    # Count contacts for the campaign record
    _reload_config()
    total_contacts = 0
    try:
        import csv as csv_mod
        csv_path = BASE_DIR / config["dialer"].get("contact_list", "contacts.csv")
        if csv_path.exists():
            with open(csv_path, newline="", encoding="utf-8") as f:
                total_contacts = sum(1 for row in csv_mod.DictReader(f) if row.get("phone_number", "").strip())
    except Exception:
        pass

    # Create and persist a new campaign record
    current_campaign = _new_campaign(total_contacts)
    _save_campaign(current_campaign)
    logger.info("Campaign started: %s (%d contacts)", current_campaign["id"], total_contacts)

    dialer_script = BASE_DIR / "dialer.py"
    dialer_process = subprocess.Popen(
        ["python", str(dialer_script)],
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # Capture the event loop in the main thread before spawning the worker
    loop = asyncio.get_event_loop()

    def _stream():
        for line in dialer_process.stdout:
            line = line.strip()
            if line:
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast({"event": "log", "msg": line, "ts": datetime.utcnow().isoformat()}),
                    loop,
                )
        # Dialer process exited naturally — finalize campaign then broadcast stopped
        asyncio.run_coroutine_threadsafe(
            _finalize_campaign_async(),
            loop,
        )
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({"event": "dialer_stopped", "ts": datetime.utcnow().isoformat()}),
            loop,
        )

    threading.Thread(target=_stream, daemon=True).start()
    await manager.broadcast({"event": "dialer_started", "ts": datetime.utcnow().isoformat()})
    return {"ok": True, "pid": dialer_process.pid, "campaign_id": current_campaign["id"]}


@app.post("/api/dialer/stop")
async def stop_dialer():
    global dialer_process, current_campaign
    if dialer_process and dialer_process.poll() is None:
        dialer_process.terminate()
        try:
            dialer_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            dialer_process.kill()
    dialer_process = None

    # Finalize the campaign record
    with campaign_lock:
        if current_campaign is not None:
            current_campaign["ended_at"] = datetime.utcnow().isoformat()
            current_campaign["status"] = "completed"
            _save_campaign(current_campaign)
            logger.info("Campaign finalized: %s", current_campaign["id"])
            current_campaign = None

    await manager.broadcast({"event": "dialer_stopped", "ts": datetime.utcnow().isoformat()})
    return {"ok": True}


@app.get("/api/ngrok/detect")
async def detect_ngrok():
    url = _get_ngrok_url()
    if url:
        _reload_config()
        config["twilio"]["webhook_base_url"] = url
        with open(CONFIG_PATH, "w") as f:
            config.write(f)
        return {"ok": True, "url": url}
    return {"ok": False, "url": ""}


@app.get("/api/call-log")
async def get_call_log():
    return {"calls": call_log[-200:]}


# ---------------------------------------------------------------------------
# Campaign history endpoints
# ---------------------------------------------------------------------------

@app.get("/api/campaigns")
async def list_campaigns():
    """Return summary list of all past campaigns (no call details)."""
    return {"campaigns": _list_campaigns()}


@app.get("/api/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str):
    """Return full campaign detail including all call records."""
    campaign = _load_campaign(campaign_id)
    if campaign is None:
        return JSONResponse({"error": "Campaign not found"}, status_code=404)
    return campaign


@app.get("/api/campaigns/{campaign_id}/export")
async def export_campaign(campaign_id: str):
    """Return campaign call log as a CSV file download."""
    import csv as csv_mod
    import io

    campaign = _load_campaign(campaign_id)
    if campaign is None:
        return JSONResponse({"error": "Campaign not found"}, status_code=404)

    output = io.StringIO()
    writer = csv_mod.writer(output)
    writer.writerow(["Name", "Phone", "Status", "Answered By", "Timestamp", "Duration"])
    for call in campaign.get("calls", []):
        writer.writerow([
            call.get("name", ""),
            call.get("phone", ""),
            call.get("status", ""),
            call.get("answered_by", ""),
            call.get("timestamp", ""),
            call.get("duration", 0),
        ])

    csv_bytes = output.getvalue().encode("utf-8")
    filename = f"{campaign_id}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        await ws.send_json({
            "event": "init",
            "agents": router.status(),
            "available": router.available_count(),
            "ts": datetime.utcnow().isoformat(),
        })
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=5000, reload=False, log_level="info")
