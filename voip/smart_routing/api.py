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


manager = ConnectionManager()
call_log: list[dict] = []
dialer_process: subprocess.Popen | None = None
ngrok_process: subprocess.Popen | None = None

# Track when each agent was marked busy (for timeout-based release)
agent_busy_since: dict[str, datetime] = {}

# Track calls already connected to an agent (prevents double-bridging from async AMD)
connected_calls: set[str] = set()


def _reload_config():
    global config, router
    config = load_config()
    router = AgentRouter(config)


async def _stuck_call_watchdog():
    """
    Background task: auto-release agents stuck busy for longer than
    agent_timeout + 60s safety buffer. Handles cases where Twilio
    never fires the agent-complete webhook.
    """
    while True:
        await asyncio.sleep(30)
        try:
            _reload_config()
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
    """Return current ngrok tunnel URL or empty string."""
    try:
        with urllib.request.urlopen("http://localhost:4040/api/tunnels", timeout=2) as r:
            data = json.loads(r.read())
        tunnels = data.get("tunnels", [])
        if tunnels:
            return tunnels[0]["public_url"]
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# Twilio Webhook endpoints
# ---------------------------------------------------------------------------
@app.post("/connect")
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

        webhook_base = config["twilio"]["webhook_base_url"].rstrip("/")
        logger.info("Bridging call %s to mobile agent %d: %s", call_sid, agent_index, mobile)

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


@app.post("/no-answer")
async def no_answer(request: Request):
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    status = form.get("CallStatus", "unknown")
    to_number = form.get("To", "unknown")
    await manager.broadcast({"event": "no_answer", "call_sid": call_sid, "status": status, "to": to_number, "ts": datetime.utcnow().isoformat()})
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
    call_status = form.get("CallStatus", "unknown")
    logger.info("Call status update: SID=%s status=%s", call_sid, call_status)

    # If call is terminal, make sure agent is freed
    if call_status in ("completed", "failed", "busy", "no-answer", "canceled"):
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
                logger.info("Safety release: agent %s freed after call %s (%s)", key, call_sid, call_status)
                await manager.broadcast({
                    "event": "agent_available",
                    "agent": key,
                    "call_sid": call_sid,
                    "reason": f"safety_release_{call_status}",
                    "ts": datetime.utcnow().isoformat()
                })
                break

    await manager.broadcast({
        "event": "call_status",
        "call_sid": call_sid,
        "status": call_status,
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

    # Start ngrok
    logger.info("Starting ngrok tunnel on port 5000...")
    ngrok_process = subprocess.Popen(
        [ngrok_exe, "http", "5000"],
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
            "ring_timeout": config["dialer"].get("ring_timeout", "20"),
            "batch_delay": config["dialer"].get("batch_delay", "2"),
        },
        "voicemail": {
            "file": config["voicemail"].get("voicemail_file", "voicemail.mp3"),
        },
        "system": {
            "wsl_sudo_password": config["system"].get("wsl_sudo_password", "8898") if config.has_section("system") else "8898",
            "ngrok_authtoken": config["system"].get("ngrok_authtoken", "") if config.has_section("system") else "",
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
        if d.get("ring_timeout"): config["dialer"]["ring_timeout"] = str(d["ring_timeout"])
        if d.get("batch_delay"): config["dialer"]["batch_delay"] = str(d["batch_delay"])

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


@app.post("/api/dialer/start")
async def start_dialer():
    global dialer_process
    if dialer_process and dialer_process.poll() is None:
        return {"ok": False, "error": "Dialer already running"}

    dialer_script = BASE_DIR / "dialer.py"
    dialer_process = subprocess.Popen(
        ["python", str(dialer_script)],
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    def _stream():
        for line in dialer_process.stdout:
            line = line.strip()
            if line:
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast({"event": "log", "msg": line, "ts": datetime.utcnow().isoformat()}),
                    asyncio.get_event_loop(),
                )
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({"event": "dialer_stopped", "ts": datetime.utcnow().isoformat()}),
            asyncio.get_event_loop(),
        )

    threading.Thread(target=_stream, daemon=True).start()
    await manager.broadcast({"event": "dialer_started", "ts": datetime.utcnow().isoformat()})
    return {"ok": True, "pid": dialer_process.pid}


@app.post("/api/dialer/stop")
async def stop_dialer():
    global dialer_process
    if dialer_process and dialer_process.poll() is None:
        dialer_process.terminate()
        try:
            dialer_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            dialer_process.kill()
    dialer_process = None
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
