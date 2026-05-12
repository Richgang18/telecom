"""
dialer.py — Smart outbound dialer with agent-matched concurrency.

Reads contacts from a CSV file and dials them via Twilio, limiting
simultaneous calls to the number of available agents (max 2).

Flow:
  1. Load contacts from contacts.csv
  2. Check available agent count (max_concurrent_calls from config)
  3. Dial up to N contacts simultaneously (N = available agents)
  4. Each answered call POSTs to /connect → agent_router bridges to agent
  5. Each unanswered call POSTs to /no-answer → voicemail_drop plays message
  6. When a call completes, agent is freed and next contact is dialed

Usage:
    python3 dialer.py                    # dial all contacts
    python3 dialer.py --dry-run          # preview without dialing
    python3 dialer.py --limit 10         # dial first 10 contacts only
"""

from __future__ import annotations

import argparse
import configparser
import csv
import logging
import time
from pathlib import Path

from twilio.rest import Client  # type: ignore[import]

from agent_router import AgentRouter

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CONFIG_PATH = Path(__file__).parent / "config.ini"


def load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH)
    return cfg


def setup_logging(config: configparser.ConfigParser) -> None:
    log_cfg = config["logging"]
    logging.basicConfig(
        level=getattr(logging, log_cfg.get("log_level", "INFO")),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(
                Path(__file__).parent / log_cfg.get("log_file", "smart_routing.log")
            ),
            logging.StreamHandler(),
        ],
    )


# ---------------------------------------------------------------------------
# Contact loader
# ---------------------------------------------------------------------------


def normalize_phone(phone: str) -> str:
    """Normalize phone number to E.164 format (+1XXXXXXXXXX for US numbers)."""
    # Strip everything except digits and leading +
    digits = "".join(c for c in phone if c.isdigit())
    if phone.strip().startswith("+"):
        return "+" + digits
    # US number: 10 digits → add +1
    if len(digits) == 10:
        return f"+1{digits}"
    # Already has country code: 11 digits starting with 1
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    # Return as-is with + prefix
    return f"+{digits}"


def load_contacts(csv_path: Path) -> list[dict[str, str]]:
    """
    Load contacts from a CSV file.

    Expected CSV format (with or without header):
        name,phone_number
        John Smith,+14145551001
        Jane Doe,+14145551002

    Parameters
    ----------
    csv_path:
        Path to the contacts CSV file.

    Returns
    -------
    list[dict]
        List of {"name": str, "phone": str} dicts.

    Raises
    ------
    FileNotFoundError
        If the CSV file does not exist.
    ValueError
        If the CSV is empty or malformed.
    """
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Contact list not found: {csv_path}\n"
            "Create a CSV file with columns: name,phone_number"
        )

    contacts: list[dict[str, str]] = []
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            name = row.get("name", "").strip()
            phone = row.get("phone_number", "").strip()
            if phone:
                phone = normalize_phone(phone)
                contacts.append({"name": name, "phone": phone})

    if not contacts:
        raise ValueError(f"No contacts found in {csv_path}")

    return contacts


# ---------------------------------------------------------------------------
# Twilio dialer
# ---------------------------------------------------------------------------


