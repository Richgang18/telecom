"""
dialer.py — Smart outbound dialer with concurrent calling support.

Supports two providers:
  - Twilio (default)
  - SignalWire (drop-in compatible, 60% cheaper)

Supports two dialing modes:
  - voicemail_blast: dials N numbers simultaneously, plays voicemail.mp3
  - mobile/softphone: dials up to available agent count simultaneously
"""

from __future__ import annotations

import argparse
import configparser
import csv
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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
# Phone normalization
# ---------------------------------------------------------------------------

def normalize_phone(phone: str) -> str:
    """Normalize any phone number format to E.164."""
    if not phone:
        return ""

    has_plus = phone.strip().startswith("+")
    digits = "".join(c for c in phone if c.isdigit())

    if not digits:
        return ""

    if has_plus:
        return "+" + digits

    # US: 10 digits
    if len(digits) == 10:
        return f"+1{digits}"

    # US with country code: 11 digits starting with 1
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"

    # Indian: 10 digits starting with 6-9
    if len(digits) == 10 and digits[0] in "6789":
        return f"+91{digits}"

    # Indian with country code: 12 digits starting with 91
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"

    return f"+{digits}"


# ---------------------------------------------------------------------------
# Contact loader
# ---------------------------------------------------------------------------

def load_contacts(csv_path: Path) -> list[dict[str, str]]:
    """Load contacts from CSV. Accepts any common column naming convention."""
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Contact list not found: {csv_path}\n"
            "Create a CSV file with columns: name,phone_number"
        )

    contacts: list[dict[str, str]] = []

    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)

        if not reader.fieldnames:
            raise ValueError(f"CSV has no headers: {csv_path}")

        header_map = {h.strip().lower(): h for h in reader.fieldnames}

        # Find phone column
        phone_col = None
        for candidate in ["phone_number", "phone", "mobile", "cell", "telephone", "number", "phonenumber"]:
            if candidate in header_map:
                phone_col = header_map[candidate]
                break

        if not phone_col:
            raise ValueError(
                f"No phone column found in {csv_path}.\n"
                f"Expected one of: phone_number, phone, mobile, cell.\n"
                f"Found columns: {list(reader.fieldnames)}"
            )

        name_col  = None
        for candidate in ["name", "full_name", "fullname", "contact"]:
            if candidate in header_map:
                name_col = header_map[candidate]
                break

        first_col = header_map.get("firstname") or header_map.get("first_name") or header_map.get("first")
        last_col  = header_map.get("lastname")  or header_map.get("last_name")  or header_map.get("last")

        skipped = 0
        for row in reader:
            raw_phone = row.get(phone_col, "").strip()
            if not raw_phone:
                skipped += 1
                continue

            phone = normalize_phone(raw_phone)
            if len(phone) < 8:
                skipped += 1
                continue

            if name_col:
                name = row.get(name_col, "").strip()
            elif first_col:
                first = row.get(first_col, "").strip()
                last  = row.get(last_col, "").strip() if last_col else ""
                name  = f"{first} {last}".strip()
            else:
                name = "Unknown"

            contacts.append({"name": name or "Unknown", "phone": phone})

        if skipped:
            logging.getLogger(__name__).warning(
                "Skipped %d rows with missing/invalid phone numbers", skipped
            )

    if not contacts:
        raise ValueError(f"No valid contacts found in {csv_path}")

    return contacts


# ---------------------------------------------------------------------------
# Provider factory — Twilio or SignalWire
# ---------------------------------------------------------------------------

def build_client(config: configparser.ConfigParser) -> Client:
    """Build Twilio client (used when SignalWire is not configured)."""
    twilio_cfg = config["twilio"]
    return Client(twilio_cfg["account_sid"], twilio_cfg["auth_token"])


# ---------------------------------------------------------------------------
# Twilio dialer
# ---------------------------------------------------------------------------

