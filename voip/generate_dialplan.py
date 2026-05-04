"""
generate_dialplan.py — Asterisk extensions.conf dialplan generator.

Provides:
  generate_dialplan(extensions, trunk_name, did) -> str
    Generates a complete extensions.conf with [general], [globals],
    [internal], and [outbound] contexts.

  generate_dialplan_with_rotation(extensions, trunk_name, dids) -> str
    Generates a dialplan with round-robin DID rotation across a pool of
    verified DIDs. Each outbound call uses the next DID in the pool.

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

# Valid internal extension range (101–105 per requirements)
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


def _validate_did_pool(dids: list[str]) -> None:
    """Raise ValueError if the DID pool is empty or any DID is invalid E.164."""
    if not dids:
        raise ValueError("DID pool must not be empty.")
    for did in dids:
        _validate_did(did)


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


def _globals_section(dids: list[str]) -> str:
    """
    Return the [globals] section with DID pool variables for rotation.

    Sets:
      DID_COUNT   — total number of DIDs in the pool
      DID_INDEX   — current rotation index (starts at 0)
      DID_0..N    — each DID in the pool

    Requirements: 5.5, 6.1, 6.2
    """
    lines: list[str] = [
        "[globals]",
        f"DID_COUNT={len(dids)}",
        "DID_INDEX=0",
    ]
    for i, did in enumerate(dids):
        lines.append(f"DID_{i}={did}")
    return "\n".join(lines)


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
    Return the [outbound] context with a single fixed DID.

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


def _outbound_rotation_section(trunk_name: str) -> str:
    """
    Return the [outbound] context with round-robin DID rotation.

    On each outbound call:
      1. Read current DID_INDEX from globals
      2. Pick DID_{INDEX} as the outbound caller ID
      3. Increment index, wrap around at DID_COUNT (modulo)
      4. Dial through the trunk with the selected DID

    This cycles through all purchased DIDs evenly across calls.

    Requirements: 5.5, 6.1, 6.2, 11.2, 11.3, 11.4, 11.6
    """
    lines: list[str] = [
        "[outbound]",
        "; Round-robin DID rotation — picks next DID from pool on each call",
        "",
        "; US/Canada 11-digit numbers",
        "exten => _1NXXNXXXXXX,1,NoOp(Outbound US call to ${EXTEN})",
        "exten => _1NXXNXXXXXX,2,Set(CURRENT_INDEX=${GLOBAL(DID_INDEX)})",
        "exten => _1NXXNXXXXXX,3,Set(SELECTED_DID=${GLOBAL(DID_${CURRENT_INDEX})})",
        "exten => _1NXXNXXXXXX,4,Set(GLOBAL(DID_INDEX)=$[( ${CURRENT_INDEX} + 1 ) % ${GLOBAL(DID_COUNT)}])",
        "exten => _1NXXNXXXXXX,5,Set(CALLERID(num)=${SELECTED_DID})",
        "exten => _1NXXNXXXXXX,6,NoOp(Using DID ${SELECTED_DID} for call to ${EXTEN})",
        f"exten => _1NXXNXXXXXX,7,Dial(PJSIP/${{EXTEN}}@{trunk_name})",
        "exten => _1NXXNXXXXXX,8,Hangup()",
        "",
        "; International E.164 numbers",
        "exten => _+.,1,NoOp(International call to ${EXTEN})",
        "exten => _+.,2,Set(CURRENT_INDEX=${GLOBAL(DID_INDEX)})",
        "exten => _+.,3,Set(SELECTED_DID=${GLOBAL(DID_${CURRENT_INDEX})})",
        "exten => _+.,4,Set(GLOBAL(DID_INDEX)=$[( ${CURRENT_INDEX} + 1 ) % ${GLOBAL(DID_COUNT)}])",
        "exten => _+.,5,Set(CALLERID(num)=${SELECTED_DID})",
        "exten => _+.,6,NoOp(Using DID ${SELECTED_DID} for call to ${EXTEN})",
        f"exten => _+.,7,Dial(PJSIP/${{EXTEN}}@{trunk_name})",
        "exten => _+.,8,Hangup()",
        "",
        "; Emergency — always use first DID, no rotation",
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
    Generate a complete Asterisk extensions.conf dialplan string
    with a single fixed outbound DID.

    Parameters
    ----------
    extensions:
        List of extension numbers to provision (must be in range 101–105).
    trunk_name:
        Name of the SIP trunk endpoint (e.g. "twilio-trunk").
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
    return "\n\n".join(sections) + "\n"


def generate_dialplan_with_rotation(
    extensions: list[str],
    trunk_name: str,
    dids: list[str],
) -> str:
    """
    Generate a complete Asterisk extensions.conf dialplan string
    with round-robin DID rotation across a pool of verified DIDs.

    Each outbound call automatically picks the next DID from the pool,
    cycling through all numbers evenly.

    Parameters
    ----------
    extensions:
        List of extension numbers to provision (must be in range 101–105).
    trunk_name:
        Name of the SIP trunk endpoint (e.g. "twilio-trunk").
    dids:
        List of verified E.164 DIDs to rotate through (e.g.
        ["+12025551001", "+12025551002", "+12025551003"]).
        Must contain at least one DID.

    Returns
    -------
    str
        Complete extensions.conf content with rotation logic.

    Raises
    ------
    ValueError
        If any extension is outside 101–105, the DID pool is empty,
        or any DID is not valid E.164.
    """
    _validate_extensions(extensions)
    _validate_did_pool(dids)

    sections = [
        _general_section(),
        _globals_section(dids),
        _internal_section(),
        _outbound_rotation_section(trunk_name),
    ]
    return "\n\n".join(sections) + "\n"


def write_extensions_conf(
    extensions: list[str],
    trunk_name: str,
    did: str,
    path: str | Path = _DEFAULT_EXTENSIONS_CONF,
) -> Path:
    """
    Generate the dialplan with a single DID and write it to *path*.

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


def write_extensions_conf_with_rotation(
    extensions: list[str],
    trunk_name: str,
    dids: list[str],
    path: str | Path = _DEFAULT_EXTENSIONS_CONF,
) -> Path:
    """
    Generate the dialplan with round-robin DID rotation and write it to *path*.

    Parameters
    ----------
    extensions:
        List of extension numbers (101–105).
    trunk_name:
        SIP trunk name used in Dial() application arguments.
    dids:
        List of verified E.164 DIDs to rotate through.
    path:
        Destination file path (default: /etc/asterisk/extensions.conf).

    Returns
    -------
    Path
        The resolved Path of the written file.
    """
    content = generate_dialplan_with_rotation(extensions, trunk_name, dids)
    return write_file(path, content)
