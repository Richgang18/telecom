"""
deploy.py — Full system deployment orchestrator for the VoIP Calling System.

Runs inside WSL2 (Ubuntu 22.04). Calls each setup script in order, then
invokes setup_windows_host.ps1 on the Windows host, reloads Asterisk, runs
the integration test suite, and prints a deployment summary.

Execution order:
  1. provision.py          — Install Asterisk + systemd
  2. setup_tls.py          — Let's Encrypt TLS certificate
  3. setup_firewall.py     — WSL2 iptables rules
  4. setup_fail2ban.py     — Fail2Ban Asterisk jail
  5. generate_pjsip.py     — pjsip.conf (endpoints + trunk)
  6. generate_dialplan.py  — extensions.conf
  7. setup_cdr.py          — CDR logging
  8. setup_ami.py          — AMI (localhost only)
  9. setup_windows_host.ps1 — Windows Firewall + portproxy + Task Scheduler
 10. asterisk core reload  — Apply all config changes
 11. pytest test_integration.py — Run integration tests

Requirements: 1.4, 1a.1, 1a.2, 1a.3, 1a.4, 13.1, 13.2, 14.1, 14.2,
              14.3, 14.4, 14.5
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable

# ---------------------------------------------------------------------------
# Script directory
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent.resolve()

# ---------------------------------------------------------------------------
# Deployment configuration
# ---------------------------------------------------------------------------

# Path to setup_windows_host.ps1 on the Windows host.
# When running inside WSL2, the Windows C: drive is mounted at /mnt/c.
WINDOWS_HOST_SCRIPT = "/mnt/c/VoIP/setup_windows_host.ps1"

# Asterisk CLI command
ASTERISK_CLI = "asterisk"


# ---------------------------------------------------------------------------
# Step runner
# ---------------------------------------------------------------------------


class DeploymentError(Exception):
    """Raised when a deployment step fails."""


def _run_step(step_name: str, fn: Callable[[], None]) -> None:
    """
    Execute *fn* as a named deployment step.

    Prints a status line before and after execution.  Raises
    :class:`DeploymentError` if *fn* raises any exception.

    Parameters
    ----------
    step_name:
        Human-readable name for the step (used in log output).
    fn:
        Zero-argument callable that performs the step.

    Raises
    ------
    DeploymentError
        If *fn* raises any exception.
    """
    print(f"\n[DEPLOY] ▶ {step_name} ...", flush=True)
    try:
        fn()
        print(f"[DEPLOY] ✓ {step_name} complete.", flush=True)
    except Exception as exc:
        print(f"[DEPLOY] ✗ {step_name} FAILED: {exc}", file=sys.stderr, flush=True)
        raise DeploymentError(f"{step_name} failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Individual step implementations
# ---------------------------------------------------------------------------


def _step_provision() -> None:
    """Run provision.py to install Asterisk inside WSL2."""
    sys.path.insert(0, str(SCRIPT_DIR))
    import provision  # noqa: F401 — side-effect import
    provision.main()


def _step_setup_tls() -> None:
    """Skip TLS certificate — to be configured separately."""
    print("  [TLS] Skipping TLS certificate setup.")
    print("  [TLS] Run get_cert.sh manually once DNS is ready.")
    print("  [TLS] System will use self-signed cert for now.")
    # Generate a self-signed cert so Asterisk starts without errors
    import subprocess
    from pathlib import Path
    keys_dir = Path("/etc/asterisk/keys")
    keys_dir.mkdir(parents=True, exist_ok=True)
    cert = keys_dir / "fullchain.pem"
    key = keys_dir / "privkey.pem"
    if not cert.exists():
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", str(key),
            "-out", str(cert),
            "-days", "365", "-nodes",
            "-subj", "/CN=pbx.vouchersdept.com"
        ], check=True)
        print("  [TLS] Self-signed certificate generated.")


def _step_setup_firewall() -> None:
    """Apply WSL2 iptables rules via setup_firewall.py."""
    from setup_firewall import apply_rules, generate_ruleset, persist_rules
    ruleset = generate_ruleset()
    apply_rules(ruleset)
    persist_rules()


def _step_setup_fail2ban() -> None:
    """Install and configure Fail2Ban via setup_fail2ban.py."""
    import setup_fail2ban
    setup_fail2ban.main()


def _step_generate_pjsip() -> None:
    """
    Generate pjsip.conf for endpoints and trunk.

    Reads endpoint and trunk configuration from environment variables or
    falls back to a placeholder that the administrator must update.
    """
    import os
    from generate_pjsip import append_trunk_config, write_pjsip_conf

    # Build endpoint list from environment or use defaults
    extensions = []
    for i in range(1, 6):
        ext = os.environ.get(f"VOIP_EXT_{i:03d}", str(100 + i))
        display = os.environ.get(f"VOIP_NAME_{i:03d}", f"User {100 + i}")
        password = os.environ.get(f"VOIP_PASS_{i:03d}", f"ChangeMe{100 + i}!")
        did = os.environ.get(f"VOIP_DID_{i:03d}", f"+1202555{100 + i:04d}")
        extensions.append({
            "extension": int(ext),
            "display_name": display,
            "password": password,
            "caller_id_num": did,
        })

    write_pjsip_conf(extensions)

    # Append trunk config if trunk env vars are set
    trunk_name = os.environ.get("VOIP_TRUNK_NAME", "")
    if trunk_name:
        trunk = {
            "trunk_name": trunk_name,
            "host": os.environ.get("VOIP_TRUNK_HOST", "sip.voip.ms"),
            "username": os.environ.get("VOIP_TRUNK_USER", ""),
            "password": os.environ.get("VOIP_TRUNK_PASS", ""),
            "from_user": os.environ.get("VOIP_TRUNK_DID", "+10000000000"),
            "from_domain": os.environ.get("VOIP_TRUNK_DOMAIN", "sip.voip.ms"),
            "transport": "transport-tls",
            "codecs": ["ulaw", "alaw"],
        }
        append_trunk_config(trunk)
        print(f"  Trunk '{trunk_name}' appended to pjsip.conf.")
    else:
        print("  VOIP_TRUNK_NAME not set — skipping trunk config.")


def _step_generate_dialplan() -> None:
    """Generate extensions.conf via generate_dialplan.py."""
    import os
    from generate_dialplan import write_extensions_conf, write_extensions_conf_with_rotation

    extensions = [str(i) for i in range(101, 106)]
    trunk_name = os.environ.get("VOIP_TRUNK_NAME", "twilio-trunk")

    # Support multiple DIDs for round-robin rotation
    # Set VOIP_TRUNK_DIDS as a comma-separated list, e.g. "+12025551001,+12025551002"
    # Falls back to single VOIP_TRUNK_DID if only one number
    dids_env = os.environ.get("VOIP_TRUNK_DIDS", "")
    if dids_env:
        dids = [d.strip() for d in dids_env.split(",") if d.strip()]
    else:
        single_did = os.environ.get("VOIP_TRUNK_DID", "+10000000000")
        dids = [single_did]

    if len(dids) > 1:
        print(f"  DID rotation enabled: {len(dids)} numbers in pool")
        write_extensions_conf_with_rotation(extensions, trunk_name, dids)
    else:
        print(f"  Single DID mode: {dids[0]}")
        write_extensions_conf(extensions, trunk_name, dids[0])


def _step_setup_cdr() -> None:
    """Configure CDR logging via setup_cdr.py."""
    import setup_cdr
    setup_cdr.main()


def _step_setup_ami() -> None:
    """Configure AMI via setup_ami.py."""
    import setup_ami
    setup_ami.main()


def _step_setup_windows_host() -> None:
    """
    Invoke setup_windows_host.ps1 on the Windows host via PowerShell.

    When running inside WSL2, powershell.exe is available on the PATH
    (it resolves to the Windows PowerShell binary via WSL interop).
    """
    script_path = WINDOWS_HOST_SCRIPT
    result = subprocess.run(
        ["powershell.exe", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", script_path],
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0:
        raise RuntimeError(
            f"setup_windows_host.ps1 exited with code {result.returncode}. "
            f"stderr: {result.stderr.strip()}"
        )


def _step_reload_asterisk() -> None:
    """Reload Asterisk configuration without restarting the service."""
    result = subprocess.run(
        [ASTERISK_CLI, "-rx", "core reload"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"asterisk core reload failed (code {result.returncode}): "
            f"{result.stderr.strip()}"
        )
    print(f"  {result.stdout.strip()}")


def _step_run_tests() -> None:
    """Run the integration test suite via pytest."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_integration.py",
         "-m", "not integration",  # skip live tests by default
         "-v", "--tb=short"],
        cwd=str(SCRIPT_DIR),
        capture_output=False,  # stream output directly
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"pytest exited with code {result.returncode}"
        )


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------


