"""
setup_firewall.py — Apply iptables firewall rules inside WSL2.

Generates and applies a hardened iptables ruleset for the Asterisk VoIP
server running inside WSL2 (Ubuntu 22.04).  The ruleset enforces the inner
security perimeter described in the design document:

  - Default INPUT policy: DROP
  - Allow ESTABLISHED / RELATED connections
  - Allow loopback interface
  - Allow TCP 22 (SSH) from admin IP range
  - Allow TCP 5061 (SIP/TLS)
  - DROP TCP and UDP 5060 (plain SIP)
  - Allow UDP 10000–20000 (RTP)
  - Allow TCP 443 (HTTPS/AMI)
  - Default FORWARD policy: DROP

Rules are persisted via iptables-save and iptables-persistent so they
survive WSL2 restarts.

Requirements: 8.6, 8.7, 8.8, 8.9
"""

from __future__ import annotations

import subprocess
from typing import List

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

# Admin IP range allowed to SSH into the server.  Override this constant
# before calling generate_ruleset() if a different range is needed.
ADMIN_IP_RANGE: str = "10.0.0.0/8"

# Path where iptables-save output is written for persistence.
IPTABLES_RULES_PATH: str = "/etc/iptables/rules.v4"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_ruleset(admin_ip_range: str = ADMIN_IP_RANGE) -> List[List[str]]:
    """
    Return the complete iptables ruleset as a list of command argument lists.

    Each element is a list of strings suitable for passing directly to
    ``subprocess.run()`` (i.e. the argv list, *without* the leading
    ``"iptables"`` binary — callers should prepend it or use the list as-is
    depending on their invocation style).

    The ruleset is ordered so that permissive rules (ESTABLISHED/RELATED,
    loopback) appear before restrictive DROP rules, which is required for
    correct iptables evaluation.

    Parameters
    ----------
    admin_ip_range:
        CIDR notation for the IP range allowed to connect on TCP 22 (SSH).
        Defaults to the module-level ``ADMIN_IP_RANGE`` constant.

    Returns
    -------
    list[list[str]]
        Ordered list of iptables argv lists.
    """
    ruleset: List[List[str]] = [
        # 1. Flush existing INPUT rules
        ["iptables", "-F", "INPUT"],

        # 2. Set default INPUT policy to DROP
        ["iptables", "-P", "INPUT", "DROP"],

        # 3. Allow ESTABLISHED and RELATED connections (must come first)
        [
            "iptables", "-A", "INPUT",
            "-m", "state", "--state", "ESTABLISHED,RELATED",
            "-j", "ACCEPT",
        ],

        # 4. Allow loopback interface
        [
            "iptables", "-A", "INPUT",
            "-i", "lo",
            "-j", "ACCEPT",
        ],

        # 5. Allow TCP 22 (SSH) from admin IP range
        [
            "iptables", "-A", "INPUT",
            "-p", "tcp", "--dport", "22",
            "-s", admin_ip_range,
            "-j", "ACCEPT",
        ],

        # 6. Allow TCP 5061 (SIP/TLS)
        [
            "iptables", "-A", "INPUT",
            "-p", "tcp", "--dport", "5061",
            "-j", "ACCEPT",
        ],

        # 7. DROP TCP 5060 (plain SIP)
        [
            "iptables", "-A", "INPUT",
            "-p", "tcp", "--dport", "5060",
            "-j", "DROP",
        ],

        # 8. DROP UDP 5060 (plain SIP)
        [
            "iptables", "-A", "INPUT",
            "-p", "udp", "--dport", "5060",
            "-j", "DROP",
        ],

        # 9. Allow UDP 10000–20000 (RTP media)
        [
            "iptables", "-A", "INPUT",
            "-p", "udp", "--dport", "10000:20000",
            "-j", "ACCEPT",
        ],

        # 10. Allow TCP 443 (HTTPS/AMI)
        [
            "iptables", "-A", "INPUT",
            "-p", "tcp", "--dport", "443",
            "-j", "ACCEPT",
        ],

        # 11. Set default FORWARD policy to DROP
        ["iptables", "-P", "FORWARD", "DROP"],
    ]
    return ruleset


def apply_rules(ruleset: List[List[str]]) -> None:
    """
    Execute each rule in *ruleset* via subprocess.

    Each element of *ruleset* must be a list of strings forming a complete
    iptables command (including the ``"iptables"`` binary as the first
    element).

    Parameters
    ----------
    ruleset:
        List of iptables argv lists as returned by ``generate_ruleset()``.

    Raises
    ------
    subprocess.CalledProcessError
        If any iptables command exits with a non-zero status.
    """
    for rule in ruleset:
        subprocess.run(rule, check=True)


def persist_rules() -> None:
    """
    Persist the current iptables rules across WSL2 restarts.

    Runs ``iptables-save`` and redirects the output to
    ``/etc/iptables/rules.v4``, then installs ``iptables-persistent`` so
    that the rules are automatically restored on boot.

    Raises
    ------
    subprocess.CalledProcessError
        If any subprocess command fails.
    """
    # Save current rules to the persistence file
    subprocess.run(
        f"iptables-save > {IPTABLES_RULES_PATH}",
        shell=True,
        check=True,
    )

    # Install iptables-persistent (non-interactive)
    subprocess.run(
        [
            "apt-get", "install", "-y",
            "-o", "Dpkg::Options::=--force-confold",
            "iptables-persistent",
        ],
        check=True,
        env={"DEBIAN_FRONTEND": "noninteractive"},
    )


def parse_iptables_save(output: str) -> List[str]:
    """
    Parse the text output of ``iptables-save`` into a list of rule strings.

    Lines that are comments (starting with ``#``), table headers (starting
    with ``*``), ``COMMIT`` lines, or empty lines are excluded.  Only actual
    rule lines (starting with ``-`` or containing chain policy lines starting
    with ``:`` ) are returned.

    Parameters
    ----------
    output:
        The raw string output of ``iptables-save``.

    Returns
    -------
    list[str]
        List of rule strings, one per line, stripped of leading/trailing
        whitespace.
    """
    rules: List[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("*"):
            continue
        if stripped == "COMMIT":
            continue
        rules.append(stripped)
    return rules


def get_rule_order(ruleset: List[List[str]]) -> List[str]:
    """
    Return human-readable descriptions of each rule in *ruleset*, in order.

    This is useful for logging and auditing the intended rule sequence before
    applying it.

    Parameters
    ----------
    ruleset:
        List of iptables argv lists as returned by ``generate_ruleset()``.

    Returns
    -------
    list[str]
        Ordered list of rule description strings.
    """
    descriptions: List[str] = []
    for rule in ruleset:
        # Join the argv list into a single readable string
        descriptions.append(" ".join(rule))
    return descriptions


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    print("Generating iptables ruleset...")
    ruleset = generate_ruleset()

    print("Rule order:")
    for i, desc in enumerate(get_rule_order(ruleset), start=1):
        print(f"  {i:2d}. {desc}")

    print("\nApplying rules...")
    try:
        apply_rules(ruleset)
        print("Rules applied successfully.")
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: Failed to apply rule: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Persisting rules...")
    try:
        persist_rules()
        print("Rules persisted.")
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: Failed to persist rules: {exc}", file=sys.stderr)
        sys.exit(1)
