"""
generate_dialplan.py — Asterisk extensions.conf dialplan generator.

Provides:
  generate_dialplan(extensions, trunk_name, did) -> str
    Generates a complete extensions.conf with [general], [internal], and
    [outbound] contexts.

  write_extensions_conf(extensions, trunk_name, did, path) -> Path
    Writes the generated dialplan to disk using config_writer.write_file.

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 5.2, 5.3, 5.4, 5.5,
              11.1, 11.2, 11.3, 11.4, 11.5, 11.6
"""

from __future__ import annotations

import re
from pathlib import Path

from config_writer import write_file

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_EXTENSIONS_CONF = "/etc/asterisk/extensions.conf"

# Valid internal extension range (101–105 per requirements, but the dialplan
# pattern _1XX covers 100–199; we validate the supplied list separately).
_VALID_EXTENSIONS = {str(n) for n in range(101, 106)}

# E.164 pattern: + followed by 1–15 digits
_E164_RE = re.compile(r"^\+\d{1,15}$")


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_extensions(extensions: list[str]) -> None:
    """Raise ValueError if any extension is outside 101–105."""
    for ext in extensions:
        if ext not in _VALID_EXTENSIONS:
            raise ValueError(
                f"Extension {ext!r} is not in the valid range 101–105. "
                f"Valid extensions: {sorted(_VALID_EXTENSIONS)}"
            )


def _validate_did(did: str) -> None:
    """Raise ValueError if *did* is not a valid E.164 number."""
    if not _E164_RE.match(did):
        raise ValueError(
            f"DID {did!r} is not a valid E.164 number. "
            "Expected format: +<1–15 digits> (e.g. +12025551000)"
        )


# ---------------------------------------------------------------------------
# Section generators
# ---------------------------------------------------------------------------


def _general_section() -> str:
    """Return the [general] section header."""
    return (
        "[general]\n"
        "static=yes\n"
        "writeprotect=no\n"
        "clearglobalvars=no\n"
    )


def _internal_section() -> str:
    """
    Return the [internal] context.

    Pattern _1XX routes to local PJSIP endpoints (extensions 100–199).
    A secondary catch-all for the same numeric range plays an invalid
    announcement for extensions not in 101–105.

    Requirements: 4.1, 4.3, 4.5, 4.6, 11.1
    """
    lines: list[str] = [
        "[internal]",
        "; Internal extensions 101-105",
        "exten => _1XX,1,NoOp(Internal call to ${EXTEN})",
        "exten => _1XX,2,Dial(PJSIP/${EXTEN},30)",
        "exten => _1XX,3,Hangup()",
        "",
        "; Invalid internal extension",
        "exten => _1[0-9][0-9],1,NoOp(Invalid extension ${EXTEN})",
        "exten => _1[0-9][0-9],2,Playback(invalid)",
        "exten => _1[0-9][0-9],3,Hangup()",
    ]
    return "\n".join(lines)


def _outbound_section(trunk_name: str, did: str) -> str:
    """
    Return the [outbound] context.

    Patterns:
      _1NXXNXXXXXX  — US/Canada 11-digit numbers (Requirements: 5.2, 5.3, 11.2)
      _+.           — International E.164 numbers  (Requirements: 5.2, 5.4, 11.3)
      911           — Emergency                    (Requirements: 11.4)
      _X.           — Catch-all invalid            (Requirements: 4.6, 11.5)

    Caller ID is overridden with the verified DID for all non-emergency
    outbound routes (Requirements: 5.5, 6.1, 6.2, 11.6).
    """
    lines: list[str] = [
        "[outbound]",
        "; US/Canada 11-digit numbers",
        f"exten => _1NXXNXXXXXX,1,NoOp(Outbound US call to ${{EXTEN}})",
        f"exten => _1NXXNXXXXXX,2,Set(CALLERID(num)={did})",
        f"exten => _1NXXNXXXXXX,3,Dial(PJSIP/${{EXTEN}}@{trunk_name})",
        "exten => _1NXXNXXXXXX,4,Hangup()",
        "",
        "; International E.164 numbers",
        f"exten => _+.,1,NoOp(International call to ${{EXTEN}})",
        f"exten => _+.,2,Set(CALLERID(num)={did})",
        f"exten => _+.,3,Dial(PJSIP/${{EXTEN}}@{trunk_name})",
        "exten => _+.,4,Hangup()",
        "",
        "; Emergency",
        "exten => 911,1,NoOp(Emergency call)",
        f"exten => 911,2,Dial(PJSIP/911@{trunk_name})",
        "exten => 911,3,Hangup()",
        "",
        "; Catch-all invalid numbers",
        "exten => _X.,1,NoOp(Invalid number ${EXTEN})",
        "exten => _X.,2,Playback(invalid)",
        "exten => _X.,3,Hangup()",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_dialplan(
    extensions: list[str],
    trunk_name: str,
    did: str,
) -> str:
    """
    Generate a complete Asterisk extensions.conf dialplan string.

    Parameters
    ----------
    extensions:
        List of extension numbers to provision (must be in range 101–105).
    trunk_name:
        Name of the SIP trunk endpoint (e.g. "voipms-trunk").
    did:
        Verified E.164 DID used as outbound caller ID (e.g. "+12025551000").

    Returns
    -------
    str
        Complete extensions.conf content ready to write to disk.

    Raises
    ------
    ValueError
        If any extension is outside 101–105, or *did* is not valid E.164.
    """
    _validate_extensions(extensions)
    _validate_did(did)

    sections = [
        _general_section(),
        _internal_section(),
        _outbound_section(trunk_name, did),
    ]
    # Join sections with a blank line between them, end with a trailing newline
    return "\n\n".join(sections) + "\n"


def write_extensions_conf(
    extensions: list[str],
    trunk_name: str,
    did: str,
    path: str | Path = _DEFAULT_EXTENSIONS_CONF,
) -> Path:
    """
    Generate the dialplan and write it to *path*.

    Parameters
    ----------
    extensions:
        List of extension numbers (101–105).
    trunk_name:
        SIP trunk name used in Dial() application arguments.
    did:
        Verified E.164 DID for outbound caller ID.
    path:
        Destination file path (default: /etc/asterisk/extensions.conf).

    Returns
    -------
    Path
        The resolved Path of the written file.
    """
    content = generate_dialplan(extensions, trunk_name, did)
    return write_file(path, content)
