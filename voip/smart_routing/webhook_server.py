"""
webhook_server.py — Flask webhook server for Twilio call events.

Handles inbound POST requests from Twilio:
  POST /connect        — Called when outbound call is answered by a human
                         Returns TwiML to bridge call to available agent
  POST /no-answer      — Called when call is not answered / goes to voicemail
                         Returns TwiML to drop pre-recorded voicemail
  POST /agent-complete — Called when agent hangs up
                         Marks agent as available for next call
  GET  /voicemail-audio — Serves the pre-recorded voicemail MP3/WAV file
  GET  /status         — Health check, shows agent availability

Usage:
    python3 webhook_server.py

The server must be publicly reachable by Twilio. Use ngrok for local
testing or deploy behind the domain configured in config.ini.
"""

from __future__ import annotations

import configparser
import logging
import mimetypes
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file  # type: ignore[import]

from agent_router import AgentRouter
from voicemail_drop import generate_no_answer_twiml

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

CONFIG_PATH = Path(__file__).parent / "config.ini"


def load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH)
    return cfg


config = load_config()

logging.basicConfig(
    level=getattr(
        logging,
        config["logging"].get("log_level", "INFO"),
    ),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(
            Path(__file__).parent
            / config["logging"].get("log_file", "smart_routing.log")
        ),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)
app = Flask(__name__)
router = AgentRouter(config)

# ---------------------------------------------------------------------------
# Webhook endpoints
# ---------------------------------------------------------------------------


@app.route("/connect", methods=["POST"])
def connect() -> Response:
    """
    Called by Twilio when an outbound call is answered by a human.

    Checks for an available agent and returns TwiML to bridge the call.
    If no agents are available, plays a busy message.
    
    Supports two modes:
    - softphone: Connects to SIP extension (original mode)
    - mobile: Dials agent's mobile phone (VICIdial-style)
    """
    call_sid = request.form.get("CallSid", "unknown")
    to_number = request.form.get("To", "unknown")
    answered_by = request.form.get("AnsweredBy", "unknown")

    logger.info(
        "Call answered: SID=%s to=%s answered_by=%s",
        call_sid, to_number, answered_by,
    )

    # If answered by machine, drop voicemail instead
    if answered_by in ("machine_start", "fax"):
        logger.info("Answering machine detected — dropping voicemail")
        twiml = generate_no_answer_twiml(config)
        return Response(twiml, mimetype="text/xml")

    # Check agent mode
    agent_mode = config["agents"].get("agent_mode", "softphone")
    
    if agent_mode == "mobile":
        # Mobile agent mode - dial agent's cellphone
        return connect_mobile_agent(call_sid, to_number)
    else:
        # Softphone mode - connect to SIP extension
        return connect_softphone_agent(call_sid, to_number)


def connect_mobile_agent(call_sid: str, to_number: str) -> Response:
    """
    Connect call to agent's mobile phone (VICIdial-style).
    
    Flow:
    1. Find available agent
    2. Dial agent's mobile number
    3. Agent answers and presses 1 to confirm
    4. Bridge both calls together
    """
    # Find available agent
    agent_index = router.get_available_agent_index()
    if agent_index is None:
        logger.warning("No agents available for call %s", call_sid)
        twiml = router.generate_busy_twiml()
        return Response(twiml, mimetype="text/xml")
    
    # Get agent mobile number
    mobile_numbers = config["agents"].get("agent_mobile_numbers", "").split(",")
    if agent_index >= len(mobile_numbers):
        logger.error("Agent index %d out of range for mobile numbers", agent_index)
        twiml = router.generate_busy_twiml()
        return Response(twiml, mimetype="text/xml")
    
    mobile_number = mobile_numbers[agent_index].strip()
    agent_timeout = int(config["agents"].get("agent_timeout", "20"))
    
    # Mark agent busy
    router.mark_busy_by_index(agent_index, call_sid)
    
    # Generate TwiML to dial mobile
    webhook_base = config["twilio"]["webhook_base_url"].rstrip("/")
    
    twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Connecting you to an agent. Please wait.</Say>
    <Dial timeout="{agent_timeout}" action="{webhook_base}/agent-complete?agent={agent_index}">
        <Number>{mobile_number}</Number>
    </Dial>
    <Say voice="alice">The agent is not available. Leaving a voicemail.</Say>
    <Play>{webhook_base}/voicemail-audio</Play>
