"""
generate_pjsip.py — Generates pjsip.conf for Asterisk SIP endpoints.

Provides generate_endpoint_config(extensions: list[dict]) -> str which
validates endpoint data and produces a complete pjsip.conf file content
for extensions 101–105.

The generated config is written to /etc/asterisk/pjsip.conf using the
write_secure_file utility from config_writer.py.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 7.1, 7.5, 12.1, 13.4
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — allow running from workspace root or voip/ directory
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))

from config_writer import write_secure_file

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PJSIP_CONF_PATH: str = "/etc/asterisk/pjsip.conf"

CERT_FILE: str = "/etc/asterisk/keys/fullchain.pem"
PRIV_KEY_FILE: str = "/etc/asterisk/keys/privkey.pem"

VALID_EXTENSION_MIN: int = 101
VALID_EXTENSION_MAX: int = 105

PASSWORD_MIN_LENGTH: int = 12

# E.164: starts with +, followed by 1–15 digits
_E164_PATTERN: re.Pattern[str] = re.compile(r"^\+\d{1,15}$")

# Mixed alphanumeric: must contain at least one letter AND at least one digit
_HAS_LETTER: re.Pattern[str] = re.compile(r"[A-Za-z]")
_HAS_DIGIT: re.Pattern[str] = re.compile(r"\d")


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_extension(extension: int | str) -> int:
    """
    Validate that *extension* is an integer in the range 101–105.

    Returns the integer value on success.

    Raises
    ------
    ValueError
        If the extension is outside the valid range.
    TypeError
        If the extension cannot be converted to an integer.
    """
    try:
        ext_int = int(extension)
    except (ValueError, TypeError) as exc:
        raise TypeError(
            f"Extension must be an integer, got {extension!r}"
        ) from exc

    if not (VALID_EXTENSION_MIN <= ext_int <= VALID_EXTENSION_MAX):
        raise ValueError(
            f"Extension {ext_int} is out of range "
            f"({VALID_EXTENSION_MIN}–{VALID_EXTENSION_MAX})"
        )
    return ext_int


def _validate_password(password: str) -> None:
    """
    Validate that *password* meets the minimum security requirements:
      - At least 12 characters
      - Contains at least one letter (A–Z or a–z)
      - Contains at least one digit (0–9)

    Raises
    ------
    ValueError
        If the password does not meet the requirements.
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters long "
            f"(got {len(password)})"
        )
    if not _HAS_LETTER.search(password):
        raise ValueError(
            "Password must contain at least one letter (A–Z or a–z)"
        )
    if not _HAS_DIGIT.search(password):
        raise ValueError(
            "Password must contain at least one digit (0–9)"
        )


def _validate_e164(caller_id_num: str) -> None:
    """
    Validate that *caller_id_num* is in E.164 format (starts with +,
    followed by 1–15 digits).

    Raises
    ------
    ValueError
        If the number is not valid E.164.
    """
    if not _E164_PATTERN.match(caller_id_num):
        raise ValueError(
            f"caller_id_num {caller_id_num!r} is not valid E.164 format "
            "(must start with '+' followed by 1–15 digits)"
        )


def _validate_endpoint(ep: dict) -> None:
    """
    Validate a single endpoint dict.

    Required keys: extension, display_name, password, caller_id_num.

    Raises
    ------
    KeyError
        If a required key is missing.
    ValueError / TypeError
        If any field fails validation.
    """
    for key in ("extension", "display_name", "password", "caller_id_num"):
        if key not in ep:
            raise KeyError(f"Endpoint dict is missing required key: {key!r}")

    _validate_extension(ep["extension"])
    _validate_password(ep["password"])
    _validate_e164(ep["caller_id_num"])


# ---------------------------------------------------------------------------
# Config generation helpers
# ---------------------------------------------------------------------------


def _transport_section() -> str:
    """Return the [transport-tls] section string."""
    return (
        "[transport-tls]\n"
        "type=transport\n"
        "protocol=tls\n"
        "bind=0.0.0.0:5061\n"
        f"cert_file={CERT_FILE}\n"
        f"priv_key_file={PRIV_KEY_FILE}\n"
        "method=tlsv1_2\n"
    )


