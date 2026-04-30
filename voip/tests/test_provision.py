"""
test_provision.py — Unit tests for provisioning helpers.

Tests cover:
  - write_file creates files with correct content and permissions
  - OS version detection (supported / unsupported OS strings)
  - wsl.conf contains [boot] and systemd=true

Requirements: 1.1, 1.6

Note on permissions:
  Unix permission bits (chmod) are only enforced on Linux/macOS.
  On Windows (NTFS), os.chmod() is a no-op for most bits, so permission
  tests are skipped on non-Linux platforms.  The scripts themselves run
  inside WSL2 (Linux), where the permissions are meaningful.
"""

import os
import platform
import stat
import textwrap
from pathlib import Path

import pytest

# Skip permission-related assertions on Windows where chmod is a no-op.
LINUX_ONLY = pytest.mark.skipif(
    platform.system() != "Linux",
    reason="Unix permission bits are only enforced on Linux",
)

# ---------------------------------------------------------------------------
# Helpers under test
# ---------------------------------------------------------------------------
# Add the voip/ directory to sys.path so imports work when running from the
# workspace root with:  python -m pytest voip/tests/test_provision.py -v
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from config_writer import (
    DEFAULT_MODE,
    SECURE_MODE,
    file_has_permission,
    write_file,
    write_secure_file,
)
from provision import read_os_release, verify_ubuntu_2204


# ===========================================================================
# Tests for config_writer.write_file
# ===========================================================================


class TestWriteFile:
    """Tests for the write_file() utility."""

    def test_creates_file_with_correct_content(self, tmp_path: Path) -> None:
        """write_file should create the file and store the exact content."""
        target = tmp_path / "test.conf"
        content = "[section]\nkey=value\n"

        write_file(target, content)

        assert target.exists(), "File was not created"
        assert target.read_text(encoding="utf-8") == content

    @LINUX_ONLY
    def test_default_permission_is_0o644(self, tmp_path: Path) -> None:
        """write_file with default mode should produce 0o644 permissions."""
        target = tmp_path / "default.conf"
        write_file(target, "data")

        assert file_has_permission(target, DEFAULT_MODE), (
            f"Expected mode {oct(DEFAULT_MODE)}, "
            f"got {oct(stat.S_IMODE(os.stat(target).st_mode))}"
        )

    @LINUX_ONLY
    def test_custom_permission_is_applied(self, tmp_path: Path) -> None:
        """write_file should honour an explicit mode argument."""
        target = tmp_path / "custom.conf"
        write_file(target, "data", mode=0o600)

        assert file_has_permission(target, 0o600)

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """write_file should create missing parent directories by default."""
        target = tmp_path / "a" / "b" / "c" / "file.conf"
        write_file(target, "hello")

        assert target.exists()

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        """write_file should overwrite an existing file."""
        target = tmp_path / "overwrite.conf"
        target.write_text("old content")

        write_file(target, "new content")

        assert target.read_text() == "new content"

    @LINUX_ONLY
    def test_write_secure_file_uses_0o640(self, tmp_path: Path) -> None:
        """write_secure_file should produce 0o640 permissions."""
        target = tmp_path / "secure.conf"
        write_secure_file(target, "secret=abc")

        assert file_has_permission(target, SECURE_MODE), (
            f"Expected mode {oct(SECURE_MODE)}, "
            f"got {oct(stat.S_IMODE(os.stat(target).st_mode))}"
        )

    def test_empty_content_creates_empty_file(self, tmp_path: Path) -> None:
        """write_file with empty string should create a zero-byte file."""
        target = tmp_path / "empty.conf"
        write_file(target, "")

        assert target.exists()
        assert target.stat().st_size == 0


# ===========================================================================
# Tests for provision.read_os_release / verify_ubuntu_2204
# ===========================================================================


