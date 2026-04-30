"""
setup_ami.py — Configure the Asterisk Manager Interface (AMI) (inside WSL2).

Writes /etc/asterisk/manager.conf with AMI enabled on localhost only,
reloads the manager module, and verifies AMI is bound to 127.0.0.1.

Requirements: 1.3, 14.1
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration file content
# ---------------------------------------------------------------------------

MANAGER_CONF_CONTENT: str = """\
[general]
enabled=yes
bindaddr=127.0.0.1
port=5038

[admin]
secret=CHANGE_ME_ADMIN_SECRET
read=all
write=all
deny=0.0.0.0/0.0.0.0
permit=127.0.0.1/255.255.255.255
"""

# Placeholder secret value — administrator must change this before deployment
_PLACEHOLDER_SECRET: str = "CHANGE_ME_ADMIN_SECRET"

# ---------------------------------------------------------------------------
# Default file paths
# ---------------------------------------------------------------------------

DEFAULT_MANAGER_CONF_PATH: str = "/etc/asterisk/manager.conf"

# AMI port
AMI_PORT: int = 5038


# ---------------------------------------------------------------------------
# Public API — config file writer
# ---------------------------------------------------------------------------


def write_manager_conf(path: str = DEFAULT_MANAGER_CONF_PATH) -> Path:
    """
    Write the Asterisk AMI configuration to *path*.

    Creates parent directories as needed.  The file is written with the
    content defined in :data:`MANAGER_CONF_CONTENT`.

    Parameters
    ----------
    path:
        Destination file path.  Defaults to ``/etc/asterisk/manager.conf``.

    Returns
    -------
    Path
        The resolved Path object of the written file.

    Raises
    ------
    OSError
        If the file cannot be written.

    Requirements: 1.3, 14.1
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(MANAGER_CONF_CONTENT, encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# Public API — module reload
# ---------------------------------------------------------------------------


def reload_manager_module() -> subprocess.CompletedProcess:
    """
    Reload the Asterisk manager module via the Asterisk CLI.

    Runs ``asterisk -rx "module reload manager"`` and returns the completed
    process result.

    Returns
    -------
    subprocess.CompletedProcess
        The result of the ``asterisk -rx`` invocation.

    Requirements: 14.1
    """
    result = subprocess.run(
        ["asterisk", "-rx", "module reload manager"],
        capture_output=True,
        text=True,
    )
    return result


# ---------------------------------------------------------------------------
# Public API — AMI localhost verification
# ---------------------------------------------------------------------------


def verify_ami_localhost_only(ss_output: str) -> bool:
    """
    Parse the output of ``ss -tlnp`` and return ``True`` if port 5038 is
    bound to ``127.0.0.1`` only.

    Returns ``False`` if port 5038 is not found, or if it is bound to
    ``0.0.0.0`` or ``::`` (i.e., all interfaces).

    This function is pure and testable without running ``ss``.

    Parameters
    ----------
    ss_output:
        The text output of ``ss -tlnp`` captured from the system.

    Returns
    -------
    bool
        ``True`` if AMI is listening on ``127.0.0.1:5038`` only;
        ``False`` otherwise.

    Requirements: 1.3, 14.1
    """
    port_str = str(AMI_PORT)

    for line in ss_output.splitlines():
        # ss -tlnp columns: State Recv-Q Send-Q Local-Address:Port Peer-Address:Port
        # We look for lines that contain our port number
        parts = line.split()
        # ss -tlnp columns: Netid State Recv-Q Send-Q Local-Address:Port Peer-Address:Port
        # The local address:port is at index 4 (0-based)
        # Guard: need at least 5 columns
        if len(parts) < 5:
            continue
        local_addr_port = parts[4]

        # Handle IPv6 format: [::1]:5038 or [::]:5038
        if local_addr_port.startswith("["):
            # IPv6 — extract port after "]:"
            bracket_end = local_addr_port.find("]")
            if bracket_end == -1:
                continue
            port_part = local_addr_port[bracket_end + 2:]
            addr_part = local_addr_port[1:bracket_end]
        elif ":" in local_addr_port:
            # IPv4 format: 127.0.0.1:5038 or 0.0.0.0:5038
            last_colon = local_addr_port.rfind(":")
            addr_part = local_addr_port[:last_colon]
            port_part = local_addr_port[last_colon + 1:]
        else:
            continue

        if port_part != port_str:
            continue

        # Found a line with port 5038 — check the address
        if addr_part == "127.0.0.1":
            return True
        # Bound to 0.0.0.0 or :: or any other address — not localhost-only
        return False

    # Port 5038 not found in ss output
    return False


# ---------------------------------------------------------------------------
# Orchestration entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """
    Orchestrate all AMI setup steps:

    1. Write ``/etc/asterisk/manager.conf``.
    2. Warn if the admin secret has not been changed from the placeholder.
    3. Reload the manager module via the Asterisk CLI.
    4. Verify AMI is listening on localhost only via ``ss -tlnp``.
    """
    print("Step 1: Writing manager.conf...")
    manager_conf_path = write_manager_conf()
    print(f"  Written to {manager_conf_path}")

    # Warn if the placeholder secret has not been changed
    if _PLACEHOLDER_SECRET in MANAGER_CONF_CONTENT:
        print(
            "\n  WARNING: The AMI admin secret is still set to the placeholder "
            f"value '{_PLACEHOLDER_SECRET}'.\n"
            "  You MUST change the secret in /etc/asterisk/manager.conf "
            "before deploying to production!\n"
        )

    print("Step 2: Reloading manager module...")
    result = reload_manager_module()
    if result.returncode == 0:
        print("  Manager module reloaded successfully.")
    else:
        print(f"  WARNING: module reload returned code {result.returncode}")
        if result.stdout:
            print(f"  stdout: {result.stdout.strip()}")
        if result.stderr:
            print(f"  stderr: {result.stderr.strip()}")

    print("Step 3: Verifying AMI is listening on localhost only...")
    try:
        ss_result = subprocess.run(
            ["ss", "-tlnp"],
            capture_output=True,
            text=True,
            check=True,
        )
        ss_output = ss_result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"  ERROR: Could not run 'ss -tlnp': {exc}")
        sys.exit(1)

    if verify_ami_localhost_only(ss_output):
        print(f"  AMI is correctly bound to 127.0.0.1:{AMI_PORT} (localhost only).")
    else:
        print(
            f"  ERROR: AMI is NOT bound to 127.0.0.1:{AMI_PORT}. "
            "Check manager.conf and reload Asterisk."
        )
        sys.exit(1)

    print("\nAMI setup complete.")


if __name__ == "__main__":
    main()
