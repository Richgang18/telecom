"""
voicemail_drop.py — Pre-recorded voicemail drop for unanswered calls.

When an outbound call is not answered (rings out or goes to voicemail),
Twilio POSTs to /no-answer. This module returns TwiML that plays the
pre-recorded voicemail audio file and hangs up.

The voicemail file must be publicly accessible via URL so Twilio can
fetch and play it. This module serves it from the webhook server or
uses a pre-uploaded URL.
"""

from __future__ import annotations

import configparser
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "config.ini"


def load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    try:
        text = CONFIG_PATH.read_text(encoding="utf-8-sig")
        cfg.read_string(text)
    except Exception:
        cfg.read(CONFIG_PATH)
    return cfg


def generate_voicemail_twiml(
    voicemail_url: str,
    delay: int = 2,
) -> str:
    """
    Generate TwiML that drops a pre-recorded voicemail.

    Pauses briefly (to let the recipient's voicemail greeting finish),
    then plays the pre-recorded message and hangs up.

    Parameters
    ----------
    voicemail_url:
        Publicly accessible URL to the voicemail audio file (MP3 or WAV).
        Twilio fetches this URL to play the audio.
    delay:
        Seconds to pause before playing the message. Default 2 seconds.

    Returns
    -------
    str
        TwiML XML string.
    """
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        f"  <Pause length=\"{delay}\"/>\n"
        f'  <Play>{voicemail_url}</Play>\n'
        "  <Hangup/>\n"
        "</Response>"
    )


def generate_no_answer_twiml(config: configparser.ConfigParser) -> str:
    """
    Generate TwiML for the /no-answer webhook endpoint.

    Reads voicemail config and returns the appropriate TwiML.
    If no voicemail file is configured, hangs up silently.

    Parameters
    ----------
    config:
        Parsed config.ini ConfigParser object.

    Returns
    -------
    str
        TwiML XML string.
    """
    cfg = config["voicemail"]
    webhook_base = config["twilio"]["webhook_base_url"].rstrip("/")
    voicemail_file = cfg.get("voicemail_file", "").strip()
    delay = int(cfg.get("voicemail_delay", "2"))

    if not voicemail_file:
        logger.warning("No voicemail_file configured — hanging up silently.")
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<Response>\n"
            "  <Hangup/>\n"
            "</Response>"
        )

    # Serve the voicemail file from the webhook server
    voicemail_url = f"{webhook_base}/voicemail-audio"
    logger.info("Voicemail drop: playing %s (delay=%ds)", voicemail_url, delay)
    return generate_voicemail_twiml(voicemail_url, delay)
