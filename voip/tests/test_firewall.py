"""
test_firewall.py — Tests for setup_firewall.py.

Covers:
  Sub-task 4.1 — Property test for firewall rule generation
    Property 3 (Firewall Rule Completeness): For any generated rule set (with
    any admin IP range), the default INPUT policy is DROP, port 5061 TCP is
    allowed, port 5060 is dropped, and UDP 10000–20000 is allowed.
    **Validates: Requirements 8.6, 8.7**

  Sub-task 4.2 — Unit tests for firewall script
    - iptables-save output is parsed and re-applied correctly
    - Rule ordering places ESTABLISHED/RELATED before DROP rules

Requirements: 8.6, 8.7, 8.8, 8.9
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List
from unittest.mock import call, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Path setup — allow running from workspace root
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from setup_firewall import (
    apply_rules,
    generate_ruleset,
    get_rule_order,
    parse_iptables_save,
)


# ===========================================================================
# Helpers
# ===========================================================================


def _ruleset_as_strings(ruleset: List[List[str]]) -> List[str]:
    """Join each argv list into a single string for easy searching."""
    return [" ".join(rule) for rule in ruleset]


# ---------------------------------------------------------------------------
# Hypothesis strategy: valid CIDR notation for IPv4
# ---------------------------------------------------------------------------

# Generate octets 0–255 and prefix lengths 8–32 to produce valid CIDR ranges
# that are representative of real admin IP ranges.
_ipv4_octet = st.integers(min_value=0, max_value=255)
_prefix_len = st.integers(min_value=8, max_value=32)

_cidr_strategy = st.builds(
    lambda a, b, c, d, p: f"{a}.{b}.{c}.{d}/{p}",
    _ipv4_octet,
    _ipv4_octet,
    _ipv4_octet,
    _ipv4_octet,
    _prefix_len,
)


# ===========================================================================
# Sub-task 4.1 — Property test: Firewall Rule Completeness
# **Validates: Requirements 8.6, 8.7**
# ===========================================================================


class TestFirewallRuleCompletenessProperty:
    """
    Property 3 (Firewall Rule Completeness):

    For any generated rule set (with any admin IP range), the following must
    always hold:
      1. The default INPUT policy is DROP.
      2. TCP port 5061 is ACCEPT-ed.
      3. TCP port 5060 is DROP-ped.
      4. UDP port 5060 is DROP-ped.
      5. UDP ports 10000–20000 are ACCEPT-ed.

    **Validates: Requirements 8.6, 8.7**
    """

    @given(admin_ip_range=_cidr_strategy)
    @settings(max_examples=100)
    def test_default_input_policy_is_drop(self, admin_ip_range: str) -> None:
        """
        Property: For any admin IP range, the ruleset always sets the default
        INPUT policy to DROP.

        **Validates: Requirements 8.6**
        """
        ruleset = generate_ruleset(admin_ip_range)
        rules = _ruleset_as_strings(ruleset)

        assert any(
            "iptables -P INPUT DROP" in r for r in rules
        ), f"No 'iptables -P INPUT DROP' found in ruleset for range {admin_ip_range!r}"

    @given(admin_ip_range=_cidr_strategy)
    @settings(max_examples=100)
    def test_tcp_5061_is_accepted(self, admin_ip_range: str) -> None:
        """
        Property: For any admin IP range, the ruleset always allows TCP 5061.

        **Validates: Requirements 8.6**
        """
        ruleset = generate_ruleset(admin_ip_range)
        rules = _ruleset_as_strings(ruleset)

        assert any(
            "-p tcp" in r and "--dport 5061" in r and "-j ACCEPT" in r
            for r in rules
        ), f"No TCP 5061 ACCEPT rule found for range {admin_ip_range!r}"

    @given(admin_ip_range=_cidr_strategy)
    @settings(max_examples=100)
    def test_tcp_5060_is_dropped(self, admin_ip_range: str) -> None:
        """
        Property: For any admin IP range, the ruleset always drops TCP 5060.

        **Validates: Requirements 8.6, 8.7**
        """
        ruleset = generate_ruleset(admin_ip_range)
        rules = _ruleset_as_strings(ruleset)

        assert any(
            "-p tcp" in r and "--dport 5060" in r and "-j DROP" in r
            for r in rules
        ), f"No TCP 5060 DROP rule found for range {admin_ip_range!r}"

    @given(admin_ip_range=_cidr_strategy)
    @settings(max_examples=100)
    def test_udp_5060_is_dropped(self, admin_ip_range: str) -> None:
        """
        Property: For any admin IP range, the ruleset always drops UDP 5060.

        **Validates: Requirements 8.6, 8.7**
        """
        ruleset = generate_ruleset(admin_ip_range)
        rules = _ruleset_as_strings(ruleset)

        assert any(
            "-p udp" in r and "--dport 5060" in r and "-j DROP" in r
            for r in rules
        ), f"No UDP 5060 DROP rule found for range {admin_ip_range!r}"

    @given(admin_ip_range=_cidr_strategy)
    @settings(max_examples=100)
    def test_udp_10000_20000_is_accepted(self, admin_ip_range: str) -> None:
        """
        Property: For any admin IP range, the ruleset always allows UDP
        10000–20000 (RTP).

        **Validates: Requirements 8.6**
        """
        ruleset = generate_ruleset(admin_ip_range)
        rules = _ruleset_as_strings(ruleset)

        assert any(
            "-p udp" in r and "--dport 10000:20000" in r and "-j ACCEPT" in r
            for r in rules
        ), f"No UDP 10000:20000 ACCEPT rule found for range {admin_ip_range!r}"

    @given(admin_ip_range=_cidr_strategy)
    @settings(max_examples=100)
    def test_forward_policy_is_drop(self, admin_ip_range: str) -> None:
        """
        Property: For any admin IP range, the ruleset always sets the default
        FORWARD policy to DROP.

        **Validates: Requirements 8.7**
        """
        ruleset = generate_ruleset(admin_ip_range)
        rules = _ruleset_as_strings(ruleset)

        assert any(
            "iptables -P FORWARD DROP" in r for r in rules
        ), f"No 'iptables -P FORWARD DROP' found for range {admin_ip_range!r}"

    @given(admin_ip_range=_cidr_strategy)
    @settings(max_examples=100)
    def test_admin_ip_range_appears_in_ssh_rule(
        self, admin_ip_range: str
    ) -> None:
        """
        Property: The admin IP range passed to generate_ruleset() always
        appears in the SSH (TCP 22) rule.

        **Validates: Requirements 8.6**
        """
        ruleset = generate_ruleset(admin_ip_range)
        rules = _ruleset_as_strings(ruleset)

        assert any(
            "--dport 22" in r and admin_ip_range in r and "-j ACCEPT" in r
            for r in rules
        ), (
            f"Admin IP range {admin_ip_range!r} not found in SSH rule. "
            f"Rules: {rules}"
        )


# ===========================================================================
# Sub-task 4.2 — Unit tests for firewall script
# ===========================================================================


class TestParseIptablesSave:
    """
    Tests for parse_iptables_save().

    Verifies that iptables-save output is parsed correctly and that the
    resulting rule strings can be re-applied.

    Requirements: 8.8
    """

    # A realistic sample of iptables-save output
    SAMPLE_IPTABLES_SAVE = """\