class TestOsVersionDetection:
    """Tests for OS version detection helpers."""

    def _make_os_release(self, tmp_path: Path, content: str) -> Path:
        """Write a fake /etc/os-release file and return its path."""
        p = tmp_path / "os-release"
        p.write_text(textwrap.dedent(content))
        return p

    # --- read_os_release ---

    def test_parses_ubuntu_2204(self, tmp_path: Path) -> None:
        """read_os_release should correctly parse Ubuntu 22.04 fields."""
        p = self._make_os_release(
            tmp_path,
            """\
            NAME="Ubuntu"
            VERSION="22.04.3 LTS (Jammy Jellyfish)"
            ID=ubuntu
            VERSION_ID="22.04"
            PRETTY_NAME="Ubuntu 22.04.3 LTS"
            """,
        )
        result = read_os_release(str(p))

        assert result["ID"] == "ubuntu"
        assert result["VERSION_ID"] == "22.04"
        assert result["NAME"] == "Ubuntu"

    def test_parses_debian(self, tmp_path: Path) -> None:
        """read_os_release should parse non-Ubuntu distros without error."""
        p = self._make_os_release(
            tmp_path,
            """\
            ID=debian
            VERSION_ID="12"
            """,
        )
        result = read_os_release(str(p))

        assert result["ID"] == "debian"
        assert result["VERSION_ID"] == "12"

    def test_returns_empty_dict_for_missing_file(self) -> None:
        """read_os_release should return {} when the file does not exist."""
        result = read_os_release("/nonexistent/path/os-release")
        assert result == {}

    def test_ignores_comment_lines(self, tmp_path: Path) -> None:
        """read_os_release should skip lines starting with '#'."""
        p = self._make_os_release(
            tmp_path,
            """\
            # This is a comment
            ID=ubuntu
            VERSION_ID="22.04"
            """,
        )
        result = read_os_release(str(p))
        assert "#" not in result
        assert result["ID"] == "ubuntu"

    # --- verify_ubuntu_2204 ---

    def test_returns_true_for_ubuntu_2204(self) -> None:
        """verify_ubuntu_2204 should return True for Ubuntu 22.04."""
        os_release = {"ID": "ubuntu", "VERSION_ID": "22.04"}
        assert verify_ubuntu_2204(os_release) is True

    def test_raises_for_ubuntu_2004(self) -> None:
        """verify_ubuntu_2204 should raise RuntimeError for Ubuntu 20.04."""
        os_release = {"ID": "ubuntu", "VERSION_ID": "20.04"}
        with pytest.raises(RuntimeError, match="Unsupported OS"):
            verify_ubuntu_2204(os_release)

    def test_raises_for_debian(self) -> None:
        """verify_ubuntu_2204 should raise RuntimeError for Debian."""
        os_release = {"ID": "debian", "VERSION_ID": "12"}
        with pytest.raises(RuntimeError, match="Unsupported OS"):
            verify_ubuntu_2204(os_release)

    def test_raises_for_centos(self) -> None:
        """verify_ubuntu_2204 should raise RuntimeError for CentOS."""
        os_release = {"ID": "centos", "VERSION_ID": "8"}
        with pytest.raises(RuntimeError, match="Unsupported OS"):
            verify_ubuntu_2204(os_release)

    def test_raises_for_empty_os_release(self) -> None:
        """verify_ubuntu_2204 should raise RuntimeError for an empty dict."""
        with pytest.raises(RuntimeError, match="Unsupported OS"):
            verify_ubuntu_2204({})

    def test_case_insensitive_id(self) -> None:
        """verify_ubuntu_2204 should handle uppercase ID values."""
        # The implementation lowercases the ID, so "Ubuntu" should work.
        os_release = {"ID": "Ubuntu", "VERSION_ID": "22.04"}
        assert verify_ubuntu_2204(os_release) is True


# ===========================================================================
# Tests for wsl.conf content
# ===========================================================================


class TestWslConf:
    """Tests that verify the wsl.conf file has the required content."""

    WSL_CONF_PATH = Path(__file__).parent.parent / "wsl.conf"

    def test_wsl_conf_exists(self) -> None:
        """The wsl.conf file should exist in the voip/ directory."""
        assert self.WSL_CONF_PATH.exists(), (
            f"wsl.conf not found at {self.WSL_CONF_PATH}"
        )

    def test_wsl_conf_contains_boot_section(self) -> None:
        """wsl.conf must contain the [boot] section header."""
        content = self.WSL_CONF_PATH.read_text(encoding="utf-8")
        assert "[boot]" in content, "wsl.conf is missing the [boot] section"

    def test_wsl_conf_enables_systemd(self) -> None:
        """wsl.conf must set systemd=true under [boot]."""
        content = self.WSL_CONF_PATH.read_text(encoding="utf-8")
        assert "systemd=true" in content, (
            "wsl.conf is missing 'systemd=true'"
        )

    def test_wsl_conf_boot_section_precedes_systemd(self) -> None:
        """[boot] must appear before systemd=true in wsl.conf."""
        content = self.WSL_CONF_PATH.read_text(encoding="utf-8")
        boot_pos = content.find("[boot]")
        systemd_pos = content.find("systemd=true")
        assert boot_pos != -1, "wsl.conf is missing [boot]"
        assert systemd_pos != -1, "wsl.conf is missing systemd=true"
        assert boot_pos < systemd_pos, (
            "[boot] must appear before systemd=true in wsl.conf"
        )

    def test_write_file_can_reproduce_wsl_conf(self, tmp_path: Path) -> None:
        """write_file should be able to write a valid wsl.conf to a temp path."""
        wsl_conf_content = "[boot]\nsystemd=true\n"
        target = tmp_path / "wsl.conf"

        write_file(target, wsl_conf_content)

        written = target.read_text(encoding="utf-8")
        assert "[boot]" in written
        assert "systemd=true" in written