</Response>'''
    
    logger.info("Connecting call %s to mobile agent %d (%s)", call_sid, agent_index, mobile_number)
    return Response(twiml, mimetype="text/xml")


def connect_softphone_agent(call_sid: str, to_number: str) -> Response:
    """
    Connect call to SIP softphone extension (original mode).
    """
    # Find available agent
    ext = router.get_available_agent()
    if ext is None:
        logger.warning("No agents available for call %s", call_sid)
        twiml = router.generate_busy_twiml()
        return Response(twiml, mimetype="text/xml")

    # Mark agent busy and connect
    router.mark_busy(ext, call_sid)
    webhook_base = config["twilio"]["webhook_base_url"].rstrip("/")
    twiml = router.generate_connect_twiml(ext, webhook_base)

    logger.info("Connecting call %s to agent extension %s", call_sid, ext)
    return Response(twiml, mimetype="text/xml")


@app.route("/no-answer", methods=["POST"])
def no_answer() -> Response:
    """
    Called by Twilio when a call is not answered, busy, or failed.

    Returns TwiML to drop the pre-recorded voicemail.
    """
    call_sid = request.form.get("CallSid", "unknown")
    call_status = request.form.get("CallStatus", "unknown")
    to_number = request.form.get("To", "unknown")

    logger.info(
        "Call not answered: SID=%s status=%s to=%s",
        call_sid, call_status, to_number,
    )

    twiml = generate_no_answer_twiml(config)
    return Response(twiml, mimetype="text/xml")


@app.route("/agent-complete", methods=["POST"])
def agent_complete() -> Response:
    """
    Called by Twilio when the agent hangs up (Dial action URL).

    Marks the agent as available for the next call.
    Supports both softphone (ext) and mobile (agent index) modes.
    """
    ext = request.args.get("ext", "")
    agent_index_str = request.args.get("agent", "")
    call_sid = request.form.get("CallSid", "unknown")
    dial_status = request.form.get("DialCallStatus", "unknown")

    logger.info(
        "Agent completed call %s (status=%s)",
        call_sid, dial_status,
    )

    # Handle mobile agent mode
    if agent_index_str:
        try:
            agent_index = int(agent_index_str)
            router.mark_available_by_index(agent_index)
            logger.info("Mobile agent %d marked available", agent_index)
        except ValueError:
            logger.error("Invalid agent index: %s", agent_index_str)
    
    # Handle softphone mode
    elif ext:
        router.mark_available(ext)
        logger.info("Softphone agent %s marked available", ext)

    # Return empty TwiML to end the call
    return Response(
        '<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>',
        mimetype="text/xml",
    )


@app.route("/voicemail-audio", methods=["GET"])
def voicemail_audio() -> Response:
    """Serve the pre-recorded voicemail audio file to Twilio."""
    voicemail_file = config["voicemail"].get("voicemail_file", "voicemail.mp3")
    audio_path = Path(__file__).parent / voicemail_file

    if not audio_path.exists():
        logger.error("Voicemail file not found: %s", audio_path)
        return Response("Voicemail file not found", status=404)

    mime_type, _ = mimetypes.guess_type(str(audio_path))
    return send_file(str(audio_path), mimetype=mime_type or "audio/mpeg")


@app.route("/status", methods=["GET"])
def status() -> Response:
    """Health check endpoint — returns agent availability status."""
    agent_status = router.status()
    available = router.available_count()
    return jsonify({
        "status": "ok",
        "agents": agent_status,
        "available_agents": available,
        "max_concurrent_calls": config["agents"].get("max_concurrent_calls", "2"),
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = 5000
    logger.info("Starting webhook server on port %d", port)
    logger.info("Webhook base URL: %s", config["twilio"]["webhook_base_url"])
    logger.info("Agent status: %s", router.status())
    app.run(host="0.0.0.0", port=port, debug=False)
