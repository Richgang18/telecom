"""
provision.py — Asterisk PBX provisioning script for WSL2 (Ubuntu 22.04).

Runs inside WSL2. Verifies the OS, installs Asterisk with chan_pjsip,
configures the systemd service with Restart=always, and verifies the
service is active after installation.

Requirements: 1.1, 1.2, 1.5, 1.6
"""

import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# OS detection
# ---------------------------------------------------------------------------

def read_os_release(path: str = "/etc/os-release") -> dict[str, str]:
    """Parse /etc/os-release into a key→value dict."""
    result: dict[str, str] = {}
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if "=" not in line or line.startswith("#"):
                    continue
                key, _, value = line.partition("=")
                # Strip surrounding quotes
                result[key.strip()] = value.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return result


def verify_ubuntu_2204(os_release: dict[str, str] | None = None) -> bool:
    """
    Return True if the current OS is Ubuntu 22.04.

    Raises RuntimeError if the OS is not Ubuntu 22.04.
    """
    if os_release is None:
        os_release = read_os_release()

    distro_id = os_release.get("ID", "").lower()
    version_id = os_release.get("VERSION_ID", "")

    if distro_id == "ubuntu" and version_id == "22.04":
        return True

    raise RuntimeError(
        f"Unsupported OS: ID={distro_id!r}, VERSION_ID={version_id!r}. "
        "This script requires Ubuntu 22.04."
    )


# ---------------------------------------------------------------------------
# Package installation
# ---------------------------------------------------------------------------

def run_command(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command, streaming output to stdout/stderr."""
    print(f"[provision] Running: {' '.join(args)}")
    return subprocess.run(args, check=check)


def install_asterisk() -> None:
    """Install Asterisk and chan_pjsip via apt-get."""
    run_command(["apt-get", "update", "-y"])
    run_command([
        "apt-get", "install", "-y",
        "asterisk",
        "asterisk-modules",   # includes chan_pjsip
    ])


# ---------------------------------------------------------------------------
# systemd service configuration
# ---------------------------------------------------------------------------

SYSTEMD_OVERRIDE_DIR = Path("/etc/systemd/system/asterisk.service.d")
SYSTEMD_OVERRIDE_FILE = SYSTEMD_OVERRIDE_DIR / "restart.conf"
OVERRIDE_CONTENT = "[Service]\nRestart=always\nRestartSec=5\n"


def configure_asterisk_service() -> None:
    """
    Drop a systemd override that sets Restart=always for the asterisk service.
    Then enable and start the service.
    """
    SYSTEMD_OVERRIDE_DIR.mkdir(parents=True, exist_ok=True)
    SYSTEMD_OVERRIDE_FILE.write_text(OVERRIDE_CONTENT)
    print(f"[provision] Wrote systemd override to {SYSTEMD_OVERRIDE_FILE}")

    run_command(["systemctl", "daemon-reload"])
    run_command(["systemctl", "enable", "asterisk"])
    run_command(["systemctl", "start", "asterisk"])


# ---------------------------------------------------------------------------
# Service verification
# ---------------------------------------------------------------------------

def verify_service_active(service: str = "asterisk") -> bool:
    """
    Return True if the given systemd service is active (running).

    Raises RuntimeError if the service is not active.
    """
    result = subprocess.run(
        ["systemctl", "is-active", service],
        capture_output=True,
        text=True,
        check=False,
    )
    status = result.stdout.strip()
    if status == "active":
        print(f"[provision] Service '{service}' is active.")
        return True
    raise RuntimeError(
        f"Service '{service}' is not active after installation (status={status!r})."
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("[provision] Verifying OS …")
    verify_ubuntu_2204()
    print("[provision] OS check passed: Ubuntu 22.04")

    print("[provision] Installing Asterisk with chan_pjsip …")
    install_asterisk()

    print("[provision] Configuring asterisk systemd service (Restart=always) …")
    configure_asterisk_service()

    print("[provision] Verifying asterisk service is active …")
    verify_service_active("asterisk")

    print("[provision] Provisioning complete.")


if __name__ == "__main__":
    main()