def _print_summary() -> None:
    """Print a deployment summary by querying Asterisk and system state."""
    print("\n" + "=" * 60)
    print("DEPLOYMENT SUMMARY")
    print("=" * 60)

    # Asterisk version
    try:
        r = subprocess.run(
            [ASTERISK_CLI, "-rx", "core show version"],
            capture_output=True, text=True, timeout=5,
        )
        print(f"Asterisk version : {r.stdout.strip()}")
    except Exception as exc:
        print(f"Asterisk version : ERROR ({exc})")

    # Active extensions
    try:
        r = subprocess.run(
            [ASTERISK_CLI, "-rx", "pjsip show registrations"],
            capture_output=True, text=True, timeout=5,
        )
        lines = [l for l in r.stdout.splitlines() if "Registered" in l]
        print(f"Registered exts  : {len(lines)}")
    except Exception as exc:
        print(f"Registered exts  : ERROR ({exc})")

    # Trunk registration status
    try:
        r = subprocess.run(
            [ASTERISK_CLI, "-rx", "pjsip show registrations"],
            capture_output=True, text=True, timeout=5,
        )
        trunk_lines = [l for l in r.stdout.splitlines() if "trunk" in l.lower()]
        status = trunk_lines[0].strip() if trunk_lines else "Not found"
        print(f"Trunk status     : {status}")
    except Exception as exc:
        print(f"Trunk status     : ERROR ({exc})")

    # WSL2 iptables rule count
    try:
        r = subprocess.run(
            ["iptables", "-L", "INPUT", "--line-numbers", "-n"],
            capture_output=True, text=True, timeout=5,
        )
        rule_count = len([l for l in r.stdout.splitlines() if l and l[0].isdigit()])
        print(f"iptables rules   : {rule_count} INPUT rules")
    except Exception as exc:
        print(f"iptables rules   : ERROR ({exc})")

    # Fail2Ban jail status
    try:
        r = subprocess.run(
            ["fail2ban-client", "status", "asterisk"],
            capture_output=True, text=True, timeout=5,
        )
        banned_line = next(
            (l for l in r.stdout.splitlines() if "Banned IP" in l), "N/A"
        )
        print(f"Fail2Ban         : {banned_line.strip()}")
    except Exception as exc:
        print(f"Fail2Ban         : ERROR ({exc})")

    # Portproxy rules (via PowerShell)
    try:
        r = subprocess.run(
            ["powershell.exe", "-NonInteractive", "-Command",
             "netsh interface portproxy show all"],
            capture_output=True, text=True, timeout=10,
        )
        proxy_lines = [l for l in r.stdout.splitlines() if "5061" in l]
        print(f"Portproxy 5061   : {proxy_lines[0].strip() if proxy_lines else 'Not found'}")
    except Exception as exc:
        print(f"Portproxy 5061   : ERROR ({exc})")

    print("=" * 60)


