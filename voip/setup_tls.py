"""
setup_tls.py — TLS certificate management for Asterisk PBX (runs inside WSL2).

This script installs certbot, obtains a Let's Encrypt certificate for the SIP
domain, copies the cert and key to Asterisk's key directory, writes a certbot
renewal hook that reloads the PJSIP module, and verifies the certificate is
valid and not expired.

Requirements: 7.3, 7.4
"""

import datetime
import os
import shutil
import ssl
import stat
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configurable constants
# ---------------------------------------------------------------------------

# The SIP domain whose DNS A record must point to the Windows 11 host's
# public IP address before running certbot.
SIP_DOMAIN: str = "pbx.example.com"

# Paths used by certbot and Asterisk
CERTBOT_LIVE_DIR: str = "/etc/letsencrypt/live"
ASTERISK_KEYS_DIR: str = "/etc/asterisk/keys"
RENEWAL_HOOK_PATH: str = (
    "/etc/letsencrypt/renewal-hooks/deploy/asterisk-reload.sh"
)

# Content of the renewal hook script
RENEWAL_HOOK_CONTENT: str = """\
#!/bin/bash
# Certbot deploy hook: reload Asterisk PJSIP module after certificate renewal.
asterisk -rx "module reload res_pjsip.so"
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def install_certbot() -> None:
    """
    Install certbot via apt-get inside WSL2 (Ubuntu 22.04).

    Raises
    ------
    subprocess.CalledProcessError
        If apt-get fails.
    RuntimeError
        If certbot is not found on PATH after installation.
    """
    subprocess.run(
        ["apt-get", "update", "-y"],
        check=True,
    )
    subprocess.run(
        ["apt-get", "install", "-y", "certbot"],
        check=True,
    )
    if shutil.which("certbot") is None:
        raise RuntimeError(
            "certbot was not found on PATH after installation. "
            "Ensure apt-get completed successfully."
        )


def obtain_certificate(domain: str) -> None:
    """
    Run ``certbot certonly --standalone`` for *domain*.

    The domain's DNS A record must already resolve to this machine's public IP
    before calling this function (certbot uses HTTP-01 challenge on port 80).

    Parameters
    ----------
    domain:
        The fully-qualified domain name for the SIP server (e.g.
        ``pbx.example.com``).

    Raises
    ------
    subprocess.CalledProcessError
        If certbot exits with a non-zero status.
    """
    subprocess.run(
        [
            "certbot",
            "certonly",
            "--standalone",
            "--non-interactive",
            "--agree-tos",
            "--register-unsafely-without-email",
            "-d",
            domain,
        ],
        check=True,
    )


def copy_certs_to_asterisk(domain: str) -> None:
    """
    Copy ``fullchain.pem`` and ``privkey.pem`` from the certbot live directory
    to ``/etc/asterisk/keys/``.

    Parameters
    ----------
    domain:
        The domain name used when obtaining the certificate (must match the
        directory name under ``/etc/letsencrypt/live/``).

    Raises
    ------
    FileNotFoundError
        If the certbot live directory or expected PEM files do not exist.
    OSError
        If the destination directory cannot be created or files cannot be
        copied.
    """
    src_dir = Path(CERTBOT_LIVE_DIR) / domain
    dest_dir = Path(ASTERISK_KEYS_DIR)

    fullchain_src = src_dir / "fullchain.pem"
    privkey_src = src_dir / "privkey.pem"

    if not fullchain_src.exists():
        raise FileNotFoundError(
            f"Certificate file not found: {fullchain_src}"
        )
    if not privkey_src.exists():
        raise FileNotFoundError(
            f"Private key file not found: {privkey_src}"
        )

    dest_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(str(fullchain_src), str(dest_dir / "fullchain.pem"))
    shutil.copy2(str(privkey_src), str(dest_dir / "privkey.pem"))

    # Restrict private key permissions: owner read/write only
    privkey_dest = dest_dir / "privkey.pem"
    os.chmod(privkey_dest, 0o600)


def write_renewal_hook() -> Path:
    """
    Write the certbot deploy renewal hook script to
    ``/etc/letsencrypt/renewal-hooks/deploy/asterisk-reload.sh``.

    The hook runs ``asterisk -rx "module reload res_pjsip.so"`` after every
    successful certificate renewal so Asterisk picks up the new cert without
    a full restart.

    Returns
    -------
    Path
        The path of the written hook script.

    Raises
    ------
    OSError
        If the file cannot be written or made executable.
    """
    hook_path = Path(RENEWAL_HOOK_PATH)
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(RENEWAL_HOOK_CONTENT, encoding="utf-8")

    # Make the hook executable (rwxr-xr-x)
    os.chmod(
        hook_path,
        stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH,
    )
    return hook_path


def verify_certificate(cert_path: str | os.PathLike) -> bool:
    """
    Verify that the certificate at *cert_path* exists and is not expired.

    Uses Python's ``ssl`` module to load the certificate and check its
    ``notAfter`` field against the current UTC time.

    Parameters
    ----------
    cert_path:
        Path to a PEM-encoded certificate file (e.g. ``fullchain.pem``).

    Returns
    -------
    bool
        ``True`` if the certificate exists and has not expired.

    Raises
    ------
    FileNotFoundError
        If *cert_path* does not exist.
    ssl.SSLError
        If the file cannot be parsed as a valid certificate.
    ValueError
        If the certificate is expired.
    """
    cert_path = Path(cert_path)
    if not cert_path.exists():
        raise FileNotFoundError(f"Certificate not found: {cert_path}")

    remaining = days_until_expiry(cert_path)
    if remaining < 0:
        raise ValueError(
            f"Certificate at {cert_path} expired {abs(remaining)} day(s) ago."
        )
    return True


def days_until_expiry(cert_path: str | os.PathLike) -> int:
    """
    Return the number of days until the certificate at *cert_path* expires.

    A negative return value means the certificate has already expired.

    Parameters
    ----------
    cert_path:
        Path to a PEM-encoded certificate file.

    Returns
    -------
    int
        Days remaining until expiry (negative if already expired).

    Raises
    ------
    FileNotFoundError
        If *cert_path* does not exist.
    ssl.SSLError
        If the file cannot be parsed as a valid certificate.
    """
    cert_path = Path(cert_path)
    if not cert_path.exists():
        raise FileNotFoundError(f"Certificate not found: {cert_path}")

    # Read the PEM file and convert to DER for ssl module parsing
    pem_data = cert_path.read_bytes()

    # Use ssl.PEM_cert_to_DER_cert to get DER bytes, then decode with
    # ssl module to extract the notAfter field.
    pem_str = pem_data.decode("ascii", errors="replace")

    # Extract the first certificate from the chain (fullchain.pem may contain
    # multiple certs; we only need the leaf cert's expiry).
    begin_marker = "-----BEGIN CERTIFICATE-----"
    end_marker = "-----END CERTIFICATE-----"
    start = pem_str.find(begin_marker)
    end = pem_str.find(end_marker)
    if start == -1 or end == -1:
        raise ssl.SSLError("No valid PEM certificate found in file.")

    leaf_pem = pem_str[start : end + len(end_marker)]

    # Convert PEM → DER → parse with ssl
    der_bytes = ssl.PEM_cert_to_DER_cert(leaf_pem)

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    cert_dict = ssl.DER_cert_to_PEM_cert(der_bytes)
    # Use the low-level _ssl module to decode the cert dict
    # ssl.get_server_certificate returns a PEM string; we need to parse
    # the notAfter field from the DER bytes directly.
    not_after_str = _get_not_after_from_der(der_bytes)

    # notAfter format from ssl module: "MMM DD HH:MM:SS YYYY GMT"
    expiry_dt = datetime.datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z")
    expiry_dt = expiry_dt.replace(tzinfo=datetime.timezone.utc)
    now = datetime.datetime.now(tz=datetime.timezone.utc)

    delta = expiry_dt - now
    return delta.days


def _get_not_after_from_der(der_bytes: bytes) -> str:
    """
    Extract the ``notAfter`` string from DER-encoded certificate bytes.

    Uses ``ssl.DER_cert_to_PEM_cert`` and the internal ``_ssl`` module's
    ``_test_decode_cert`` helper (available in CPython) to parse the cert
    dict.  Falls back to the ``cryptography`` library if available.

    Parameters
    ----------
    der_bytes:
        DER-encoded certificate bytes.

    Returns
    -------
    str
        The ``notAfter`` string in the format ``"MMM DD HH:MM:SS YYYY GMT"``.

    Raises
    ------
    RuntimeError
        If neither the internal CPython helper nor the ``cryptography``
        library is available.
    """
    # Attempt 1: use the cryptography library (preferred, widely available)
    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend

        cert = x509.load_der_x509_certificate(der_bytes, default_backend())
        not_after = cert.not_valid_after_utc
        # Format to match ssl module convention
        return not_after.strftime("%b %d %H:%M:%S %Y GMT")
    except ImportError:
        pass

    # Attempt 2: use CPython's internal _ssl._test_decode_cert via a temp file
    import tempfile

    pem_str = ssl.DER_cert_to_PEM_cert(der_bytes)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".pem", delete=False, encoding="ascii"
    ) as tmp:
        tmp.write(pem_str)
        tmp_path = tmp.name

    try:
        import _ssl  # type: ignore[import]

        cert_dict = _ssl._test_decode_cert(tmp_path)  # type: ignore[attr-defined]
        not_after = cert_dict.get("notAfter")
        if not_after:
            return not_after
        raise RuntimeError(
            "notAfter field not found in certificate dict from _ssl module."
        )
    except (ImportError, AttributeError):
        raise RuntimeError(
            "Cannot parse certificate expiry: neither the 'cryptography' "
            "library nor the CPython '_ssl._test_decode_cert' helper is "
            "available. Install 'cryptography' with: pip install cryptography"
        )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """
    Run the full TLS setup sequence for the configured SIP_DOMAIN.

    Steps:
      1. Install certbot
      2. Obtain certificate for SIP_DOMAIN
      3. Copy certs to /etc/asterisk/keys/
      4. Write renewal hook
      5. Verify certificate
    """
    domain = SIP_DOMAIN
    print(f"[setup_tls] Starting TLS setup for domain: {domain}")

    print("[setup_tls] Step 1: Installing certbot...")
    install_certbot()
    print("[setup_tls] certbot installed.")

    print(f"[setup_tls] Step 2: Obtaining certificate for {domain}...")
    obtain_certificate(domain)
    print("[setup_tls] Certificate obtained.")

    print("[setup_tls] Step 3: Copying certs to Asterisk keys directory...")
    copy_certs_to_asterisk(domain)
    print(f"[setup_tls] Certs copied to {ASTERISK_KEYS_DIR}.")

    print("[setup_tls] Step 4: Writing certbot renewal hook...")
    hook_path = write_renewal_hook()
    print(f"[setup_tls] Renewal hook written to {hook_path}.")

    cert_path = Path(ASTERISK_KEYS_DIR) / "fullchain.pem"
    print(f"[setup_tls] Step 5: Verifying certificate at {cert_path}...")
    verify_certificate(cert_path)
    remaining = days_until_expiry(cert_path)
    print(f"[setup_tls] Certificate is valid. Days until expiry: {remaining}")

    print("[setup_tls] TLS setup complete.")


if __name__ == "__main__":
    main()