# Generated by iptables-save v1.8.7 on Mon Jan  1 00:00:00 2024
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -i lo -j ACCEPT
-A INPUT -p tcp --dport 22 -s 10.0.0.0/8 -j ACCEPT
-A INPUT -p tcp --dport 5061 -j ACCEPT
-A INPUT -p tcp --dport 5060 -j DROP
-A INPUT -p udp --dport 5060 -j DROP
-A INPUT -p udp --dport 10000:20000 -j ACCEPT
-A INPUT -p tcp --dport 443 -j ACCEPT
COMMIT
# Completed on Mon Jan  1 00:00:00 2024
"""

    def test_parses_rule_lines(self) -> None:
        """parse_iptables_save should return all -A and : lines."""
        rules = parse_iptables_save(self.SAMPLE_IPTABLES_SAVE)

        # Should include chain policy lines and -A rules
        assert any(r.startswith(":INPUT") for r in rules)
        assert any(r.startswith(":FORWARD") for r in rules)
        assert any(r.startswith("-A INPUT") for r in rules)

    def test_excludes_comment_lines(self) -> None:
        """parse_iptables_save should exclude lines starting with '#'."""
        rules = parse_iptables_save(self.SAMPLE_IPTABLES_SAVE)
        assert not any(r.startswith("#") for r in rules)

    def test_excludes_table_header_lines(self) -> None:
        """parse_iptables_save should exclude lines starting with '*'."""
        rules = parse_iptables_save(self.SAMPLE_IPTABLES_SAVE)
        assert not any(r.startswith("*") for r in rules)

    def test_excludes_commit_lines(self) -> None:
        """parse_iptables_save should exclude COMMIT lines."""
        rules = parse_iptables_save(self.SAMPLE_IPTABLES_SAVE)
        assert "COMMIT" not in rules

    def test_excludes_empty_lines(self) -> None:
        """parse_iptables_save should exclude empty/blank lines."""
        rules = parse_iptables_save(self.SAMPLE_IPTABLES_SAVE)
        assert all(r.strip() for r in rules)

    def test_all_append_rules_present(self) -> None:
        """All -A INPUT rules from the sample should be in the parsed output."""
        rules = parse_iptables_save(self.SAMPLE_IPTABLES_SAVE)
        append_rules = [r for r in rules if r.startswith("-A INPUT")]

        expected_rules = [
            "-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT",
            "-A INPUT -i lo -j ACCEPT",
            "-A INPUT -p tcp --dport 22 -s 10.0.0.0/8 -j ACCEPT",
            "-A INPUT -p tcp --dport 5061 -j ACCEPT",
            "-A INPUT -p tcp --dport 5060 -j DROP",
            "-A INPUT -p udp --dport 5060 -j DROP",
            "-A INPUT -p udp --dport 10000:20000 -j ACCEPT",
            "-A INPUT -p tcp --dport 443 -j ACCEPT",
        ]
        for expected in expected_rules:
            assert expected in append_rules, (
                f"Expected rule not found in parsed output: {expected!r}"
            )

    def test_empty_input_returns_empty_list(self) -> None:
        """parse_iptables_save with empty string should return []."""
        assert parse_iptables_save("") == []

    def test_only_comments_returns_empty_list(self) -> None:
        """parse_iptables_save with only comment lines should return []."""
        output = "# comment 1\n# comment 2\n"
        assert parse_iptables_save(output) == []

    def test_parsed_rules_contain_key_ports(self) -> None:
        """
        Parsed rules should contain entries for all required ports so they
        can be re-applied to restore the firewall state.

        Requirements: 8.8
        """
        rules = parse_iptables_save(self.SAMPLE_IPTABLES_SAVE)
        rule_text = "\n".join(rules)

        assert "5061" in rule_text, "Port 5061 not found in parsed rules"
        assert "5060" in rule_text, "Port 5060 not found in parsed rules"
        assert "10000:20000" in rule_text, "RTP range not found in parsed rules"
        assert "443" in rule_text, "Port 443 not found in parsed rules"


class TestRuleOrdering:
    """
    Tests that verify the rule ordering contract.

    The ESTABLISHED/RELATED rule must appear before any DROP rules so that
    existing connections are not interrupted when the default policy is DROP.

    Requirements: 8.9
    """

    def test_established_related_before_drop_rules(self) -> None:
        """
        ESTABLISHED/RELATED ACCEPT rule must appear before DROP rules in the
        generated ruleset.

        Requirements: 8.9
        """
        ruleset = generate_ruleset()
        rules = _ruleset_as_strings(ruleset)

        # Find the index of the ESTABLISHED/RELATED rule
        established_idx = next(
            (i for i, r in enumerate(rules) if "ESTABLISHED,RELATED" in r),
            None,
        )
        assert established_idx is not None, (
            "ESTABLISHED/RELATED rule not found in ruleset"
        )

        # Find the index of the first DROP rule (excluding policy lines)
        first_drop_idx = next(
            (
                i
                for i, r in enumerate(rules)
                if "-j DROP" in r
            ),
            None,
        )
        assert first_drop_idx is not None, "No DROP rule found in ruleset"

        assert established_idx < first_drop_idx, (
            f"ESTABLISHED/RELATED rule (index {established_idx}) must appear "
            f"before the first DROP rule (index {first_drop_idx})"
        )

    def test_loopback_before_drop_rules(self) -> None:
        """
        Loopback ACCEPT rule must appear before DROP rules.

        Requirements: 8.9
        """
        ruleset = generate_ruleset()
        rules = _ruleset_as_strings(ruleset)

        loopback_idx = next(
            (i for i, r in enumerate(rules) if "-i lo" in r and "-j ACCEPT" in r),
            None,
        )
        assert loopback_idx is not None, "Loopback rule not found in ruleset"

        first_drop_idx = next(
            (i for i, r in enumerate(rules) if "-j DROP" in r),
            None,
        )
        assert first_drop_idx is not None, "No DROP rule found in ruleset"

        assert loopback_idx < first_drop_idx, (
            f"Loopback rule (index {loopback_idx}) must appear before the "
            f"first DROP rule (index {first_drop_idx})"
        )

    def test_flush_before_policy_and_rules(self) -> None:
        """
        The INPUT flush (-F INPUT) must be the first rule in the ruleset.

        Requirements: 8.9
        """
        ruleset = generate_ruleset()
        rules = _ruleset_as_strings(ruleset)

        assert rules[0] == "iptables -F INPUT", (
            f"Expected 'iptables -F INPUT' as first rule, got {rules[0]!r}"
        )

    def test_default_policy_set_before_append_rules(self) -> None:
        """
        The default INPUT policy (-P INPUT DROP) must appear before any
        -A INPUT append rules.

        Requirements: 8.9
        """
        ruleset = generate_ruleset()
        rules = _ruleset_as_strings(ruleset)

        policy_idx = next(
            (i for i, r in enumerate(rules) if "iptables -P INPUT DROP" in r),
            None,
        )
        assert policy_idx is not None, "INPUT DROP policy not found"

        first_append_idx = next(
            (i for i, r in enumerate(rules) if "-A INPUT" in r),
            None,
        )
        assert first_append_idx is not None, "No -A INPUT rule found"

        assert policy_idx < first_append_idx, (
            f"Policy rule (index {policy_idx}) must appear before the first "
            f"-A INPUT rule (index {first_append_idx})"
        )


class TestGetRuleOrder:
    """Tests for get_rule_order()."""

    def test_returns_list_of_strings(self) -> None:
        """get_rule_order should return a list of strings."""
        ruleset = generate_ruleset()
        order = get_rule_order(ruleset)
        assert isinstance(order, list)
        assert all(isinstance(s, str) for s in order)

    def test_length_matches_ruleset(self) -> None:
        """get_rule_order should return one description per rule."""
        ruleset = generate_ruleset()
        order = get_rule_order(ruleset)
        assert len(order) == len(ruleset)

    def test_descriptions_contain_iptables(self) -> None:
        """Each description should contain 'iptables'."""
        ruleset = generate_ruleset()
        order = get_rule_order(ruleset)
        assert all("iptables" in desc for desc in order)


class TestApplyRules:
    """Tests for apply_rules() — uses mocking to avoid requiring root."""

    def test_apply_rules_calls_subprocess_for_each_rule(self) -> None:
        """apply_rules should call subprocess.run once per rule."""
        ruleset = generate_ruleset()

        with patch("setup_firewall.subprocess.run") as mock_run:
            apply_rules(ruleset)

        assert mock_run.call_count == len(ruleset), (
            f"Expected {len(ruleset)} subprocess.run calls, "
            f"got {mock_run.call_count}"
        )

    def test_apply_rules_passes_check_true(self) -> None:
        """apply_rules should pass check=True to subprocess.run."""
        ruleset = [["iptables", "-F", "INPUT"]]

        with patch("setup_firewall.subprocess.run") as mock_run:
            apply_rules(ruleset)

        mock_run.assert_called_once_with(
            ["iptables", "-F", "INPUT"], check=True
        )

    def test_apply_rules_passes_correct_argv(self) -> None:
        """apply_rules should pass each rule's argv list unchanged."""
        ruleset = generate_ruleset()

        with patch("setup_firewall.subprocess.run") as mock_run:
            apply_rules(ruleset)

        actual_calls = [c.args[0] for c in mock_run.call_args_list]
        assert actual_calls == ruleset