class SmartDialer:
    """
    Outbound dialer with concurrent calling and multi-provider support.

    Providers: Twilio (default) or SignalWire (60% cheaper, drop-in compatible)
    Modes: voicemail_blast (N simultaneous) or mobile/softphone (agent-limited)
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
        self.account_sid  = twilio_cfg["account_sid"]
        self.auth_token   = twilio_cfg["auth_token"]
        self.from_number  = twilio_cfg["from_number"]
        self.webhook_base = twilio_cfg["webhook_base_url"].rstrip("/")

        # Detect provider
        self.use_signalwire = (
            config.has_section("signalwire") and
            bool(config["signalwire"].get("space_url", "").strip())
        )
        if self.use_signalwire:
            space_url = config["signalwire"]["space_url"].strip()
            if not space_url.startswith("http"):
                space_url = f"https://{space_url}"
            self.sw_base_url = f"{space_url.rstrip('/')}/api/laml/2010-04-01"
            self.provider = "SignalWire"
            self.logger.info("Provider: SignalWire (%s)", self.sw_base_url)
        else:
            self.client = Client(self.account_sid, self.auth_token)
            self.provider = "Twilio"
            self.logger.info("Provider: Twilio")

        dialer_cfg = config["dialer"]
        self.ring_timeout     = int(dialer_cfg.get("ring_timeout", "20"))
        self.batch_delay      = float(dialer_cfg.get("batch_delay", "1"))
        self.max_concurrent   = int(config["agents"].get("max_concurrent_calls", "2"))
        self.concurrent_calls = int(dialer_cfg.get("concurrent_calls", "5"))

        self._active_calls: dict[str, dict] = {}
        self._lock = threading.Lock()

    def dial_contact(self, contact: dict[str, str]) -> str | None:
        """Initiate a single outbound call. Thread-safe."""
        phone = contact.get("phone", "").strip()
        name  = contact.get("name", "Unknown").strip()

        if not phone or len(phone) < 8:
            self.logger.warning("Skipping invalid phone for %s: '%s'", name, phone)
            return None

        if self.dry_run:
            self.logger.info("[DRY RUN] Would dial %s (%s)", name, phone)
            return None

        # Reload latest config
        cfg = load_config()
        webhook_base = cfg["twilio"]["webhook_base_url"].rstrip("/")
        agent_mode   = cfg["agents"].get("agent_mode", "mobile")
        enable_amd   = cfg["agents"].getboolean("enable_amd", True)
        amd_timeout  = int(cfg["agents"].get("amd_timeout", "30"))

        self.logger.info("Dialing %s (%s) via %s | mode=%s", name, phone, self.provider, agent_mode)

        call_params = {
            "to": phone,
            "from_": self.from_number,
            "url": f"{webhook_base}/connect",
            "status_callback": f"{webhook_base}/call-status",
            "status_callback_event": ["initiated", "ringing", "answered", "completed"],
            "status_callback_method": "POST",
            "timeout": self.ring_timeout,
        }

        if agent_mode == "voicemail_blast" or enable_amd:
            call_params["machine_detection"] = "DetectMessageEnd"
            call_params["machine_detection_timeout"] = amd_timeout
            call_params["async_amd"] = "true"
            call_params["async_amd_status_callback"] = f"{webhook_base}/connect"
            call_params["async_amd_status_callback_method"] = "POST"

        try:
            if self.use_signalwire:
                sid = self._call_via_signalwire(call_params)
            else:
                call = self.client.calls.create(**call_params)
                sid = call.sid

            if sid:
                self.logger.info("Call initiated: SID=%s to=%s name=%s", sid, phone, name)
                with self._lock:
                    self._active_calls[sid] = contact
            return sid
        except Exception as e:
            self.logger.error("Failed to dial %s (%s): %s", name, phone, e)
            return None

    def _call_via_signalwire(self, call_params: dict) -> str | None:
        """Make outbound call via SignalWire Compatibility REST API."""
        import requests as req

        url = f"{self.sw_base_url}/Accounts/{self.account_sid}/Calls.json"

        data: dict = {
            "To":                   call_params["to"],
            "From":                 call_params["from_"],
            "Url":                  call_params["url"],
            "StatusCallback":       call_params.get("status_callback", ""),
            "StatusCallbackMethod": call_params.get("status_callback_method", "POST"),
            "Timeout":              str(call_params.get("timeout", 20)),
        }

        for ev in call_params.get("status_callback_event", []):
            data.setdefault("StatusCallbackEvent[]", [])
            data["StatusCallbackEvent[]"].append(ev)  # type: ignore

        if "machine_detection" in call_params:
            data["MachineDetection"]             = call_params["machine_detection"]
            data["MachineDetectionTimeout"]      = str(call_params.get("machine_detection_timeout", 30))
            data["AsyncAmd"]                     = "true"
            data["AsyncAmdStatusCallback"]       = call_params.get("async_amd_status_callback", "")
            data["AsyncAmdStatusCallbackMethod"] = "POST"

        resp = req.post(
            url,
            data=data,
            auth=(self.account_sid, self.auth_token),
            timeout=10,
        )
        resp.raise_for_status()
        result = resp.json()
        return result.get("sid") or result.get("Sid", "")

    def run(self, contacts: list[dict[str, str]], limit: int | None = None) -> None:
        """Dial all contacts with concurrent calling."""
        if limit:
            contacts = contacts[:limit]

        total = len(contacts)
        cfg = load_config()
        agent_mode = cfg["agents"].get("agent_mode", "mobile")

        if agent_mode == "voicemail_blast":
            concurrency = self.concurrent_calls
        else:
            concurrency = self.max_concurrent

        self.logger.info(
            "Starting dialer: %d contacts | mode=%s | concurrency=%d",
            total, agent_mode, concurrency,
        )

        index  = 0
        dialed = 0

        while index < total:
            if agent_mode != "voicemail_blast":
                available = self.router.available_count()
                if available == 0:
                    self.logger.info("All agents busy — waiting...")
                    if self.router.wait_for_available_agent(timeout=60):
                        self.logger.info("Agent available — resuming")
                    continue
                concurrency = min(available, self.max_concurrent)

            batch = contacts[index: index + concurrency]
            if not batch:
                break

            self.logger.info(
                "Batch: dialing %d simultaneously (%d/%d total)",
                len(batch), index + len(batch), total,
            )

            with ThreadPoolExecutor(max_workers=len(batch)) as executor:
                futures = {executor.submit(self.dial_contact, c): c for c in batch}
                for future in as_completed(futures):
                    sid = future.result()
                    if sid:
                        dialed += 1

            index += len(batch)

            if index < total:
                time.sleep(self.batch_delay)

        self.logger.info("Dialing complete. Total dialed: %d/%d", dialed, total)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Smart outbound dialer")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--config", type=str, default=str(CONFIG_PATH))
    args = parser.parse_args()

    config = load_config()
    setup_logging(config)
    logger = logging.getLogger(__name__)

    contact_csv = (
        Path(__file__).parent
        / config["dialer"].get("contact_list", "contacts.csv")
    )
    contacts = load_contacts(contact_csv)
    logger.info("Loaded %d contacts from %s", len(contacts), contact_csv)

    router = AgentRouter(config)
    dialer = SmartDialer(config, router, dry_run=args.dry_run)
    dialer.run(contacts, limit=args.limit)


if __name__ == "__main__":
    main()
