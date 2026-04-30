"""
test_setup_ami.py — Unit tests for setup_ami.py.

Covers sub-task 11.1:
  - manager.conf sets ``bindaddr=127.0.0.1`` (not ``0.0.0.0``)
  - The admin user section contains ``secret`` and ``read=all``
  - verify_ami_localhost_only() correctly parses ``ss -tlnp`` output

Requirements: 1.3, 14.1
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup — allow running from workspace root or voip/ directory
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from setup_ami import (
    MANAGER_CONF_CONTENT,
    AMI_PORT,
    write_manager_conf,
    verify_ami_localhost_only,
)


# ===========================================================================
# Sub-task 11.1 — Unit tests for AMI configuration
# ===========================================================================


class TestManagerConfContent:
    """
    Unit tests verifying the content of manager.conf.

    Requirements: 1.3, 14.1
    """

    def test_general_section_present(self) -> None:
        """manager.conf must have a [general] section header."""
        assert "[general]" in MANAGER_CONF_CONTENT, (
            "MANAGER_CONF_CONTENT does not contain '[general]' section header"
        )

    def test_enabled_yes(self) -> None:
        """manager.conf must contain ``enabled=yes``."""
        assert "enabled=yes" in MANAGER_CONF_CONTENT, (
            "MANAGER_CONF_CONTENT does not contain 'enabled=yes'"
        )

    def test_bindaddr_is_localhost(self) -> None:
        """
        manager.conf must bind to 127.0.0.1, not 0.0.0.0.

        This is the core security requirement: AMI must only be accessible
        from localhost.

        Requirements: 1.3, 14.1
        """
        assert "bindaddr=127.0.0.1" in MANAGER_CONF_CONTENT, (
            "MANAGER_CONF_CONTENT does not contain 'bindaddr=127.0.0.1'"
        )

    def test_bindaddr_is_not_all_interfaces(self) -> None:
        """
        manager.conf must NOT bind to 0.0.0.0 (all interfaces).

        Requirements: 1.3
        """
        assert "bindaddr=0.0.0.0" not in MANAGER_CONF_CONTENT, (
            "MANAGER_CONF_CONTENT must not contain 'bindaddr=0.0.0.0' — "
            "AMI must be restricted to localhost"
        )

    def test_port_is_5038(self) -> None:
        """manager.conf must set port=5038."""
        assert "port=5038" in MANAGER_CONF_CONTENT, (
            "MANAGER_CONF_CONTENT does not contain 'port=5038'"
        )

    def test_admin_section_present(self) -> None:
        """manager.conf must have an [admin] user section."""
        assert "[admin]" in MANAGER_CONF_CONTENT, (
            "MANAGER_CONF_CONTENT does not contain '[admin]' section header"
        )

    def test_admin_section_has_secret(self) -> None:
        """
        The [admin] section must contain a ``secret`` key.

        Requirements: 14.1
        """
        # Verify the key is present (value may be a placeholder)
        assert "secret=" in MANAGER_CONF_CONTENT, (
            "MANAGER_CONF_CONTENT does not contain a 'secret=' entry in the "
            "[admin] section"
        )

    def test_admin_section_has_read_all(self) -> None:
        """
        The [admin] section must contain ``read=all``.

        Requirements: 14.1
        """
        assert "read=all" in MANAGER_CONF_CONTENT, (
            "MANAGER_CONF_CONTENT does not contain 'read=all'"
        )

    def test_admin_section_has_write_all(self) -> None:
        """The [admin] section must contain ``write=all``."""
        assert "write=all" in MANAGER_CONF_CONTENT, (
            "MANAGER_CONF_CONTENT does not contain 'write=all'"
        )

    def test_admin_section_has_deny_all(self) -> None:
        """
        The [admin] section must deny all addresses by default before
        permitting localhost.

        Requirements: 1.3
        """
        assert "deny=0.0.0.0/0.0.0.0" in MANAGER_CONF_CONTENT, (
            "MANAGER_CONF_CONTENT does not contain 'deny=0.0.0.0/0.0.0.0'"
        )

    def test_admin_section_permits_localhost(self) -> None:
        """
        The [admin] section must explicitly permit 127.0.0.1.

        Requirements: 1.3
        """
        assert "permit=127.0.0.1/255.255.255.255" in MANAGER_CONF_CONTENT, (
            "MANAGER_CONF_CONTENT does not contain "
            "'permit=127.0.0.1/255.255.255.255'"
        )


class TestWriteManagerConf:
    """
    Unit tests for the write_manager_conf() function.

    Requirements: 1.3, 14.1
    """

    def test_creates_file(self, tmp_path: Path) -> None:
        """write_manager_conf should create the file at the given path."""
        target = tmp_path / "manager.conf"
        result = write_manager_conf(str(target))
        assert result == target
        assert target.exists()

    def test_file_content_matches_constant(self, tmp_path: Path) -> None:
        """write_manager_conf should write exactly MANAGER_CONF_CONTENT."""
        target = tmp_path / "manager.conf"
        write_manager_conf(str(target))
        assert target.read_text(encoding="utf-8") == MANAGER_CONF_CONTENT

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """write_manager_conf should create missing parent directories."""
        target = tmp_path / "asterisk" / "manager.conf"
        write_manager_conf(str(target))
        assert target.exists()

    def test_written_file_has_bindaddr_localhost(self, tmp_path: Path) -> None:
        """
        The written file must contain ``bindaddr=127.0.0.1``.

        Requirements: 1.3
        """
        target = tmp_path / "manager.conf"
        write_manager_conf(str(target))
        content = target.read_text(encoding="utf-8")
        assert "bindaddr=127.0.0.1" in content

    def test_written_file_has_secret(self, tmp_path: Path) -> None:
        """
        The written file must contain a ``secret=`` entry in the [admin]
        section.

        Requirements: 14.1
        """
        target = tmp_path / "manager.conf"
        write_manager_conf(str(target))
        content = target.read_text(encoding="utf-8")
        assert "secret=" in content

    def test_written_file_has_read_all(self, tmp_path: Path) -> None:
        """
        The written file must contain ``read=all`` in the [admin] section.

        Requirements: 14.1
        """
        target = tmp_path / "manager.conf"
        write_manager_conf(str(target))
        content = target.read_text(encoding="utf-8")
        assert "read=all" in content


# ===========================================================================
# Tests for verify_ami_localhost_only()
# ===========================================================================


class TestVerifyAmiLocalhostOnly:
    """
    Unit tests for verify_ami_localhost_only().

    The function must parse ``ss -tlnp`` output and return True only when
    port 5038 is bound to 127.0.0.1.

    Requirements: 1.3, 14.1
    """

    # Realistic ``ss -tlnp`` output samples
    _SS_LOCALHOST_ONLY = (
        "Netid  State   Recv-Q  Send-Q  Local Address:Port  Peer Address:Port\n"
        "tcp    LISTEN  0       10      127.0.0.1:5038      0.0.0.0:*\n"
        "tcp    LISTEN  0       128     0.0.0.0:22          0.0.0.0:*\n"
    )

    _SS_ALL_INTERFACES = (
        "Netid  State   Recv-Q  Send-Q  Local Address:Port  Peer Address:Port\n"
        "tcp    LISTEN  0       10      0.0.0.0:5038        0.0.0.0:*\n"
    )

    _SS_IPV6_ALL = (
        "Netid  State   Recv-Q  Send-Q  Local Address:Port  Peer Address:Port\n"
        "tcp    LISTEN  0       10      [::]:5038           [::]:*\n"
    )

    _SS_PORT_NOT_PRESENT = (
        "Netid  State   Recv-Q  Send-Q  Local Address:Port  Peer Address:Port\n"
        "tcp    LISTEN  0       128     0.0.0.0:22          0.0.0.0:*\n"
    )

    _SS_EMPTY = ""

    def test_returns_true_when_bound_to_localhost(self) -> None:
        """
        Returns True when port 5038 is bound to 127.0.0.1.

        Requirements: 1.3
        """
        assert verify_ami_localhost_only(self._SS_LOCALHOST_ONLY) is True

    def test_returns_false_when_bound_to_all_interfaces(self) -> None:
        """
        Returns False when port 5038 is bound to 0.0.0.0 (all interfaces).

        Requirements: 1.3
        """
        assert verify_ami_localhost_only(self._SS_ALL_INTERFACES) is False

    def test_returns_false_when_bound_to_ipv6_all(self) -> None:
        """
        Returns False when port 5038 is bound to :: (all IPv6 interfaces).

        Requirements: 1.3
        """
        assert verify_ami_localhost_only(self._SS_IPV6_ALL) is False

    def test_returns_false_when_port_not_present(self) -> None:
        """
        Returns False when port 5038 does not appear in ss output (AMI not
        running).

        Requirements: 1.3
        """
        assert verify_ami_localhost_only(self._SS_PORT_NOT_PRESENT) is False

    def test_returns_false_for_empty_output(self) -> None:
        """Returns False for empty ss output."""
        assert verify_ami_localhost_only(self._SS_EMPTY) is False

    def test_ignores_other_ports_on_localhost(self) -> None:
        """
        Does not confuse other ports bound to 127.0.0.1 with port 5038.
        """
        ss_output = (
            "Netid  State   Recv-Q  Send-Q  Local Address:Port  Peer Address:Port\n"
            "tcp    LISTEN  0       10      127.0.0.1:8080      0.0.0.0:*\n"
            "tcp    LISTEN  0       128     0.0.0.0:22          0.0.0.0:*\n"
        )
        assert verify_ami_localhost_only(ss_output) is False

    def test_port_5038_on_localhost_among_many_entries(self) -> None:
        """
        Returns True when port 5038 on 127.0.0.1 appears among many other
        listening sockets.
        """
        ss_output = (
            "Netid  State   Recv-Q  Send-Q  Local Address:Port  Peer Address:Port\n"
            "tcp    LISTEN  0       128     0.0.0.0:22          0.0.0.0:*\n"
            "tcp    LISTEN  0       10      127.0.0.1:5038      0.0.0.0:*\n"
            "tcp    LISTEN  0       10      0.0.0.0:443         0.0.0.0:*\n"
            "tcp    LISTEN  0       10      0.0.0.0:5061        0.0.0.0:*\n"
        )
        assert verify_ami_localhost_only(ss_output) is True

    def test_ami_port_constant_is_5038(self) -> None:
        """AMI_PORT constant must equal 5038."""
        assert AMI_PORT == 5038
