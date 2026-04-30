"""
test_generate_linphone_guide.py — Unit tests for generate_linphone_guide.py.

Sub-task 13.1 — Unit tests for guide generation:
  - The generated Markdown contains all required sections (account setup,
    internal calling, outbound calling, troubleshooting, admin commands).
  - Port 5061 and transport TLS appear in the account setup section.
  - WSL2 troubleshooting and Windows host commands are present.

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup — allow running from workspace root or voip/tests/
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from generate_linphone_guide import LINPHONE_GUIDE_CONTENT, generate_guide

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _section_content(content: str, header: str) -> str:
    """
    Return the text of the section starting with *header* up to the next
    same-level (##) header or end of file.
    """
    lines = content.splitlines()
    in_section = False
    section_lines: list[str] = []
    for line in lines:
        if line.strip() == header:
            in_section = True
            section_lines.append(line)
            continue
        if in_section and line.startswith("## ") and line.strip() != header:
            break
        if in_section:
            section_lines.append(line)
    return "\n".join(section_lines)


# ===========================================================================
# Section presence tests
# Requirements: 15.1, 15.2, 15.3, 15.4, 15.5
# ===========================================================================


class TestRequiredSections:
    """Verify all five required H2 sections are present in the guide."""

    def test_account_setup_section_present(self) -> None:
        """
        Guide must contain the account setup section.

        Requirements: 15.1
        """
        assert "## 1. Account Setup in Linphone" in LINPHONE_GUIDE_CONTENT

    def test_internal_calling_section_present(self) -> None:
        """
        Guide must contain the internal calling section.

        Requirements: 15.2
        """
        assert "## 2. Making Internal Calls" in LINPHONE_GUIDE_CONTENT

    def test_outbound_calling_section_present(self) -> None:
        """
        Guide must contain the outbound international calling section.

        Requirements: 15.3
        """
        assert "## 3. Making Outbound International Calls" in LINPHONE_GUIDE_CONTENT

    def test_troubleshooting_section_present(self) -> None:
        """
        Guide must contain the troubleshooting section.

        Requirements: 15.4
        """
        assert "## 4. Troubleshooting" in LINPHONE_GUIDE_CONTENT

    def test_admin_commands_section_present(self) -> None:
        """
        Guide must contain the administrator commands section.

        Requirements: 15.5
        """
        assert "## 5. Administrator Commands" in LINPHONE_GUIDE_CONTENT

    def test_all_five_h2_sections_present(self) -> None:
        """All five required H2 sections must be present together."""
        required = [
            "## 1. Account Setup in Linphone",
            "## 2. Making Internal Calls",
            "## 3. Making Outbound International Calls",
            "## 4. Troubleshooting",
            "## 5. Administrator Commands",
        ]
        for header in required:
            assert header in LINPHONE_GUIDE_CONTENT, (
                f"Required section header not found: {header!r}"
            )


# ===========================================================================
# Account setup section: port 5061 and TLS
# Requirements: 15.1, 3.3
# ===========================================================================


class TestAccountSetupSection:
    """Verify port 5061 and TLS transport appear in the account setup section."""

    @pytest.fixture(scope="class")
    def account_section(self) -> str:
        return _section_content(
            LINPHONE_GUIDE_CONTENT, "## 1. Account Setup in Linphone"
        )

    def test_port_5061_in_account_setup(self, account_section: str) -> None:
        """
        Port 5061 must appear in the account setup section.

        Requirements: 15.1, 3.3
        """
        assert "5061" in account_section, (
            "Port 5061 not found in account setup section"
        )

    def test_tls_transport_in_account_setup(self, account_section: str) -> None:
        """
        TLS transport must appear in the account setup section.

        Requirements: 15.1, 3.3
        """
        assert "TLS" in account_section, (
            "TLS transport not found in account setup section"
        )

    def test_srtp_instructions_in_account_setup(
        self, account_section: str
    ) -> None:
        """
        SRTP enable instructions must appear in the account setup section.

        Requirements: 3.4
        """
        assert "SRTP" in account_section, (
            "SRTP instructions not found in account setup section"
        )

    def test_codec_instructions_in_account_setup(
        self, account_section: str
    ) -> None:
        """
        Codec preference instructions (ulaw/alaw) must appear in account setup.

        Requirements: 12.5
        """
        assert "ulaw" in account_section.lower() or "PCMU" in account_section, (
            "G.711 ulaw codec instructions not found in account setup section"
        )
        assert "alaw" in account_section.lower() or "PCMA" in account_section, (
            "G.711 alaw codec instructions not found in account setup section"
        )

    def test_reregistration_interval_in_account_setup(
        self, account_section: str
    ) -> None:
        """
        Re-registration interval of 1800 seconds must appear in account setup.

        Requirements: 3.7
        """
        assert "1800" in account_section, (
            "Re-registration interval (1800 seconds) not found in account setup section"
        )


# ===========================================================================
# Internal calling section
# Requirements: 15.2
# ===========================================================================


class TestInternalCallingSection:
    """Verify internal calling instructions are correct."""

    @pytest.fixture(scope="class")
    def internal_section(self) -> str:
        return _section_content(
            LINPHONE_GUIDE_CONTENT, "## 2. Making Internal Calls"
        )

    def test_three_digit_extension_mentioned(
        self, internal_section: str
    ) -> None:
        """
        Internal calling section must mention dialling a 3-digit extension.

        Requirements: 15.2
        """
        assert "3-digit" in internal_section or "three-digit" in internal_section.lower(), (
            "3-digit extension instruction not found in internal calling section"
        )

    def test_extension_range_mentioned(self, internal_section: str) -> None:
        """
        Internal calling section must reference the 101–105 extension range.

        Requirements: 15.2
        """
        assert "101" in internal_section, (
            "Extension range (101) not found in internal calling section"
        )


# ===========================================================================
# Outbound calling section
# Requirements: 15.3
# ===========================================================================


class TestOutboundCallingSection:
    """Verify outbound international calling instructions are correct."""

    @pytest.fixture(scope="class")
    def outbound_section(self) -> str:
        return _section_content(
            LINPHONE_GUIDE_CONTENT, "## 3. Making Outbound International Calls"
        )

    def test_e164_format_mentioned(self, outbound_section: str) -> None:
        """
        Outbound section must mention E.164 format.

        Requirements: 15.3
        """
        assert "E.164" in outbound_section or "+1" in outbound_section, (
            "E.164 format not found in outbound calling section"
        )

    def test_plus_prefix_example_present(self, outbound_section: str) -> None:
        """
        Outbound section must include an example with + prefix.

        Requirements: 15.3
        """
        assert "+" in outbound_section, (
            "No + prefix example found in outbound calling section"
        )


# ===========================================================================
# Troubleshooting section
# Requirements: 15.4
# ===========================================================================


class TestTroubleshootingSection:
    """Verify all required troubleshooting topics are covered."""

    @pytest.fixture(scope="class")
    def troubleshooting_section(self) -> str:
        return _section_content(
            LINPHONE_GUIDE_CONTENT, "## 4. Troubleshooting"
        )

    def test_registration_failure_covered(
        self, troubleshooting_section: str
    ) -> None:
        """
        Troubleshooting must cover registration failure.

        Requirements: 15.4
        """
        assert (
            "registration" in troubleshooting_section.lower()
            or "Registration" in troubleshooting_section
        ), "Registration failure not covered in troubleshooting section"

    def test_one_way_audio_covered(self, troubleshooting_section: str) -> None:
        """
        Troubleshooting must cover one-way audio.

        Requirements: 15.4
        """
        assert "one-way" in troubleshooting_section.lower() or (
            "one way" in troubleshooting_section.lower()
        ), "One-way audio not covered in troubleshooting section"

    def test_trunk_unavailable_covered(
        self, troubleshooting_section: str
    ) -> None:
        """
        Troubleshooting must cover trunk unavailable.

        Requirements: 15.4
        """
        assert "trunk" in troubleshooting_section.lower(), (
            "Trunk unavailable not covered in troubleshooting section"
        )

    def test_banned_ip_recovery_covered(
        self, troubleshooting_section: str
    ) -> None:
        """
        Troubleshooting must cover banned IP recovery.

        Requirements: 15.4
        """
        assert "ban" in troubleshooting_section.lower(), (
            "Banned IP recovery not covered in troubleshooting section"
        )

    def test_wsl2_not_starting_covered(
        self, troubleshooting_section: str
    ) -> None:
        """
        Troubleshooting must cover WSL2 not starting on boot.

        Requirements: 15.4
        """
        assert "WSL2" in troubleshooting_section or "wsl2" in troubleshooting_section.lower(), (
            "WSL2 not starting on boot not covered in troubleshooting section"
        )

    def test_task_scheduler_mentioned(
        self, troubleshooting_section: str
    ) -> None:
        """
        Troubleshooting must mention checking Task Scheduler for WSL2 boot issue.

        Requirements: 15.4
        """
        assert "Task Scheduler" in troubleshooting_section, (
            "Task Scheduler not mentioned in WSL2 troubleshooting"
        )

    def test_wsl_startup_script_mentioned(
        self, troubleshooting_section: str
    ) -> None:
        """
        Troubleshooting must mention running wsl_startup.ps1 manually.

        Requirements: 15.4
        """
        assert "wsl_startup.ps1" in troubleshooting_section, (
            "wsl_startup.ps1 not mentioned in WSL2 troubleshooting"
        )


# ===========================================================================
# Administrator commands section
# Requirements: 15.5
# ===========================================================================


class TestAdminCommandsSection:
    """Verify all required administrator commands are present."""

    @pytest.fixture(scope="class")
    def admin_section(self) -> str:
        return _section_content(
            LINPHONE_GUIDE_CONTENT, "## 5. Administrator Commands"
        )

    def test_pjsip_show_registrations_present(
        self, admin_section: str
    ) -> None:
        """
        Admin section must include 'asterisk -rx "pjsip show registrations"'.

        Requirements: 15.5
        """
        assert 'pjsip show registrations' in admin_section, (
            "pjsip show registrations command not found in admin section"
        )

    def test_core_show_channels_present(self, admin_section: str) -> None:
        """
        Admin section must include 'asterisk -rx "core show channels"'.

        Requirements: 15.5
        """
        assert "core show channels" in admin_section, (
            "core show channels command not found in admin section"
        )

    def test_fail2ban_status_present(self, admin_section: str) -> None:
        """
        Admin section must include 'fail2ban-client status asterisk'.

        Requirements: 15.5
        """
        assert "fail2ban-client status asterisk" in admin_section, (
            "fail2ban-client status asterisk not found in admin section"
        )

    def test_fail2ban_unban_present(self, admin_section: str) -> None:
        """
        Admin section must include 'fail2ban-client set asterisk unbanip <IP>'.

        Requirements: 15.5
        """
        assert "fail2ban-client set asterisk unbanip" in admin_section, (
            "fail2ban-client unbanip command not found in admin section"
        )

    def test_windows_portproxy_command_present(
        self, admin_section: str
    ) -> None:
        """
        Admin section must include 'netsh interface portproxy show all'.

        Requirements: 15.5
        """
        assert "netsh interface portproxy show all" in admin_section, (
            "netsh portproxy show all command not found in admin section"
        )

    def test_windows_firewall_command_present(
        self, admin_section: str
    ) -> None:
        """
        Admin section must include the Get-NetFirewallRule VoIP filter command.

        Requirements: 15.5
        """
        assert 'Get-NetFirewallRule' in admin_section, (
            "Get-NetFirewallRule command not found in admin section"
        )
        assert 'VoIP' in admin_section, (
            "VoIP firewall filter not found in admin section"
        )

    def test_wsl_hostname_command_present(self, admin_section: str) -> None:
        """
        Admin section must include 'wsl hostname -I'.

        Requirements: 15.5
        """
        assert "wsl hostname -I" in admin_section, (
            "wsl hostname -I command not found in admin section"
        )


# ===========================================================================
# generate_guide() function tests
# ===========================================================================


class TestGenerateGuide:
    """Tests for the generate_guide() function."""

    def test_creates_file(self, tmp_path: Path) -> None:
        """generate_guide must create the output file."""
        target = tmp_path / "linphone_setup.md"
        result = generate_guide(str(target))
        assert target.exists(), "Output file was not created"

    def test_returns_path(self, tmp_path: Path) -> None:
        """generate_guide must return a Path object."""
        target = tmp_path / "linphone_setup.md"
        result = generate_guide(str(target))
        assert isinstance(result, Path), (
            f"Expected Path, got {type(result).__name__}"
        )

    def test_file_content_matches_constant(self, tmp_path: Path) -> None:
        """File content must match LINPHONE_GUIDE_CONTENT."""
        target = tmp_path / "linphone_setup.md"
        generate_guide(str(target))
        actual = target.read_text(encoding="utf-8")
        assert actual == LINPHONE_GUIDE_CONTENT, (
            "Written file content does not match LINPHONE_GUIDE_CONTENT"
        )

    def test_default_filename(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """generate_guide() with no args writes to linphone_setup.md in cwd."""
        monkeypatch.chdir(tmp_path)
        result = generate_guide()
        assert result.name == "linphone_setup.md"
        assert (tmp_path / "linphone_setup.md").exists()

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """generate_guide must create missing parent directories."""
        target = tmp_path / "docs" / "voip" / "linphone_setup.md"
        generate_guide(str(target))
        assert target.exists(), "File not created in nested directory"

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        """generate_guide must overwrite an existing file."""
        target = tmp_path / "linphone_setup.md"
        target.write_text("old content", encoding="utf-8")
        generate_guide(str(target))
        content = target.read_text(encoding="utf-8")
        assert "old content" not in content
        assert "## 1. Account Setup in Linphone" in content

    def test_generated_file_contains_port_5061(self, tmp_path: Path) -> None:
        """Generated file must contain port 5061."""
        target = tmp_path / "linphone_setup.md"
        generate_guide(str(target))
        content = target.read_text(encoding="utf-8")
        assert "5061" in content

    def test_generated_file_contains_tls(self, tmp_path: Path) -> None:
        """Generated file must contain TLS transport reference."""
        target = tmp_path / "linphone_setup.md"
        generate_guide(str(target))
        content = target.read_text(encoding="utf-8")
        assert "TLS" in content

    def test_generated_file_contains_wsl2_troubleshooting(
        self, tmp_path: Path
    ) -> None:
        """Generated file must contain WSL2 troubleshooting content."""
        target = tmp_path / "linphone_setup.md"
        generate_guide(str(target))
        content = target.read_text(encoding="utf-8")
        assert "WSL2" in content
        assert "wsl_startup.ps1" in content
        assert "Task Scheduler" in content

    def test_generated_file_contains_windows_host_commands(
        self, tmp_path: Path
    ) -> None:
        """Generated file must contain Windows host commands."""
        target = tmp_path / "linphone_setup.md"
        generate_guide(str(target))
        content = target.read_text(encoding="utf-8")
        assert "netsh interface portproxy show all" in content
        assert "Get-NetFirewallRule" in content
        assert "wsl hostname -I" in content