class SmartDialer:
    """
    Outbound dialer that limits concurrent calls to available agent count.

    Each call is initiated via Twilio's REST API. Twilio webhooks handle
    call routing (connect to agent or drop voicemail).
    """

    def __init__(
        self,
        config: configparser.ConfigParser,
        agent_router: AgentRouter,
        dry_run: bool = False,
    ) -> None:
        self.config = config
        self.router = agent_router
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)

        twilio_cfg = config["twilio"]
        self.client = Client(
            twilio_cfg["account_sid"],
            twilio_cfg["auth_token"],
        )
        self.from_number = twilio_cfg["from_number"]
        self.webhook_base = twilio_cfg["webhook_base_url"].rstrip("/")

        dialer_cfg = config["dialer"]
        self.ring_timeout = int(dialer_cfg.get("ring_timeout", "20"))
        self.batch_delay = float(dialer_cfg.get("batch_delay", "2"))
        self.max_concurrent = int(config["agents"].get("max_concurrent_calls", "2"))

        # Track active call SIDs → contact info
        self._active_calls: dict[str, dict] = {}

    def dial_contact(self, contact: dict[str, str]) -> str | None:
        """
        Initiate a single outbound call to a contact.

        Parameters
        ----------
        contact:
            Dict with "name" and "phone" keys.

        Returns
        -------
        str | None
            Twilio call SID on success, None on dry run.
        """
        phone = contact["phone"]
        name = contact["name"]

        if self.dry_run:
            self.logger.info("[DRY RUN] Would dial %s (%s)", name, phone)
            return None

        self.logger.info("Dialing %s (%s)...", name, phone)

        # Always read the LATEST webhook URL from config (ngrok may have changed)
        self.config.read(CONFIG_PATH)
        self.webhook_base = self.config["twilio"]["webhook_base_url"].rstrip("/")

        # Get AMD settings from config
        enable_amd = self.config["agents"].getboolean("enable_amd", True)
        amd_timeout = int(self.config["agents"].get("amd_timeout", "30"))
        
        # Build call parameters
        call_params = {
            "to": phone,
            "from_": self.from_number,
            "url": f"{self.webhook_base}/connect",
            "status_callback": f"{self.webhook_base}/call-status",
            "status_callback_event": ["initiated", "ringing", "answered", "completed"],
            "status_callback_method": "POST",
            "timeout": self.ring_timeout,
        }

        self.logger.info("Using webhook URL: %s", self.webhook_base)
        
        # Add AMD if enabled
        if enable_amd:
            call_params["machine_detection"] = "DetectMessageEnd"
            call_params["machine_detection_timeout"] = amd_timeout
            call_params["async_amd"] = "true"
            call_params["async_amd_status_callback"] = f"{self.webhook_base}/connect"
            call_params["async_amd_status_callback_method"] = "POST"

        call = self.client.calls.create(**call_params)

        self.logger.info(
            "Call initiated: SID=%s to=%s name=%s AMD=%s",
            call.sid, phone, name, "enabled" if enable_amd else "disabled",
        )
        return call.sid

    def run(self, contacts: list[dict[str, str]], limit: int | None = None) -> None:
        """
        Dial all contacts, respecting agent availability.

        Parameters
        ----------
        contacts:
            List of contact dicts from load_contacts().
        limit:
            Optional max number of contacts to dial.
        """
        if limit:
            contacts = contacts[:limit]

        total = len(contacts)
        self.logger.info(
            "Starting smart dialer: %d contacts, max %d concurrent calls",
            total, self.max_concurrent,
        )

        dialed = 0
        index = 0

        while index < total:
            available = self.router.available_count()

            if available == 0:
                self.logger.info(
                    "⏸️  All %d agents busy — pausing dialer until one becomes available...",
                    self.max_concurrent
                )
                # Wait for an agent to become available (with 60 second timeout as safety)
                if self.router.wait_for_available_agent(timeout=60):
                    self.logger.info("✅ Agent available — resuming dialing")
                    continue
                else:
                    # Timeout occurred, check again
                    self.logger.warning("⚠️  Timeout waiting for agent — checking status...")
                    continue

            # Dial up to available agent count
            batch_size = min(available, total - index)
            self.logger.info(
                "Batch: dialing %d contact(s) (%d/%d total) — %d agents available",
                batch_size, index + batch_size, total, available,
            )

            for _ in range(batch_size):
                if index >= total:
                    break
                contact = contacts[index]
                sid = self.dial_contact(contact)
                if sid:
                    self._active_calls[sid] = contact
                index += 1
                dialed += 1

            # Small delay between batches to avoid overwhelming Twilio API
            time.sleep(self.batch_delay)

        self.logger.info(
            "Dialing complete. Total dialed: %d/%d", dialed, total
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smart outbound dialer — dials contacts matched to agent availability"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview contacts without making real calls",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of contacts to dial",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=str(CONFIG_PATH),
        help="Path to config.ini (default: ./config.ini)",
    )
    args = parser.parse_args()

    config = load_config()
    setup_logging(config)
    logger = logging.getLogger(__name__)

    # Load contacts
    contact_csv = (
        Path(__file__).parent
        / config["dialer"].get("contact_list", "contacts.csv")
    )
    contacts = load_contacts(contact_csv)
    logger.info("Loaded %d contacts from %s", len(contacts), contact_csv)

    # Initialise agent router
    router = AgentRouter(config)

    # Run dialer
    dialer = SmartDialer(config, router, dry_run=args.dry_run)
    dialer.run(contacts, limit=args.limit)


if __name__ == "__main__":
    main()