def _endpoint_sections(ep: dict) -> str:
    """
    Return the [<ext>], [auth<ext>], and [aor<ext>] sections for one endpoint.
    """
    ext = int(ep["extension"])
    display_name = ep["display_name"]
    password = ep["password"]
    caller_id_num = ep["caller_id_num"]

    endpoint_section = (
        f"[{ext}]\n"
        "type=endpoint\n"
        "transport=transport-tls\n"
        "context=internal\n"
        "disallow=all\n"
        "allow=ulaw,alaw\n"
        f"auth=auth{ext}\n"
        f"aors=aor{ext}\n"
        f"callerid={display_name} <{caller_id_num}>\n"
        "media_encryption=sdes\n"
        "dtmf_mode=rfc4733\n"
        "rtp_symmetric=yes\n"
        "force_rport=yes\n"
        "direct_media=no\n"
    )

    auth_section = (
        f"[auth{ext}]\n"
        "type=auth\n"
        "auth_type=userpass\n"
        f"username={ext}\n"
        f"password={password}\n"
    )

    aor_section = (
        f"[aor{ext}]\n"
        "type=aor\n"
        "max_contacts=1\n"
    )

    return endpoint_section + "\n" + auth_section + "\n" + aor_section


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_endpoint_config(extensions: list[dict]) -> str:
    """
    Generate a complete pjsip.conf content string for the given extensions.

    Parameters
    ----------
    extensions:
        A list of endpoint dicts, each with keys:
          - extension     : int or str, must be in range 101–105
          - display_name  : str, human-readable name
          - password      : str, ≥ 12 mixed alphanumeric characters
          - caller_id_num : str, E.164 format (e.g. "+12025551001")

    Returns
    -------
    str
        The complete pjsip.conf content.

    Raises
    ------
    ValueError
        If any extension number is out of range, any password is invalid,
        any caller_id_num is not E.164, or extension numbers are not unique.
    KeyError
        If a required key is missing from an endpoint dict.
    TypeError
        If an extension value cannot be converted to an integer.
    """
    if not extensions:
        raise ValueError("extensions list must not be empty")

    # Validate all endpoints first
    for ep in extensions:
        _validate_endpoint(ep)

    # Check uniqueness of extension numbers (Requirement 2.3)
    ext_numbers = [int(ep["extension"]) for ep in extensions]
    if len(ext_numbers) != len(set(ext_numbers)):
        seen: set[int] = set()
        duplicates: list[int] = []
        for n in ext_numbers:
            if n in seen:
                duplicates.append(n)
            seen.add(n)
        raise ValueError(
            f"Duplicate extension numbers found: {duplicates}"
        )

    # Build the config string
    parts: list[str] = [_transport_section()]

    for ep in extensions:
        parts.append("")  # blank line between sections
        parts.append(_endpoint_sections(ep))

    return "\n".join(parts)


def write_pjsip_conf(
    extensions: list[dict],
    path: str = PJSIP_CONF_PATH,
) -> Path:
    """
    Generate pjsip.conf content and write it to *path*.

    Uses write_secure_file (mode 0o640) because the file contains passwords.

    Parameters
    ----------
    extensions:
        See generate_endpoint_config().
    path:
        Destination path (default: /etc/asterisk/pjsip.conf).

    Returns
    -------
    Path
        The resolved Path of the written file.
    """
    content = generate_endpoint_config(extensions)
    return write_secure_file(path, content)


# ---------------------------------------------------------------------------
# Trunk config validation helpers
# ---------------------------------------------------------------------------


def _validate_trunk_codecs(codecs: list[str]) -> None:
    """
    Validate that *codecs* includes at least one of 'ulaw' or 'alaw'.

    Raises
    ------
    ValueError
        If neither 'ulaw' nor 'alaw' is present in the codec list.
    """
    if not codecs:
        raise ValueError(
            "codecs list must not be empty; must include at least 'ulaw' or 'alaw'"
        )
    normalised = [c.strip().lower() for c in codecs]
    if "ulaw" not in normalised and "alaw" not in normalised:
        raise ValueError(
            f"codecs {codecs!r} must include at least 'ulaw' or 'alaw' "
            "for PSTN compatibility (Requirement 5.6, 12.3)"
        )


def _validate_trunk(trunk: dict) -> None:
    """
    Validate a trunk configuration dict.

    Required keys: trunk_name, host, username, password, from_user,
                   from_domain, transport, codecs.

    Raises
    ------
    KeyError
        If a required key is missing.
    ValueError
        If from_user is not E.164 or codecs lacks ulaw/alaw.
    """
    required_keys = (
        "trunk_name",
        "host",
        "username",
        "password",
        "from_user",
        "from_domain",
        "transport",
        "codecs",
    )
    for key in required_keys:
        if key not in trunk:
            raise KeyError(f"Trunk dict is missing required key: {key!r}")

    # Reuse the existing E.164 validator for from_user (Requirement 6.1, 6.2)
    _validate_e164(trunk["from_user"])

    # Codec must include ulaw or alaw (Requirement 5.6, 12.3)
    _validate_trunk_codecs(trunk["codecs"])


# ---------------------------------------------------------------------------
# Trunk config generation
# ---------------------------------------------------------------------------


