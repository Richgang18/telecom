"""
setup_fail2ban.py — Install and configure Fail2Ban for Asterisk (inside WSL2).

Installs fail2ban, writes the Asterisk filter and jail configuration files,
enables the fail2ban service, and validates the filter regex against a sample
Asterisk log line using fail2ban-regex.

The filter regex matches Asterisk authentication failure log lines from
/var/log/asterisk/messages, including:

  Pattern 1 — PJSIP distributor (chan_pjsip) failures:
    [2024-01-15 10:23:45] NOTICE[1234] res_pjsip/pjsip_distributor.c:
        Request 'REGISTER' from '"101" <sip:101@pbx.local>'
        failed for '1.2.3.4:5061' (callid: abc123) - No matching endpoint found

  Pattern 2 — chan_sip registration failures:
    [2024-01-15 10:23:45] NOTICE[1234] chan_sip.c:
        Registration from '"101" <sip:101@pbx.local>'
        failed for '1.2.3.4' - Wrong password

  Pattern 3 — PJSIP registrar failures:
    [2024-01-01 12:00:00] NOTICE[1234] res_pjsip_registrar.c:
        Registration failed for '101' - Wrong password

  Pattern 4 — Security event failures (FailedACL / InvalidPassword):
    [2024-01-01 12:00:00] SECURITY[1234] res_security_log.c:
        SecurityEvent="FailedACL",...

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Regex constant — matches Asterisk authentication failure log lines
# ---------------------------------------------------------------------------

# This regex is used in the fail2ban filter.  It matches four distinct
# Asterisk failure patterns written to /var/log/asterisk/messages.
#
# The fail2ban <HOST> tag captures the offending IP address.
#
# Pattern 1 (PJSIP distributor): IP appears after "failed for '"
#   Request 'REGISTER' from '...' failed for '<HOST>:<port>' (callid: ...) - <reason>
#
# Pattern 2 (chan_sip): IP appears after "failed for '"
#   Registration from '...' failed for '<HOST>' - <reason>
#   Registration from '...' failed for '<HOST>:<port>' - <reason>
#
# Pattern 3 (PJSIP registrar): no IP in the line (uses log prefix)
#   Registration failed for '...' - Wrong password
#
# Pattern 4 (Security event): IP in RemoteAddress field
#   SecurityEvent="FailedACL",...,RemoteAddress=".../<HOST>/..."
ASTERISK_FILTER_REGEX: str = (
    r"(%(__prefix_line)s|\[.*?\] (?:NOTICE|SECURITY)\[\d+\] \S+: )"
    r"(?:"
    # Pattern 1: PJSIP distributor — Request '...' from '...' failed for '<HOST>:port' (...) - reason
    r"Request '\w+' from '.*?' failed for '<HOST>(?::\d+)?' (?:\(callid: [^)]+\) )?- \S.*"
    r"|"
    # Pattern 2: chan_sip — Registration from '...' failed for '<HOST>' or '<HOST>:port' - reason
    r"Registration from '.*?' failed for '<HOST>(?::\d+)?' - \S.*"
    r"|"
    # Pattern 3: PJSIP registrar — Registration failed for '...' - Wrong password
    r"Registration failed for '.*?' - Wrong password"
    r"|"
    # Pattern 4: Security event — SecurityEvent="FailedACL" or "InvalidPassword"
    r'SecurityEvent="(?:FailedACL|InvalidPassword)".*?RemoteAddress="[^"]*?/(?:<HOST>)/\d+"'
    r")"
)

# ---------------------------------------------------------------------------
# Configuration file contents
# ---------------------------------------------------------------------------

FILTER_CONF_CONTENT: str = f"""\
# Fail2Ban filter for Asterisk PBX
# Matches authentication failure log lines from /var/log/asterisk/messages
#
# Requirements: 9.1, 9.5

[INCLUDES]
before = common.conf

[Definition]
_daemon = asterisk

failregex = {ASTERISK_FILTER_REGEX}

ignoreregex =
"""

JAIL_CONF_CONTENT: str = """\
# Fail2Ban jail configuration for Asterisk PBX
#
# Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6

