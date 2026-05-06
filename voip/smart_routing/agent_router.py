"""
agent_router.py — Agent availability tracking and call routing.

Tracks which agents (extensions 101, 102) are available and routes
answered outbound calls to a free agent via Twilio's <Dial> verb.

Each agent maps to a SIP extension on the Asterisk PBX. When a call
is answered, Twilio POSTs to /connect — this module picks the next
free agent and returns TwiML to bridge the call.
"""

from __future__ import annotations

import configparser
import logging
import threading
from pathlib import Path

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

CONFIG_PATH = Path(__file__).parent / "config.ini"


def load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH)
    return cfg


# ---------------------------------------------------------------------------
# Agent state
# ---------------------------------------------------------------------------

class AgentRouter:
    """
    Thread-safe agent availability tracker.

    Agents are identified by their SIP extension. Status is either
    'available' or 'busy'. Calls are routed round-robin to available agents.
    """

    def __init__(self, config: configparser.ConfigParser) -> None:
        cfg = config["agents"]
        extensions = [e.strip() for e in cfg["agent_extensions"].split(",")]
        names = [n.strip() for n in cfg["agent_names"].split(",")]
        self.agent_timeout = int(cfg.get("agent_timeout", "20"))
        self.max_concurrent = int(cfg.get("max_concurrent_calls", "2"))

        self._lock = threading.Lock()
        self._availability_event = threading.Event()  # Signal when agent becomes available
        
        # {extension: {"name": str, "status": "available"|"busy", "call_sid": str|None}}
        self._agents: dict[str, dict] = {
            ext: {"name": name, "status": "available", "call_sid": None}
            for ext, name in zip(extensions, names)
        }

        self.logger = logging.getLogger(__name__)
        self.logger.info(
            "AgentRouter initialised with %d agents: %s",
            len(self._agents),
            list(self._agents.keys()),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def available_count(self) -> int:
        """Return the number of currently available agents."""
        with self._lock:
            return sum(
                1 for a in self._agents.values() if a["status"] == "available"
            )

    def get_available_agent(self) -> str | None:
        """
        Return the extension of the next available agent, or None if all busy.
        Does NOT mark the agent as busy — call mark_busy() after routing.
        """
        with self._lock:
            for ext, info in self._agents.items():
                if info["status"] == "available":
                    return ext
        return None

    def mark_busy(self, extension: str, call_sid: str) -> None:
        """Mark an agent as busy with the given call SID."""
        with self._lock:
            if extension in self._agents:
                self._agents[extension]["status"] = "busy"
                self._agents[extension]["call_sid"] = call_sid
                self.logger.info("Agent %s marked busy (call %s)", extension, call_sid)
                
                # Check if all agents are now busy
                if self.available_count() == 0:
                    self.logger.warning("⚠️  All agents busy - dialing will pause until one becomes available")

    def mark_available(self, extension: str) -> None:
        """Mark an agent as available (call ended)."""
        with self._lock:
            if extension in self._agents:
                self._agents[extension]["status"] = "available"
                self._agents[extension]["call_sid"] = None
                self.logger.info("✅ Agent %s marked available - resuming dialing", extension)
                
                # Signal that an agent is now available
                self._availability_event.set()

    def status(self) -> dict[str, dict]:
        """Return a copy of the current agent status dict."""
        with self._lock:
            return {ext: dict(info) for ext, info in self._agents.items()}
    
    def wait_for_available_agent(self, timeout: float = None) -> bool:
        """
        Block until at least one agent becomes available.
        
        Parameters
        ----------
        timeout:
            Maximum time to wait in seconds. None = wait indefinitely.
        
        Returns
        -------
        bool
            True if an agent is available, False if timeout occurred.
        """
        # Check if already available
        if self.available_count() > 0:
            return True
        
        # Clear the event and wait for it to be set
        self._availability_event.clear()
        result = self._availability_event.wait(timeout)
        
        # Clear the event for next wait
        self._availability_event.clear()
        
        return result and self.available_count() > 0

    def generate_connect_twiml(self, extension: str, webhook_base: str) -> str:
        """
        Generate TwiML to connect an answered outbound call to a SIP agent.

        Uses Twilio's <Dial><Sip> to bridge the call to the Asterisk
        extension via SIP. The action URL is called when the agent hangs up.

        Parameters
        ----------
        extension:
            The agent's SIP extension (e.g. "101").
        webhook_base:
            Base URL for Twilio webhooks (e.g. "https://pbx.vouchersdept.com").

        Returns
        -------
        str
            TwiML XML string.
        """
        sip_uri = f"sip:{extension}@pbx.vouchersdept.com:5061;transport=tls"
        action_url = f"{webhook_base}/agent-complete?ext={extension}"

        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<Response>\n"
            f'  <Dial timeout="{self.agent_timeout}" '
            f'action="{action_url}" method="POST">\n'
            f'    <Sip>{sip_uri}</Sip>\n'
            "  </Dial>\n"
            "</Response>"
        )

    def generate_busy_twiml(self) -> str:
        """TwiML returned when no agents are available — plays a message and hangs up."""
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<Response>\n"
            "  <Say>All agents are currently busy. Please try again later.</Say>\n"
            "  <Hangup/>\n"
            "</Response>"
        )
