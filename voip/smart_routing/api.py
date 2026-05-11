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


def _reload_config():
    global config, router
    config = load_config()
    router = AgentRouter(config)


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

    if answered_by in ("machine_start", "fax"):
        logger.info("AMD: machine detected — dropping voicemail")
        await manager.broadcast({"event": "amd_machine", "call_sid": call_sid, "ts": datetime.utcnow().isoformat()})
        return Response(content=generate_no_answer_twiml(config), media_type="text/xml")

    agent_mode = config["agents"].get("agent_mode", "softphone")

    if agent_mode == "mobile":
        agent_index = router.get_available_agent_index()
        if agent_index is None:
            await manager.broadcast({"event": "no_agent", "call_sid": call_sid, "ts": datetime.utcnow().isoformat()})
            return Response(content=router.generate_busy_twiml(), media_type="text/xml")

        mobile_numbers = [n.strip() for n in config["agents"].get("agent_mobile_numbers", "").split(",")]
        mobile = mobile_numbers[agent_index]
        timeout = int(config["agents"].get("agent_timeout", "20"))
        router.mark_busy_by_index(agent_index, call_sid)
        webhook_base = config["twilio"]["webhook_base_url"].rstrip("/")

        twiml = (
            f'<?xml version="1.0" encoding="UTF-8"?><Response>'
            f'<Say voice="alice">Please hold while we connect you.</Say>'
            f'<Dial timeout="{timeout}" action="{webhook_base}/agent-complete?agent={agent_index}">'
            f'<Number>{mobile}</Number></Dial>'
            f'<Play>{webhook_base}/voicemail-audio</Play></Response>'
        )
        await manager.broadcast({"event": "call_connected", "call_sid": call_sid, "agent": agent_index, "mobile": mobile, "ts": datetime.utcnow().isoformat()})
        return Response(content=twiml, media_type="text/xml")
    else:
        ext = router.get_available_agent()
        if ext is None:
            return Response(content=router.generate_busy_twiml(), media_type="text/xml")
        router.mark_busy(ext, call_sid)
        webhook_base = config["twilio"]["webhook_base_url"].rstrip("/")
        twiml = router.generate_connect_twiml(ext, webhook_base)
        await manager.broadcast({"event": "call_connected", "call_sid": call_sid, "agent": ext, "ts": datetime.utcnow().isoformat()})
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
    if agent:
        try:
            router.mark_available_by_index(int(agent))
        except ValueError:
            pass
    elif ext:
        router.mark_available(ext)
    await manager.broadcast({"event": "agent_available", "agent": agent or ext, "call_sid": call_sid, "ts": datetime.utcnow().isoformat()})
    return Response(content='<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>', media_type="text/xml")


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
    """Start ngrok automatically — called by the loading screen."""
    global ngrok_process

    # Already running?
    existing_url = _get_ngrok_url()
    if existing_url:
        _reload_config()
        config["twilio"]["webhook_base_url"] = existing_url
        with open(CONFIG_PATH, "w") as f:
            config.write(f)
        return {"ok": True, "url": existing_url, "already_running": True}

    # Find ngrok executable
    ngrok_paths = [
        r"C:\Users\Admin\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe",
        r"C:\Users\Admin\Downloads\ngrok.exe",
        str(BASE_DIR / "ngrok.exe"),
        "ngrok",
    ]
    ngrok_exe = None
    for p in ngrok_paths:
        try:
            r = subprocess.run([p, "version"], capture_output=True, timeout=2)
            if r.returncode == 0:
                ngrok_exe = p
                break
        except Exception:
            continue

    if not ngrok_exe:
        return {
            "ok": False,
            "error": "ngrok.exe not found. Download from https://ngrok.com/download and place it in the Smart Dialer folder."
        }

    ngrok_process = subprocess.Popen(
        [ngrok_exe, "http", "5000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait up to 10s for tunnel
    for _ in range(10):
        await asyncio.sleep(1)
        url = _get_ngrok_url()
        if url:
            _reload_config()
            config["twilio"]["webhook_base_url"] = url
            with open(CONFIG_PATH, "w") as f:
                config.write(f)
            await manager.broadcast({"event": "ngrok_ready", "url": url, "ts": datetime.utcnow().isoformat()})
            return {"ok": True, "url": url}

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

    with open(CONFIG_PATH, "w") as f:
        config.write(f)
    _reload_config()
    return {"ok": True}


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