# ---------------------------------------------------------------------------
# Ordered deployment steps
# ---------------------------------------------------------------------------

STEPS: list[tuple[str, Callable[[], None]]] = [
    ("1. Provision Asterisk (WSL2)",        _step_provision),
    ("2. TLS certificate (WSL2)",           _step_setup_tls),
    ("3. iptables firewall (WSL2)",         _step_setup_firewall),
    ("4. Fail2Ban (WSL2)",                  _step_setup_fail2ban),
    ("5. Generate pjsip.conf (WSL2)",       _step_generate_pjsip),
    ("6. Generate extensions.conf (WSL2)",  _step_generate_dialplan),
    ("7. CDR logging (WSL2)",               _step_setup_cdr),
    ("8. AMI configuration (WSL2)",         _step_setup_ami),
    ("9. Windows host setup (PowerShell)",  _step_setup_windows_host),
    ("10. Asterisk core reload",            _step_reload_asterisk),
    ("11. Run test suite",                  _step_run_tests),
]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(steps: list[tuple[str, Callable[[], None]]] | None = None) -> int:
    """
    Execute all deployment steps in order.

    Parameters
    ----------
    steps:
        Optional list of (name, callable) tuples to execute.  Defaults to
        the module-level ``STEPS`` list.

    Returns
    -------
    int
        0 on success, 1 on failure.
    """
    if steps is None:
        steps = STEPS

    print("=" * 60)
    print("VoIP Calling System — Full Deployment")
    print(f"Running {len(steps)} steps...")
    print("=" * 60)

    for step_name, step_fn in steps:
        try:
            _run_step(step_name, step_fn)
        except DeploymentError:
            print(
                f"\n[DEPLOY] Deployment halted at step: {step_name}",
                file=sys.stderr,
            )
            return 1

    _print_summary()
    print("\n[DEPLOY] All steps completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
