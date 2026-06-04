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
    # Read with UTF-8 and strip BOM — PowerShell Set-Content writes UTF-8 BOM
    # which causes configparser to misread the first section header.
    try:
        text = CONFIG_PATH.read_text(encoding="utf-8-sig")  # utf-8-sig strips BOM
        cfg.read_string(text)
    except Exception:
        cfg.read(CONFIG_PATH)  # fallback
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

        # Detect provider — Telnyx takes priority if api_key is set
        telnyx_key = (
            config["telnyx"].get("api_key", "").strip()
            if config.has_section("telnyx") else ""
        )
        self.use_telnyx = bool(telnyx_key)

        self.use_signalwire = (
            not self.use_telnyx and
            config.has_section("signalwire") and
            bool(config["signalwire"].get("space_url", "").strip())
        )

        if self.use_telnyx:
            self.telnyx_api_key  = telnyx_key
            self.telnyx_from     = config["telnyx"].get("from_number", "").strip()
            if self.telnyx_from:
                self.from_number = self.telnyx_from  # override from number
            self.provider = "Telnyx"
            self.logger.info("Provider: Telnyx (from=%s)", self.from_number)
        elif self.use_signalwire:
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

        if agent_mode == "voicemail_blast":
            # Point url directly to /connect — plays voicemail immediately on answer.
            # No AMD needed: we play the voicemail regardless of human or machine.
            # This avoids the AMD timeout causing no-answer before playback starts.
            call_params["url"] = f"{webhook_base}/connect"
            # Keep AMD as async so we can log human vs machine, but don't block on it
            call_params["machine_detection"] = "DetectMessageEnd"
            call_params["machine_detection_timeout"] = amd_timeout
            call_params["async_amd"] = "true"
            call_params["async_amd_status_callback"] = f"{webhook_base}/connect"
            call_params["async_amd_status_callback_method"] = "POST"
        elif enable_amd:
            call_params["machine_detection"] = "DetectMessageEnd"
            call_params["machine_detection_timeout"] = amd_timeout
            call_params["async_amd"] = "true"
            call_params["async_amd_status_callback"] = f"{webhook_base}/connect"
            call_params["async_amd_status_callback_method"] = "POST"

        try:
            if self.use_telnyx:
                sid = self._call_via_telnyx(call_params)
            elif self.use_signalwire:
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
            err_str = str(e)
            # Rate limit hit — wait and retry once
            if "rate" in err_str.lower() or "429" in err_str or "30022" in err_str:
                self.logger.warning(
                    "Rate limit hit for %s (%s) — waiting 5s then retrying", name, phone
                )
                time.sleep(5)
                try:
                    if self.use_telnyx:
                        sid = self._call_via_telnyx(call_params)
                    elif self.use_signalwire:
                        sid = self._call_via_signalwire(call_params)
                    else:
                        call = self.client.calls.create(**call_params)
                        sid = call.sid
                    if sid:
                        self.logger.info("Retry succeeded: SID=%s to=%s name=%s", sid, phone, name)
                        with self._lock:
                            self._active_calls[sid] = contact
                    return sid
                except Exception as e2:
                    self.logger.error("Retry also failed for %s (%s): %s", name, phone, e2)
                    return None
            self.logger.error("Failed to dial %s (%s): %s", name, phone, e)
            return None

    def _call_via_signalwire(self, call_params: dict) -> str | None:
        """Make outbound call via SignalWire Compatibility REST API."""
        import requests as req

        url = f"{self.sw_base_url}/Accounts/{self.account_sid}/Calls.json"

        # Core required params
        data: list[tuple[str, str]] = [
            ("To",     call_params["to"]),
            ("From",   call_params["from_"]),
            ("Url",    call_params["url"]),
            ("Timeout", str(call_params.get("timeout", 20))),
        ]

        # Status callback
        if call_params.get("status_callback"):
            data.append(("StatusCallback", call_params["status_callback"]))
            data.append(("StatusCallbackMethod", "POST"))
            for ev in call_params.get("status_callback_event", []):
                data.append(("StatusCallbackEvent", ev))

        # AMD params
        if "machine_detection" in call_params:
            data.append(("MachineDetection", call_params["machine_detection"]))
            data.append(("MachineDetectionTimeout", str(call_params.get("machine_detection_timeout", 30))))
            data.append(("AsyncAmd", "true"))
            if call_params.get("async_amd_status_callback"):
                data.append(("AsyncAmdStatusCallback", call_params["async_amd_status_callback"]))
                data.append(("AsyncAmdStatusCallbackMethod", "POST"))

        self.logger.info("SignalWire POST to %s with To=%s From=%s Url=%s",
                         url, call_params["to"], call_params["from_"], call_params["url"])

        resp = req.post(
            url,
            data=data,
            auth=(self.account_sid, self.auth_token),
            timeout=10,
        )
        if not resp.ok:
            body = resp.text
            self.logger.error(
                "SignalWire %s error — body: %s", resp.status_code, body
            )
            # Surface rate limit clearly
            if resp.status_code in (429, 422) and ("rate" in body.lower() or "30022" in body):
                raise Exception(f"Rate limit exceeded (HTTP {resp.status_code}): {body}")
        resp.raise_for_status()
        result = resp.json()
        return result.get("sid") or result.get("Sid", "")

    def _call_via_telnyx(self, call_params: dict) -> str | None:
        """Make outbound call via Telnyx API v2."""
        import requests as req

        url = "https://api.telnyx.com/v2/calls"
        webhook_base = call_params["url"].rsplit("/", 1)[0]  # base without path

        # Telnyx uses a JSON body — completely different from Twilio's form params
        payload = {
            "to": call_params["to"],
            "from": call_params["from_"],
            "connection_id": "",          # filled from config if set
            "webhook_url": call_params["url"],
            "webhook_url_method": "POST",
            "timeout_secs": call_params.get("timeout", 20),
            "record_channels": "none",
        }

        # Connection ID (Telnyx credential/SIP connection) — optional
        cfg = load_config()
        connection_id = cfg["telnyx"].get("connection_id", "").strip() if cfg.has_section("telnyx") else ""
        if connection_id:
            payload["connection_id"] = connection_id
        else:
            del payload["connection_id"]

        # AMD — Telnyx calls it answering_machine_detection
        if "machine_detection" in call_params:
            payload["answering_machine_detection"] = "detect_beep"
            payload["answering_machine_detection_config"] = {
                "total_analysis_time_millis": call_params.get("machine_detection_timeout", 30) * 1000,
                "after_greeting_silence_millis": 800,
                "between_words_silence_millis": 50,
                "greeting_duration_millis": 3500,
                "initial_silence_millis": 3000,
                "maximum_number_of_words": 5,
                "maximum_word_length_millis": 5000,
                "silence_threshold": 256,
                "greeting_total_analysis_time_millis": 7500,
                "greeting_silence_duration_millis": 2000,
            }
            # Telnyx fires AMD result via webhook — same /connect endpoint
            payload["answering_machine_detection_webhook_url"] = call_params.get(
                "async_amd_status_callback", call_params["url"]
            )

        # Status callback via webhook
        if call_params.get("status_callback"):
            payload["webhook_url"] = call_params["url"]

        self.logger.info("Telnyx POST to %s with to=%s from=%s url=%s",
                         url, call_params["to"], call_params["from_"], call_params["url"])

        resp = req.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self.telnyx_api_key}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        if not resp.ok:
            body = resp.text
            self.logger.error("Telnyx %s error — body: %s", resp.status_code, body)
            if resp.status_code == 429:
                raise Exception(f"Rate limit exceeded (HTTP 429): {body}")
        resp.raise_for_status()
        result = resp.json()
        # Telnyx returns {"data": {"call_control_id": "...", "call_leg_id": "..."}}
        data = result.get("data", {})
        return data.get("call_control_id") or data.get("call_leg_id", "")

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
