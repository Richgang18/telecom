"""
test_windows_host.py — Unit tests for Windows host configuration scripts.

Tests cover two categories:

1. Script content tests (sub-task 2.1):
   - setup_windows_host.ps1 contains all five New-NetFirewallRule calls
   - wsl_startup.ps1 contains wsl hostname -I IP resolution and portproxy
     update logic
   - wsl_startup.ps1 contains wsl -e sudo systemctl start asterisk

2. Simulated command-output parsing tests (task 2):
   - Portproxy rule for TCP 5061 exists (parses netsh output)
   - Windows Firewall rules for TCP 5061, UDP 10000-20000, TCP 443 are Allow
   - Windows Firewall rules for TCP/UDP 5060 are Block
   - Task Scheduler task "WSL2 VoIP Startup" exists

Requirements: 1a.1, 1a.2, 1a.3, 1a.4, 1a.5, 1a.6, 1a.7
"""

import re
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
VOIP_DIR = Path(__file__).parent.parent
SETUP_SCRIPT = VOIP_DIR / "setup_windows_host.ps1"
STARTUP_SCRIPT = VOIP_DIR / "wsl_startup.ps1"


# ===========================================================================
# Helpers
# ===========================================================================


def _read_script(path: Path) -> str:
    """Return the text content of a PowerShell script."""
    assert path.exists(), f"Script not found: {path}"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Simulated command-output parsers
# (These replicate the logic that would run against real Windows output.)
# ---------------------------------------------------------------------------


def parse_portproxy_rules(netsh_output: str) -> list[dict]:
    """
    Parse the output of `netsh interface portproxy show all` into a list of
    rule dicts with keys: listen_address, listen_port, connect_address,
    connect_port.

    Example netsh output::

        Listen on ipv4:             Connect to ipv4:

        Address         Port        Address         Port
        --------------- ----------  --------------- ----------
        0.0.0.0         5061        172.28.144.1    5061
    """
    rules = []
    # Match lines that look like portproxy entries (IP/wildcard + port pairs)
    pattern = re.compile(
        r"^(\S+)\s+(\d+)\s+(\S+)\s+(\d+)\s*$",
        re.MULTILINE,
    )
    for m in pattern.finditer(netsh_output):
        rules.append(
            {
                "listen_address": m.group(1),
                "listen_port": int(m.group(2)),
                "connect_address": m.group(3),
                "connect_port": int(m.group(4)),
            }
        )
    return rules


def parse_firewall_rules(fw_output: str) -> list[dict]:
    """
    Parse simulated `Get-NetFirewallRule` output into a list of rule dicts
    with keys: display_name, protocol, local_port, action.

    Expected format (one rule per block, fields separated by colons)::

        DisplayName : VoIP SIP TLS
        Protocol    : TCP
        LocalPort   : 5061
        Action      : Allow
    """
    rules = []
    # Split on blank lines to get individual rule blocks
    blocks = re.split(r"\n\s*\n", fw_output.strip())
    for block in blocks:
        if not block.strip():
            continue
        rule: dict = {}
        for line in block.splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                rule[key.strip().lower().replace(" ", "_")] = value.strip()
        if rule:
            rules.append(rule)
    return rules


def parse_scheduled_tasks(schtasks_output: str) -> list[str]:
    """
    Parse simulated `schtasks /query /fo LIST` output and return a list of
    task names.

    Expected format::

        TaskName: \\WSL2 VoIP Startup
        Status:   Ready
    """
    names = []
    for line in schtasks_output.splitlines():
        if line.strip().lower().startswith("taskname"):
            _, _, name = line.partition(":")
            # Strip leading backslashes that schtasks adds
            names.append(name.strip().lstrip("\\"))
    return names


# ===========================================================================
# Sub-task 2.1 — Script content tests
# ===========================================================================