class TestGenerateRuleset:
    """Unit tests for generate_ruleset() with the default admin IP range."""

    def test_returns_list(self) -> None:
        """generate_ruleset should return a list."""
        assert isinstance(generate_ruleset(), list)

    def test_each_element_is_list_of_strings(self) -> None:
        """Each rule should be a list of strings."""
        for rule in generate_ruleset():
            assert isinstance(rule, list)
            assert all(isinstance(s, str) for s in rule)

    def test_contains_flush_input(self) -> None:
        """Ruleset must contain a flush INPUT rule."""
        rules = _ruleset_as_strings(generate_ruleset())
        assert any("iptables -F INPUT" in r for r in rules)

    def test_contains_input_drop_policy(self) -> None:
        """Ruleset must set INPUT policy to DROP."""
        rules = _ruleset_as_strings(generate_ruleset())
        assert any("iptables -P INPUT DROP" in r for r in rules)

    def test_contains_forward_drop_policy(self) -> None:
        """Ruleset must set FORWARD policy to DROP."""
        rules = _ruleset_as_strings(generate_ruleset())
        assert any("iptables -P FORWARD DROP" in r for r in rules)

    def test_contains_established_related_rule(self) -> None:
        """Ruleset must allow ESTABLISHED/RELATED connections."""
        rules = _ruleset_as_strings(generate_ruleset())
        assert any("ESTABLISHED,RELATED" in r and "ACCEPT" in r for r in rules)

    def test_contains_loopback_rule(self) -> None:
        """Ruleset must allow loopback interface."""
        rules = _ruleset_as_strings(generate_ruleset())
        assert any("-i lo" in r and "ACCEPT" in r for r in rules)

    def test_contains_ssh_rule_with_default_admin_range(self) -> None:
        """Ruleset must allow SSH from the default admin IP range."""
        from setup_firewall import ADMIN_IP_RANGE

        rules = _ruleset_as_strings(generate_ruleset())
        assert any(
            "--dport 22" in r and ADMIN_IP_RANGE in r and "ACCEPT" in r
            for r in rules
        )

    def test_contains_sip_tls_rule(self) -> None:
        """Ruleset must allow TCP 5061 (SIP/TLS)."""
        rules = _ruleset_as_strings(generate_ruleset())
        assert any(
            "-p tcp" in r and "--dport 5061" in r and "ACCEPT" in r
            for r in rules
        )

    def test_contains_tcp_5060_drop(self) -> None:
        """Ruleset must drop TCP 5060 (plain SIP)."""
        rules = _ruleset_as_strings(generate_ruleset())
        assert any(
            "-p tcp" in r and "--dport 5060" in r and "DROP" in r
            for r in rules
        )

    def test_contains_udp_5060_drop(self) -> None:
        """Ruleset must drop UDP 5060 (plain SIP)."""
        rules = _ruleset_as_strings(generate_ruleset())
        assert any(
            "-p udp" in r and "--dport 5060" in r and "DROP" in r
            for r in rules
        )

    def test_contains_rtp_rule(self) -> None:
        """Ruleset must allow UDP 10000–20000 (RTP)."""
        rules = _ruleset_as_strings(generate_ruleset())
        assert any(
            "-p udp" in r and "--dport 10000:20000" in r and "ACCEPT" in r
            for r in rules
        )

    def test_contains_https_ami_rule(self) -> None:
        """Ruleset must allow TCP 443 (HTTPS/AMI)."""
        rules = _ruleset_as_strings(generate_ruleset())
        assert any(
            "-p tcp" in r and "--dport 443" in r and "ACCEPT" in r
            for r in rules
        )

    def test_custom_admin_ip_range_used(self) -> None:
        """generate_ruleset should use the provided admin IP range."""
        custom_range = "192.168.1.0/24"
        rules = _ruleset_as_strings(generate_ruleset(custom_range))
        assert any(
            "--dport 22" in r and custom_range in r for r in rules
        )
