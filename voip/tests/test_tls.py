"""
test_tls.py — Unit tests for TLS setup helpers in setup_tls.py.

Tests cover:
  - Certificate expiry detection logic with mock cert data (days remaining)
    - A cert expiring in 5 days returns ~5 days remaining
    - An already-expired cert returns a negative number
    - A cert expiring in 60 days returns ~60 days remaining
  - Renewal hook script content is written correctly
    - Hook file contains 'asterisk -rx "module reload res_pjsip.so"'
    - Hook file is executable (Linux only)

Requirements: 7.3, 7.4
"""

import datetime
import os
import platform
import stat
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup — allow running from workspace root
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from setup_tls import (
    RENEWAL_HOOK_CONTENT,
    days_until_expiry,
    verify_certificate,
    write_renewal_hook,
)

# ---------------------------------------------------------------------------
# Platform guard for executable-bit tests
# ---------------------------------------------------------------------------
LINUX_ONLY = pytest.mark.skipif(
    platform.system() != "Linux",
    reason="Executable permission bits are only enforced on Linux",
)


# ===========================================================================
# Helpers
# ===========================================================================


def _make_fake_cert_pem(not_after: datetime.datetime) -> str:
    """
    Return a minimal PEM certificate string whose notAfter is *not_after*.

    Rather than generating a real X.509 cert (which requires cryptography or
    openssl), we mock the internal ``_get_not_after_from_der`` helper so that
    ``days_until_expiry`` uses the date we supply.  This helper just produces
    a syntactically valid PEM wrapper so the PEM-parsing code in
    ``days_until_expiry`` can find the BEGIN/END markers.
    """
    # A minimal (but syntactically valid) base64 body — the actual DER bytes
    # are irrelevant because we mock _get_not_after_from_der.
    fake_b64 = (
        "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2a2rwplBQLF29amygykE"
        "MmYz0+Kcj3bKBp29Ld7AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    )
    return (
        "-----BEGIN CERTIFICATE-----\n"
        f"{fake_b64}\n"
        "-----END CERTIFICATE-----\n"
    )


def _not_after_str(dt: datetime.datetime) -> str:
    """Format a datetime as the ssl-module notAfter string."""
    return dt.strftime("%b %d %H:%M:%S %Y GMT")


# ===========================================================================
# Tests: days_until_expiry
# ===========================================================================


class TestDaysUntilExpiry:
    """Tests for the days_until_expiry() helper."""

    def _run_with_expiry(
        self, tmp_path: Path, days_from_now: int
    ) -> int:
        """
        Write a fake PEM cert to a temp file, mock the DER-parsing internals,
        and call days_until_expiry().  Returns the integer result.
        """
        now_utc = datetime.datetime.now(tz=datetime.timezone.utc)
        expiry_dt = now_utc + datetime.timedelta(days=days_from_now)

        cert_file = tmp_path / "fullchain.pem"
        cert_file.write_text(_make_fake_cert_pem(expiry_dt), encoding="ascii")

        # Mock ssl.PEM_cert_to_DER_cert to return dummy bytes (the actual DER
        # content is irrelevant because we also mock _get_not_after_from_der).
        dummy_der = b"\x30\x82\x01\x00"  # minimal DER-like bytes

        with patch("setup_tls.ssl.PEM_cert_to_DER_cert", return_value=dummy_der), \
             patch(
                 "setup_tls._get_not_after_from_der",
                 return_value=_not_after_str(expiry_dt),
             ):
            return days_until_expiry(cert_file)

    def test_cert_expiring_in_5_days(self, tmp_path: Path) -> None:
        """A cert expiring in 5 days should return approximately 5."""
        result = self._run_with_expiry(tmp_path, days_from_now=5)
        # Allow ±1 day tolerance for time elapsed during the test
        assert 4 <= result <= 5, (
            f"Expected ~5 days remaining, got {result}"
        )

    def test_cert_expiring_in_60_days(self, tmp_path: Path) -> None:
        """A cert expiring in 60 days should return approximately 60."""
        result = self._run_with_expiry(tmp_path, days_from_now=60)
        assert 59 <= result <= 60, (
            f"Expected ~60 days remaining, got {result}"
        )

    def test_expired_cert_returns_negative(self, tmp_path: Path) -> None:
        """An already-expired cert should return a negative number."""
        result = self._run_with_expiry(tmp_path, days_from_now=-10)
        assert result < 0, (
            f"Expected a negative value for an expired cert, got {result}"
        )

    def test_expired_cert_value_is_approximately_minus_10(
        self, tmp_path: Path
    ) -> None:
        """A cert that expired 10 days ago should return approximately -10."""
        result = self._run_with_expiry(tmp_path, days_from_now=-10)
        assert -11 <= result <= -10, (
            f"Expected approximately -10, got {result}"
        )

    def test_raises_file_not_found_for_missing_cert(self) -> None:
        """days_until_expiry should raise FileNotFoundError for a missing file."""
        with pytest.raises(FileNotFoundError):
            days_until_expiry("/nonexistent/path/fullchain.pem")

    def test_raises_ssl_error_for_invalid_pem(self, tmp_path: Path) -> None:
        """days_until_expiry should raise ssl.SSLError for a non-PEM file."""
        import ssl

        bad_cert = tmp_path / "bad.pem"
        bad_cert.write_text("this is not a certificate", encoding="ascii")
        with pytest.raises(ssl.SSLError):
            days_until_expiry(bad_cert)


# ===========================================================================
# Tests: verify_certificate
# ===========================================================================


class TestVerifyCertificate:
    """Tests for the verify_certificate() helper."""

    def test_valid_cert_returns_true(self, tmp_path: Path) -> None:
        """verify_certificate should return True for a valid, non-expired cert."""
        now_utc = datetime.datetime.now(tz=datetime.timezone.utc)
        expiry_dt = now_utc + datetime.timedelta(days=30)
        cert_file = tmp_path / "fullchain.pem"
        cert_file.write_text(_make_fake_cert_pem(expiry_dt), encoding="ascii")

        dummy_der = b"\x30\x82\x01\x00"
        with patch("setup_tls.ssl.PEM_cert_to_DER_cert", return_value=dummy_der), \
             patch(
                 "setup_tls._get_not_after_from_der",
                 return_value=_not_after_str(expiry_dt),
             ):
            result = verify_certificate(cert_file)

        assert result is True

    def test_expired_cert_raises_value_error(self, tmp_path: Path) -> None:
        """verify_certificate should raise ValueError for an expired cert."""
        now_utc = datetime.datetime.now(tz=datetime.timezone.utc)
        expiry_dt = now_utc - datetime.timedelta(days=5)
        cert_file = tmp_path / "fullchain.pem"
        cert_file.write_text(_make_fake_cert_pem(expiry_dt), encoding="ascii")

        dummy_der = b"\x30\x82\x01\x00"
        with patch("setup_tls.ssl.PEM_cert_to_DER_cert", return_value=dummy_der), \
             patch(
                 "setup_tls._get_not_after_from_der",
                 return_value=_not_after_str(expiry_dt),
             ):
            with pytest.raises(ValueError, match="expired"):
                verify_certificate(cert_file)

    def test_missing_cert_raises_file_not_found(self) -> None:
        """verify_certificate should raise FileNotFoundError for a missing file."""
        with pytest.raises(FileNotFoundError):
            verify_certificate("/nonexistent/path/fullchain.pem")


# ===========================================================================
# Tests: write_renewal_hook
# ===========================================================================


class TestWriteRenewalHook:
    """Tests for the write_renewal_hook() helper."""

    def test_hook_file_is_created(self, tmp_path: Path) -> None:
        """write_renewal_hook should create the hook file."""
        hook_path = tmp_path / "deploy" / "asterisk-reload.sh"

        with patch("setup_tls.RENEWAL_HOOK_PATH", str(hook_path)):
            result = write_renewal_hook()

        assert hook_path.exists(), "Renewal hook file was not created"
        assert result == hook_path

    def test_hook_contains_asterisk_reload_command(
        self, tmp_path: Path
    ) -> None:
        """Hook file must contain the asterisk module reload command."""
        hook_path = tmp_path / "deploy" / "asterisk-reload.sh"

        with patch("setup_tls.RENEWAL_HOOK_PATH", str(hook_path)):
            write_renewal_hook()

        content = hook_path.read_text(encoding="utf-8")
        assert 'asterisk -rx "module reload res_pjsip.so"' in content, (
            "Renewal hook does not contain the expected asterisk reload command"
        )

    def test_hook_contains_bash_shebang(self, tmp_path: Path) -> None:
        """Hook file should start with a bash shebang line."""
        hook_path = tmp_path / "deploy" / "asterisk-reload.sh"

        with patch("setup_tls.RENEWAL_HOOK_PATH", str(hook_path)):
            write_renewal_hook()

        content = hook_path.read_text(encoding="utf-8")
        assert content.startswith("#!/bin/bash"), (
            "Renewal hook does not start with #!/bin/bash"
        )

    def test_hook_content_matches_constant(self, tmp_path: Path) -> None:
        """Hook file content should match the RENEWAL_HOOK_CONTENT constant."""
        hook_path = tmp_path / "deploy" / "asterisk-reload.sh"

        with patch("setup_tls.RENEWAL_HOOK_PATH", str(hook_path)):
            write_renewal_hook()

        content = hook_path.read_text(encoding="utf-8")
        assert content == RENEWAL_HOOK_CONTENT

    def test_hook_creates_parent_directories(self, tmp_path: Path) -> None:
        """write_renewal_hook should create missing parent directories."""
        hook_path = tmp_path / "a" / "b" / "c" / "asterisk-reload.sh"

        with patch("setup_tls.RENEWAL_HOOK_PATH", str(hook_path)):
            write_renewal_hook()

        assert hook_path.exists()

    @LINUX_ONLY
    def test_hook_is_executable(self, tmp_path: Path) -> None:
        """Hook file must be executable on Linux."""
        hook_path = tmp_path / "deploy" / "asterisk-reload.sh"

        with patch("setup_tls.RENEWAL_HOOK_PATH", str(hook_path)):
            write_renewal_hook()

        file_stat = os.stat(hook_path)
        mode = stat.S_IMODE(file_stat.st_mode)

        # Check owner execute bit (S_IXUSR)
        assert mode & stat.S_IXUSR, (
            f"Hook file is not executable by owner. Mode: {oct(mode)}"
        )
        # Check group execute bit (S_IXGRP)
        assert mode & stat.S_IXGRP, (
            f"Hook file is not executable by group. Mode: {oct(mode)}"
        )
        # Check other execute bit (S_IXOTH)
        assert mode & stat.S_IXOTH, (
            f"Hook file is not executable by others. Mode: {oct(mode)}"
        )

    @LINUX_ONLY
    def test_hook_permission_is_0o755(self, tmp_path: Path) -> None:
        """Hook file should have 0o755 permissions on Linux."""
        hook_path = tmp_path / "deploy" / "asterisk-reload.sh"

        with patch("setup_tls.RENEWAL_HOOK_PATH", str(hook_path)):
            write_renewal_hook()

        file_stat = os.stat(hook_path)
        mode = stat.S_IMODE(file_stat.st_mode)
        assert mode == 0o755, (
            f"Expected hook permissions 0o755, got {oct(mode)}"
        )