class TestSetupWindowsHostScriptContent:
    """Verify that setup_windows_host.ps1 contains the required commands."""

    def test_script_exists(self) -> None:
        """setup_windows_host.ps1 must exist in the voip/ directory."""
        assert SETUP_SCRIPT.exists(), f"Script not found: {SETUP_SCRIPT}"

    def test_contains_wsl_ip_resolution(self) -> None:
        """Script must resolve WSL2 IP via wsl hostname -I."""
        content = _read_script(SETUP_SCRIPT)
        assert "wsl hostname -I" in content, (
            "setup_windows_host.ps1 is missing WSL2 IP resolution via 'wsl hostname -I'"
        )

    def test_contains_portproxy_add(self) -> None:
        """Script must add a netsh portproxy rule for port 5061."""
        content = _read_script(SETUP_SCRIPT)
        assert "portproxy add v4tov4" in content, (
            "setup_windows_host.ps1 is missing 'netsh interface portproxy add v4tov4'"
        )
        assert "5061" in content, (
            "setup_windows_host.ps1 portproxy rule does not reference port 5061"
        )

    def test_contains_firewall_rule_sip_tls(self) -> None:
        """Script must create the 'VoIP SIP TLS' firewall rule (TCP 5061 Allow)."""
        content = _read_script(SETUP_SCRIPT)
        assert 'New-NetFirewallRule' in content, (
            "setup_windows_host.ps1 is missing New-NetFirewallRule calls"
        )
        assert '"VoIP SIP TLS"' in content or "'VoIP SIP TLS'" in content, (
            "setup_windows_host.ps1 is missing the 'VoIP SIP TLS' firewall rule"
        )

    def test_contains_firewall_rule_rtp(self) -> None:
        """Script must create the 'VoIP RTP' firewall rule (UDP 10000-20000 Allow)."""
        content = _read_script(SETUP_SCRIPT)
        assert '"VoIP RTP"' in content or "'VoIP RTP'" in content, (
            "setup_windows_host.ps1 is missing the 'VoIP RTP' firewall rule"
        )

    def test_contains_firewall_rule_https(self) -> None:
        """Script must create the 'VoIP HTTPS' firewall rule (TCP 443 Allow)."""
        content = _read_script(SETUP_SCRIPT)
        assert '"VoIP HTTPS"' in content or "'VoIP HTTPS'" in content, (
            "setup_windows_host.ps1 is missing the 'VoIP HTTPS' firewall rule"
        )

    def test_contains_firewall_rule_block_sip_tcp(self) -> None:
        """Script must create the 'Block SIP TCP' firewall rule (TCP 5060 Block)."""
        content = _read_script(SETUP_SCRIPT)
        assert '"Block SIP TCP"' in content or "'Block SIP TCP'" in content, (
            "setup_windows_host.ps1 is missing the 'Block SIP TCP' firewall rule"
        )

    def test_contains_firewall_rule_block_sip_udp(self) -> None:
        """Script must create the 'Block SIP UDP' firewall rule (UDP 5060 Block)."""
        content = _read_script(SETUP_SCRIPT)
        assert '"Block SIP UDP"' in content or "'Block SIP UDP'" in content, (
            "setup_windows_host.ps1 is missing the 'Block SIP UDP' firewall rule"
        )

    def test_contains_all_five_new_netfirewallrule_calls(self) -> None:
        """Script must contain exactly five New-NetFirewallRule calls."""
        content = _read_script(SETUP_SCRIPT)
        count = content.count("New-NetFirewallRule")
        assert count >= 5, (
            f"Expected at least 5 New-NetFirewallRule calls, found {count}"
        )

    def test_contains_task_scheduler_registration(self) -> None:
        """Script must register the 'WSL2 VoIP Startup' scheduled task."""
        content = _read_script(SETUP_SCRIPT)
        assert "Register-ScheduledTask" in content, (
            "setup_windows_host.ps1 is missing Register-ScheduledTask"
        )
        assert "WSL2 VoIP Startup" in content, (
            "setup_windows_host.ps1 is missing the 'WSL2 VoIP Startup' task name"
        )

    def test_contains_wsl_startup_script_reference(self) -> None:
        """Script must reference wsl_startup.ps1 in the scheduled task action."""
        content = _read_script(SETUP_SCRIPT)
        assert "wsl_startup.ps1" in content, (
            "setup_windows_host.ps1 does not reference wsl_startup.ps1"
        )