[asterisk]
enabled  = true
port     = 5060,5061
filter   = asterisk
logpath  = /var/log/asterisk/messages
maxretry = 5
findtime = 60
bantime  = 3600
action   = iptables-allports
"""

# ---------------------------------------------------------------------------
# Default file paths
# ---------------------------------------------------------------------------

DEFAULT_FILTER_PATH: str = "/etc/fail2ban/filter.d/asterisk.conf"
DEFAULT_JAIL_PATH: str = "/etc/fail2ban/jail.d/asterisk.conf"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_filter_conf(path: str = DEFAULT_FILTER_PATH) -> Path:
    """
    Write the Fail2Ban Asterisk filter configuration to *path*.

    Creates parent directories as needed.

    Parameters
    ----------
    path:
        Destination file path.  Defaults to
        ``/etc/fail2ban/filter.d/asterisk.conf``.

    Returns
    -------
    Path
        The resolved Path object of the written file.

    Raises
    ------
    OSError
        If the file cannot be written.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(FILTER_CONF_CONTENT, encoding="utf-8")
    return target


def write_jail_conf(path: str = DEFAULT_JAIL_PATH) -> Path:
    """
    Write the Fail2Ban Asterisk jail configuration to *path*.

    Creates parent directories as needed.

    Parameters
    ----------
    path:
        Destination file path.  Defaults to
        ``/etc/fail2ban/jail.d/asterisk.conf``.

    Returns
    -------
    Path
        The resolved Path object of the written file.

    Raises
    ------
    OSError
        If the file cannot be written.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(JAIL_CONF_CONTENT, encoding="utf-8")
    return target


def enable_fail2ban() -> None:
    """
    Enable and restart the fail2ban systemd service.

    Runs ``systemctl enable fail2ban`` followed by
    ``systemctl restart fail2ban``.

    Raises
    ------
    subprocess.CalledProcessError
        If either systemctl command exits with a non-zero status.
    """
    subprocess.run(["systemctl", "enable", "fail2ban"], check=True)
    subprocess.run(["systemctl", "restart", "fail2ban"], check=True)


def validate_filter(filter_path: str, log_sample: str) -> subprocess.CompletedProcess:
    """
    Validate the fail2ban filter at *filter_path* against *log_sample*.

    Runs ``fail2ban-regex <log_sample> <filter_path>`` via subprocess and
    returns the completed process result.  The caller can inspect
    ``result.returncode`` to determine whether the filter matched.

    Parameters
    ----------
    filter_path:
        Path to the fail2ban filter configuration file.
    log_sample:
        A single Asterisk log line (or path to a log file) to test against
        the filter.

    Returns
    -------
    subprocess.CompletedProcess
        The result of the ``fail2ban-regex`` invocation.

    Raises
    ------
    subprocess.CalledProcessError
        If ``fail2ban-regex`` exits with a non-zero status and
        ``check=True`` is used.  (This function does NOT pass ``check=True``
        so the caller can inspect the return code.)
    """
    result = subprocess.run(
        ["fail2ban-regex", log_sample, filter_path],
        capture_output=True,
        text=True,
    )
    return result


def install_fail2ban() -> None:
    """
    Install fail2ban via apt-get (non-interactive).

    Raises
    ------
    subprocess.CalledProcessError
        If the apt-get command fails.
    """
    subprocess.run(
        ["apt-get", "install", "-y", "fail2ban"],
        check=True,
        env={"DEBIAN_FRONTEND": "noninteractive"},
    )


def main() -> None:
    """
    Orchestrate all Fail2Ban setup steps:

    1. Install fail2ban via apt.
    2. Write the Asterisk filter configuration.
    3. Write the Asterisk jail configuration.
    4. Enable and restart the fail2ban service.
    5. Validate the filter with a sample log line.
    """
    print("Step 1: Installing fail2ban...")
    install_fail2ban()
    print("  fail2ban installed.")

    print("Step 2: Writing filter configuration...")
    filter_path = write_filter_conf()
    print(f"  Filter written to {filter_path}")

    print("Step 3: Writing jail configuration...")
    jail_path = write_jail_conf()
    print(f"  Jail written to {jail_path}")

    print("Step 4: Enabling and restarting fail2ban service...")
    enable_fail2ban()
    print("  fail2ban service enabled and restarted.")

    print("Step 5: Validating filter with sample log line...")
    sample = (
        "[2024-01-15 10:23:45] NOTICE[1234] res_pjsip/pjsip_distributor.c: "
        "Request 'REGISTER' from '\"101\" <sip:101@pbx.local>' "
        "failed for '1.2.3.4:5061' (callid: abc123) - No matching endpoint found"
    )
    result = validate_filter(str(filter_path), sample)
    if result.returncode == 0:
        print("  Filter validation passed.")
    else:
        print(f"  WARNING: Filter validation returned code {result.returncode}")
        print(f"  stdout: {result.stdout}")
        print(f"  stderr: {result.stderr}")

    print("\nFail2Ban setup complete.")


if __name__ == "__main__":
    main()