def generate_trunk_config(trunk: dict) -> str:
    """
    Generate pjsip.conf sections for a SIP trunk.

    Produces four INI-style sections:
      - [<trunk_name>-reg]   type=registration  (expiry=60)
      - [<trunk_name>-auth]  type=auth
      - [<trunk_name>-aop]   type=aor
      - [<trunk_name>]       type=endpoint      (qualify_frequency=30,
                                                  from_user=<verified DID>)

    Parameters
    ----------
    trunk:
        A dict with keys:
          - trunk_name  : str  — identifier (e.g. "voipms-trunk")
          - host        : str  — provider SIP domain (e.g. "sip.voip.ms")
          - username    : str  — trunk account username
          - password    : str  — trunk account password
          - from_user   : str  — verified DID in E.164 format (e.g. "+12025551000")
          - from_domain : str  — provider domain for From header
          - transport   : str  — transport name (e.g. "transport-tls")
          - codecs      : list[str] — must include 'ulaw' or 'alaw'

    Returns
    -------
    str
        The trunk config block (four INI sections, newline-separated).

    Raises
    ------
    KeyError
        If a required key is missing from *trunk*.
    ValueError
        If from_user is not valid E.164 or codecs lacks ulaw/alaw.

    Requirements: 5.1, 5.6, 6.1, 6.2, 6.3, 12.3
    """
    _validate_trunk(trunk)

    name = trunk["trunk_name"]
    host = trunk["host"]
    username = trunk["username"]
    password = trunk["password"]
    from_user = trunk["from_user"]
    from_domain = trunk["from_domain"]
    transport = trunk["transport"]

    registration_section = (
        f"[{name}-reg]\n"
        "type=registration\n"
        f"outbound_auth={name}-auth\n"
        f"server_uri=sip:{host}\n"
        f"client_uri=sip:{from_user}@{host}\n"
        "expiry=60\n"
    )

    auth_section = (
        f"[{name}-auth]\n"
        "type=auth\n"
        "auth_type=userpass\n"
        f"username={username}\n"
        f"password={password}\n"
    )

    aop_section = (
        f"[{name}-aop]\n"
        "type=aor\n"
        f"contact=sip:{host}\n"
    )

    endpoint_section = (
        f"[{name}]\n"
        "type=endpoint\n"
        f"transport={transport}\n"
        "context=from-trunk\n"
        "disallow=all\n"
        "allow=ulaw,alaw\n"
        f"outbound_auth={name}-auth\n"
        f"aors={name}-aop\n"
        f"from_user={from_user}\n"
        f"from_domain={from_domain}\n"
        "qualify_frequency=30\n"
    )

    return (
        registration_section
        + "\n"
        + auth_section
        + "\n"
        + aop_section
        + "\n"
        + endpoint_section
    )


def append_trunk_config(
    trunk: dict,
    path: str = PJSIP_CONF_PATH,
) -> Path:
    """
    Append the trunk config block to *path* (default: /etc/asterisk/pjsip.conf).

    The trunk config is generated via generate_trunk_config() and appended
    to the existing file.  If the file does not exist it is created.

    Parameters
    ----------
    trunk:
        See generate_trunk_config().
    path:
        Destination path (default: /etc/asterisk/pjsip.conf).

    Returns
    -------
    Path
        The resolved Path of the written file.

    Requirements: 5.1, 6.1, 6.2, 6.3
    """
    content = generate_trunk_config(trunk)
    target = Path(path)

    # Ensure parent directories exist
    target.parent.mkdir(parents=True, exist_ok=True)

    # Append (or create) the file
    with target.open("a", encoding="utf-8") as fh:
        # Ensure we start on a new line
        fh.write("\n" + content)

    return target


# ---------------------------------------------------------------------------
# CLI entry point (run inside WSL2)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Example: generate config for all 5 extensions
    sample_extensions = [
        {
            "extension": 101,
            "display_name": "Alice Smith",
            "password": "Str0ngP@ssw0rd1",
            "caller_id_num": "+12025551001",
        },
        {
            "extension": 102,
            "display_name": "Bob Jones",
            "password": "Str0ngP@ssw0rd2",
            "caller_id_num": "+12025551002",
        },
        {
            "extension": 103,
            "display_name": "Carol White",
            "password": "Str0ngP@ssw0rd3",
            "caller_id_num": "+12025551003",
        },
        {
            "extension": 104,
            "display_name": "Dave Brown",
            "password": "Str0ngP@ssw0rd4",
            "caller_id_num": "+12025551004",
        },
        {
            "extension": 105,
            "display_name": "Eve Davis",
            "password": "Str0ngP@ssw0rd5",
            "caller_id_num": "+12025551005",
        },
    ]

    written = write_pjsip_conf(sample_extensions)
    print(f"Written: {written}")