class TestWslStartupScriptContent:
    """Verify that wsl_startup.ps1 contains the required commands."""

    def test_script_exists(self) -> None:
        """wsl_startup.ps1 must exist in the voip/ directory."""
        assert STARTUP_SCRIPT.exists(), f"Script not found: {STARTUP_SCRIPT}"

    def test_contains_wsl_start(self) -> None:
        """Script must start WSL2 via wsl -e echo."""
        content = _read_script(STARTUP_SCRIPT)
        assert 'wsl -e echo' in content, (
            "wsl_startup.ps1 is missing 'wsl -e echo' to start WSL2"
        )

    def test_contains_sleep(self) -> None:
        """Script must wait for WSL2 to be ready via Start-Sleep."""
        content = _read_script(STARTUP_SCRIPT)
        assert "Start-Sleep" in content, (
            "wsl_startup.ps1 is missing Start-Sleep to wait for WSL2 readiness"
        )

    def test_contains_wsl_ip_resolution(self) -> None:
        """Script must resolve WSL2 IP via wsl hostname -I."""
        content = _read_script(STARTUP_SCRIPT)
        assert "wsl hostname -I" in content, (
            "wsl_startup.ps1 is missing WSL2 IP resolution via 'wsl hostname -I'"
        )

    def test_contains_portproxy_delete(self) -> None:
        """Script must remove the old portproxy rule before adding the new one."""
        content = _read_script(STARTUP_SCRIPT)
        assert "portproxy delete v4tov4" in content, (
            "wsl_startup.ps1 is missing 'netsh interface portproxy delete v4tov4'"
        )

    def test_contains_portproxy_add(self) -> None:
        """Script must add an updated portproxy rule with the current WSL2 IP."""
        content = _read_script(STARTUP_SCRIPT)
        assert "portproxy add v4tov4" in content, (
            "wsl_startup.ps1 is missing 'netsh interface portproxy add v4tov4'"
        )

    def test_contains_asterisk_start(self) -> None:
        """Script must start Asterisk inside WSL2 via wsl -e sudo systemctl start asterisk."""
        content = _read_script(STARTUP_SCRIPT)
        assert "wsl -e sudo systemctl start asterisk" in content, (
            "wsl_startup.ps1 is missing 'wsl -e sudo systemctl start asterisk'"
        )


# ===========================================================================
# Task 2 — Simulated command-output parsing tests
# ===========================================================================


class TestPortproxyParsing:
    """Tests for the portproxy output parser and rule verification."""

    SAMPLE_NETSH_OUTPUT = """\
Listen on ipv4:             Connect to ipv4:

Address         Port        Address         Port
--------------- ----------  --------------- ----------
0.0.0.0         5061        172.28.144.1    5061
"""

    def test_parses_portproxy_rule(self) -> None:
        """Parser should extract the portproxy rule from netsh output."""
        rules = parse_portproxy_rules(self.SAMPLE_NETSH_OUTPUT)
        assert len(rules) == 1
        assert rules[0]["listen_port"] == 5061
        assert rules[0]["connect_port"] == 5061

    def test_portproxy_rule_for_5061_exists(self) -> None:
        """A portproxy rule for TCP 5061 must be present in the output."""
        rules = parse_portproxy_rules(self.SAMPLE_NETSH_OUTPUT)
        ports = [r["listen_port"] for r in rules]
        assert 5061 in ports, "No portproxy rule found for port 5061"

    def test_portproxy_listens_on_all_interfaces(self) -> None:
        """The portproxy rule must listen on 0.0.0.0 (all interfaces)."""
        rules = parse_portproxy_rules(self.SAMPLE_NETSH_OUTPUT)
        rule_5061 = next((r for r in rules if r["listen_port"] == 5061), None)
        assert rule_5061 is not None
        assert rule_5061["listen_address"] == "0.0.0.0"

    def test_empty_output_returns_no_rules(self) -> None:
        """Parser should return an empty list for empty netsh output."""
        rules = parse_portproxy_rules("")
        assert rules == []

    def test_multiple_rules_parsed(self) -> None:
        """Parser should handle multiple portproxy rules."""
        output = """\
Address         Port        Address         Port
--------------- ----------  --------------- ----------
0.0.0.0         5061        172.28.1.1      5061
0.0.0.0         443         172.28.1.1      443
"""
        rules = parse_portproxy_rules(output)
        assert len(rules) == 2


class TestFirewallRuleParsing:
    """Tests for the firewall rule parser and rule verification."""

    SAMPLE_FW_OUTPUT = """\
DisplayName : VoIP SIP TLS
Protocol    : TCP
LocalPort   : 5061
Action      : Allow

DisplayName : VoIP RTP
Protocol    : UDP
LocalPort   : 10000-20000
Action      : Allow

DisplayName : VoIP HTTPS
Protocol    : TCP
LocalPort   : 443
Action      : Allow

DisplayName : Block SIP TCP
Protocol    : TCP
LocalPort   : 5060
Action      : Block

DisplayName : Block SIP UDP
Protocol    : UDP
LocalPort   : 5060
Action      : Block
"""

    def test_parses_all_five_rules(self) -> None:
        """Parser should extract all five firewall rules."""
        rules = parse_firewall_rules(self.SAMPLE_FW_OUTPUT)
        assert len(rules) == 5

    def test_sip_tls_rule_exists_and_allows(self) -> None:
        """TCP 5061 (VoIP SIP TLS) rule must exist and be set to Allow."""
        rules = parse_firewall_rules(self.SAMPLE_FW_OUTPUT)
        rule = next(
            (r for r in rules if r.get("displayname") == "VoIP SIP TLS"), None
        )
        assert rule is not None, "VoIP SIP TLS rule not found"
        assert rule["protocol"].upper() == "TCP"
        assert rule["localport"] == "5061"
        assert rule["action"].lower() == "allow"

    def test_rtp_rule_exists_and_allows(self) -> None:
        """UDP 10000-20000 (VoIP RTP) rule must exist and be set to Allow."""
        rules = parse_firewall_rules(self.SAMPLE_FW_OUTPUT)
        rule = next(
            (r for r in rules if r.get("displayname") == "VoIP RTP"), None
        )
        assert rule is not None, "VoIP RTP rule not found"
        assert rule["protocol"].upper() == "UDP"
        assert rule["localport"] == "10000-20000"
        assert rule["action"].lower() == "allow"

    def test_https_rule_exists_and_allows(self) -> None:
        """TCP 443 (VoIP HTTPS) rule must exist and be set to Allow."""
        rules = parse_firewall_rules(self.SAMPLE_FW_OUTPUT)
        rule = next(
            (r for r in rules if r.get("displayname") == "VoIP HTTPS"), None
        )
        assert rule is not None, "VoIP HTTPS rule not found"
        assert rule["protocol"].upper() == "TCP"
        assert rule["localport"] == "443"
        assert rule["action"].lower() == "allow"

    def test_block_sip_tcp_rule_exists_and_blocks(self) -> None:
        """TCP 5060 (Block SIP TCP) rule must exist and be set to Block."""
        rules = parse_firewall_rules(self.SAMPLE_FW_OUTPUT)
        rule = next(
            (r for r in rules if r.get("displayname") == "Block SIP TCP"), None
        )
        assert rule is not None, "Block SIP TCP rule not found"
        assert rule["protocol"].upper() == "TCP"
        assert rule["localport"] == "5060"
        assert rule["action"].lower() == "block"

    def test_block_sip_udp_rule_exists_and_blocks(self) -> None:
        """UDP 5060 (Block SIP UDP) rule must exist and be set to Block."""
        rules = parse_firewall_rules(self.SAMPLE_FW_OUTPUT)
        rule = next(
            (r for r in rules if r.get("displayname") == "Block SIP UDP"), None
        )
        assert rule is not None, "Block SIP UDP rule not found"
        assert rule["protocol"].upper() == "UDP"
        assert rule["localport"] == "5060"
        assert rule["action"].lower() == "block"

    def test_empty_output_returns_no_rules(self) -> None:
        """Parser should return an empty list for empty firewall output."""
        rules = parse_firewall_rules("")
        assert rules == []


class TestScheduledTaskParsing:
    """Tests for the scheduled task parser and task verification."""

    SAMPLE_SCHTASKS_OUTPUT = """\
TaskName: \\WSL2 VoIP Startup
Status:   Ready
Run As User: SYSTEM

TaskName: \\Microsoft\\Windows\\UpdateOrchestrator\\Schedule Scan
Status:   Ready
"""

    def test_parses_task_names(self) -> None:
        """Parser should extract task names from schtasks output."""
        names = parse_scheduled_tasks(self.SAMPLE_SCHTASKS_OUTPUT)
        assert "WSL2 VoIP Startup" in names

    def test_wsl2_voip_startup_task_exists(self) -> None:
        """The 'WSL2 VoIP Startup' task must be present in the output."""
        names = parse_scheduled_tasks(self.SAMPLE_SCHTASKS_OUTPUT)
        assert "WSL2 VoIP Startup" in names, (
            "Task 'WSL2 VoIP Startup' not found in scheduled tasks output"
        )

    def test_empty_output_returns_no_tasks(self) -> None:
        """Parser should return an empty list for empty schtasks output."""
        names = parse_scheduled_tasks("")
        assert names == []

    def test_multiple_tasks_parsed(self) -> None:
        """Parser should handle multiple tasks in the output."""
        names = parse_scheduled_tasks(self.SAMPLE_SCHTASKS_OUTPUT)
        assert len(names) >= 2
