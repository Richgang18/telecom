"""
test_fail2ban.py — Tests for setup_fail2ban.py.

Covers:
  Sub-task 5.1 — Property test for fail2ban filter regex
    Property 5 (Brute Force Protection): The fail2ban regex matches Asterisk
    authentication failure log lines and does NOT match successful registration
    lines.
    **Validates: Requirements 9.1, 9.5**

  Sub-task 5.2 — Unit tests for fail2ban configuration
    - Jail config file content contains correct maxretry, findtime, bantime
    - Filter regex matches known Asterisk failure log samples
    - Filter regex does NOT match successful registration lines

Requirements: 9.1, 9.2, 9.3, 9.5
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Path setup — allow running from workspace root or voip/ directory
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from setup_fail2ban import (
    ASTERISK_FILTER_REGEX,
    FILTER_CONF_CONTENT,
    JAIL_CONF_CONTENT,
    write_filter_conf,
    write_jail_conf,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# The fail2ban filter uses <HOST> as a placeholder for the IP address.
# For direct Python regex testing we replace <HOST> with a real IPv4 pattern.
_HOST_PATTERN = r"(?:\d{1,3}\.){3}\d{1,3}"
_TESTABLE_REGEX = ASTERISK_FILTER_REGEX.replace("<HOST>", _HOST_PATTERN)

# Also replace the fail2ban macro %(__prefix_line)s with an empty string
# so the regex can be applied directly to raw log lines.
_TESTABLE_REGEX = re.sub(r"%\(__prefix_line\)s\|?", "", _TESTABLE_REGEX)
# Clean up any leading | inside the outer group
_TESTABLE_REGEX = _TESTABLE_REGEX.replace("(|", "(")

_COMPILED_REGEX = re.compile(_TESTABLE_REGEX)


def _matches(line: str) -> bool:
    """Return True if the compiled filter regex matches *line*."""
    return bool(_COMPILED_REGEX.search(line))


# ---------------------------------------------------------------------------
# Known failure log lines (must match)
# ---------------------------------------------------------------------------

FAILURE_LINES = [
    # Pattern 1: PJSIP distributor — from the task spec
    (
        "[2024-01-15 10:23:45] NOTICE[1234] res_pjsip/pjsip_distributor.c: "
        "Request 'REGISTER' from '\"101\" <sip:101@pbx.local>' "
        "failed for '1.2.3.4:5061' (callid: abc123) - No matching endpoint found"
    ),
    # Pattern 1 variant: different reason
    (
        "[2024-01-15 10:23:45] NOTICE[1234] res_pjsip/pjsip_distributor.c: "
        "Request 'REGISTER' from '\"102\" <sip:102@pbx.local>' "
        "failed for '10.0.0.1:5060' (callid: xyz789) - Wrong password"
    ),
    # Pattern 2: chan_sip — from the task spec
    (
        "[2024-01-15 10:23:45] NOTICE[1234] chan_sip.c: "
        "Registration from '\"101\" <sip:101@pbx.local>' "
        "failed for '1.2.3.4' - Wrong password"
    ),
    # Pattern 2 variant: with port
    (
        "[2024-01-15 10:23:45] NOTICE[1234] chan_sip.c: "
        "Registration from '\"103\" <sip:103@192.168.1.1>' "
        "failed for '192.168.1.1:5060' - Wrong password"
    ),
    # Pattern 3: PJSIP registrar
    (
        "[2024-01-01 12:00:00] NOTICE[1234] res_pjsip_registrar.c: "
        "Registration failed for '101' - Wrong password"
    ),
    # Pattern 4: Security event FailedACL
    (
        "[2024-01-01 12:00:00] SECURITY[1234] res_security_log.c: "
        'SecurityEvent="FailedACL",EventTV="2024-01-01T12:00:00.000-0000",'
        'Severity="Error",Service="SIP",AccountID="101",'
        'SessionID="0x7f1234","RemoteAddress="IPV4/UDP/1.2.3.4/5060"'
    ),
]

# ---------------------------------------------------------------------------
# Known success log lines (must NOT match)
# ---------------------------------------------------------------------------

SUCCESS_LINES = [
    # Successful registration — from the task spec
    (
        "[2024-01-15 10:23:45] NOTICE[1234] res_pjsip/pjsip_distributor.c: "
        "Request 'REGISTER' from '\"101\" <sip:101@pbx.local>' - Successful"
    ),
    # Generic successful registration
    (
        "[2024-01-15 10:23:45] NOTICE[1234] res_pjsip_registrar.c: "
        "Endpoint '101' is now Reachable"
    ),
    # Successful call setup
    (
        "[2024-01-15 10:23:45] NOTICE[1234] chan_sip.c: "
        "Call from '101' to extension '102' accepted"
    ),
    # Informational log line
    (
        "[2024-01-15 10:23:45] VERBOSE[1234] pbx.c: "
        "Executing [102@internal:1] Dial"
    ),
    # Unrelated log line
    (
        "[2024-01-15 10:23:45] DEBUG[1234] chan_sip.c: "
        "SIP/2.0 200 OK"
    ),
]


# ===========================================================================
# Sub-task 5.1 — Property test: Brute Force Protection regex
# **Validates: Requirements 9.1, 9.5**
# ===========================================================================


class TestBruteForceProtectionProperty:
    """
    Property 5 (Brute Force Protection):

    The fail2ban regex must match Asterisk authentication failure log lines
    and must NOT match successful registration lines.

    **Validates: Requirements 9.1, 9.5**
    """

    # -----------------------------------------------------------------------
    # Hypothesis strategies for generating log lines
    # -----------------------------------------------------------------------

    # Strategy: generate realistic IPv4 addresses
    _ipv4 = st.builds(
        lambda a, b, c, d: f"{a}.{b}.{c}.{d}",
        st.integers(min_value=1, max_value=254),
        st.integers(min_value=0, max_value=255),
        st.integers(min_value=0, max_value=255),
        st.integers(min_value=1, max_value=254),
    )

    # Strategy: generate realistic SIP ports
    _port = st.integers(min_value=1024, max_value=65535)

    # Strategy: generate realistic extension numbers
    _ext = st.integers(min_value=100, max_value=199).map(str)

    # Strategy: generate realistic thread IDs
    _tid = st.integers(min_value=1, max_value=99999)

    # Strategy: generate realistic callids
    _callid = st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
        min_size=4,
        max_size=20,
    )

    # Strategy: generate failure reasons for pjsip_distributor
    _pjsip_reason = st.sampled_from([
        "No matching endpoint found",
        "Wrong password",
        "Failed to authenticate",
        "Not found",
    ])

    @given(
        ip=_ipv4,
        port=_port,
        ext=_ext,
        tid=_tid,
        callid=_callid,
        reason=_pjsip_reason,
    )
    @settings(max_examples=100)
    def test_pjsip_distributor_failure_always_matches(
        self,
        ip: str,
        port: int,
        ext: str,
        tid: int,
        callid: str,
        reason: str,
    ) -> None:
        """
        Property: For any valid PJSIP distributor failure log line (with any
        IP, port, extension, thread ID, callid, and reason), the filter regex
        always matches.

        **Validates: Requirements 9.1, 9.5**
        """
        line = (
            f"[2024-01-15 10:23:45] NOTICE[{tid}] res_pjsip/pjsip_distributor.c: "
            f"Request 'REGISTER' from '\"{ext}\" <sip:{ext}@pbx.local>' "
            f"failed for '{ip}:{port}' (callid: {callid}) - {reason}"
        )
        assert _matches(line), (
            f"Filter regex did not match PJSIP distributor failure line:\n  {line!r}"
        )

    @given(
        ip=_ipv4,
        port=_port,
        ext=_ext,
        tid=_tid,
    )
    @settings(max_examples=100)
    def test_chan_sip_failure_with_port_always_matches(
        self,
        ip: str,
        port: int,
        ext: str,
        tid: int,
    ) -> None:
        """
        Property: For any valid chan_sip failure log line with IP:port, the
        filter regex always matches.

        **Validates: Requirements 9.1, 9.5**
        """
        line = (
            f"[2024-01-15 10:23:45] NOTICE[{tid}] chan_sip.c: "
            f"Registration from '\"{ext}\" <sip:{ext}@pbx.local>' "
            f"failed for '{ip}:{port}' - Wrong password"
        )
        assert _matches(line), (
            f"Filter regex did not match chan_sip failure line (with port):\n  {line!r}"
        )

    @given(
        ip=_ipv4,
        ext=_ext,
        tid=_tid,
    )
    @settings(max_examples=100)
    def test_chan_sip_failure_without_port_always_matches(
        self,
        ip: str,
        ext: str,
        tid: int,
    ) -> None:
        """
        Property: For any valid chan_sip failure log line with IP only (no
        port), the filter regex always matches.

        **Validates: Requirements 9.1, 9.5**
        """
        line = (
            f"[2024-01-15 10:23:45] NOTICE[{tid}] chan_sip.c: "
            f"Registration from '\"{ext}\" <sip:{ext}@pbx.local>' "
            f"failed for '{ip}' - Wrong password"
        )
        assert _matches(line), (
            f"Filter regex did not match chan_sip failure line (no port):\n  {line!r}"
        )

    @given(
        ext=_ext,
        tid=_tid,
    )
    @settings(max_examples=50)
    def test_successful_registration_never_matches(
        self,
        ext: str,
        tid: int,
    ) -> None:
        """
        Property: For any successful registration log line, the filter regex
        never matches.

        **Validates: Requirements 9.1, 9.5**
        """
        line = (
            f"[2024-01-15 10:23:45] NOTICE[{tid}] res_pjsip/pjsip_distributor.c: "
            f"Request 'REGISTER' from '\"{ext}\" <sip:{ext}@pbx.local>' - Successful"
        )
        assert not _matches(line), (
            f"Filter regex incorrectly matched successful registration line:\n  {line!r}"
        )

    @given(
        ext=_ext,
        tid=_tid,
    )
    @settings(max_examples=50)
    def test_reachable_notice_never_matches(
        self,
        ext: str,
        tid: int,
    ) -> None:
        """
        Property: Endpoint reachability notices never match the failure regex.

        **Validates: Requirements 9.5**
        """
        line = (
            f"[2024-01-15 10:23:45] NOTICE[{tid}] res_pjsip_registrar.c: "
            f"Endpoint '{ext}' is now Reachable"
        )
        assert not _matches(line), (
            f"Filter regex incorrectly matched reachability notice:\n  {line!r}"
        )


# ===========================================================================
# Sub-task 5.2 — Unit tests for fail2ban configuration
# ===========================================================================


class TestJailConfigContent:
    """
    Unit tests verifying the jail configuration file content.

    Requirements: 9.2, 9.3
    """

    def test_maxretry_is_5(self) -> None:
        """
        Jail config must set maxretry=5.

        Requirements: 9.2
        """
        assert "maxretry = 5" in JAIL_CONF_CONTENT, (
            "JAIL_CONF_CONTENT does not contain 'maxretry = 5'"
        )

    def test_findtime_is_60(self) -> None:
        """
        Jail config must set findtime=60 (seconds).

        Requirements: 9.2
        """
        assert "findtime = 60" in JAIL_CONF_CONTENT, (
            "JAIL_CONF_CONTENT does not contain 'findtime = 60'"
        )

    def test_bantime_is_3600(self) -> None:
        """
        Jail config must set bantime=3600 (1 hour).

        Requirements: 9.3
        """
        # The config uses aligned spacing: "bantime  = 3600"
        assert "bantime" in JAIL_CONF_CONTENT and "3600" in JAIL_CONF_CONTENT, (
            "JAIL_CONF_CONTENT does not contain bantime = 3600"
        )
        # Extract the bantime value
        import re as _re
        m = _re.search(r"bantime\s*=\s*(\d+)", JAIL_CONF_CONTENT)
        assert m is not None, "bantime setting not found in JAIL_CONF_CONTENT"
        assert m.group(1) == "3600", (
            f"bantime value is {m.group(1)!r}, expected '3600'"
        )

    def test_logpath_is_asterisk_messages(self) -> None:
        """
        Jail config must point to /var/log/asterisk/messages.

        Requirements: 9.1
        """
        assert "logpath  = /var/log/asterisk/messages" in JAIL_CONF_CONTENT, (
            "JAIL_CONF_CONTENT does not contain correct logpath"
        )

    def test_action_is_iptables_allports(self) -> None:
        """
        Jail config must use iptables-allports action.

        Requirements: 9.4
        """
        assert "action   = iptables-allports" in JAIL_CONF_CONTENT, (
            "JAIL_CONF_CONTENT does not contain 'action   = iptables-allports'"
        )

    def test_jail_is_enabled(self) -> None:
        """Jail config must have enabled = true."""
        assert "enabled  = true" in JAIL_CONF_CONTENT, (
            "JAIL_CONF_CONTENT does not contain 'enabled  = true'"
        )

    def test_filter_is_asterisk(self) -> None:
        """Jail config must reference the asterisk filter."""
        assert "filter   = asterisk" in JAIL_CONF_CONTENT, (
            "JAIL_CONF_CONTENT does not contain 'filter   = asterisk'"
        )

    def test_jail_section_header(self) -> None:
        """Jail config must have [asterisk] section header."""
        assert "[asterisk]" in JAIL_CONF_CONTENT, (
            "JAIL_CONF_CONTENT does not contain '[asterisk]' section header"
        )

    def test_write_jail_conf_creates_file(self, tmp_path: Path) -> None:
        """write_jail_conf should create the file at the given path."""
        target = tmp_path / "asterisk.conf"
        result = write_jail_conf(str(target))
        assert result == target
        assert target.exists()
        assert target.read_text(encoding="utf-8") == JAIL_CONF_CONTENT

    def test_write_jail_conf_creates_parent_dirs(self, tmp_path: Path) -> None:
        """write_jail_conf should create parent directories as needed."""
        target = tmp_path / "jail.d" / "asterisk.conf"
        write_jail_conf(str(target))
        assert target.exists()


class TestFilterConfigContent:
    """
    Unit tests verifying the filter configuration file content.

    Requirements: 9.5
    """

    def test_filter_conf_has_definition_section(self) -> None:
        """Filter config must have a [Definition] section."""
        assert "[Definition]" in FILTER_CONF_CONTENT, (
            "FILTER_CONF_CONTENT does not contain '[Definition]' section"
        )

    def test_filter_conf_has_failregex(self) -> None:
        """Filter config must define failregex."""
        assert "failregex" in FILTER_CONF_CONTENT, (
            "FILTER_CONF_CONTENT does not contain 'failregex'"
        )

    def test_filter_conf_has_includes_section(self) -> None:
        """Filter config must include common.conf."""
        assert "[INCLUDES]" in FILTER_CONF_CONTENT, (
            "FILTER_CONF_CONTENT does not contain '[INCLUDES]' section"
        )
        assert "before = common.conf" in FILTER_CONF_CONTENT, (
            "FILTER_CONF_CONTENT does not include 'before = common.conf'"
        )

    def test_write_filter_conf_creates_file(self, tmp_path: Path) -> None:
        """write_filter_conf should create the file at the given path."""
        target = tmp_path / "asterisk.conf"
        result = write_filter_conf(str(target))
        assert result == target
        assert target.exists()
        assert target.read_text(encoding="utf-8") == FILTER_CONF_CONTENT

    def test_write_filter_conf_creates_parent_dirs(self, tmp_path: Path) -> None:
        """write_filter_conf should create parent directories as needed."""
        target = tmp_path / "filter.d" / "asterisk.conf"
        write_filter_conf(str(target))
        assert target.exists()


class TestFilterRegexMatchesFailureLines:
    """
    Unit tests verifying the filter regex matches known Asterisk failure log
    samples.

    Requirements: 9.5
    """

    @pytest.mark.parametrize("line", FAILURE_LINES)
    def test_matches_known_failure_line(self, line: str) -> None:
        """
        Filter regex must match each known Asterisk authentication failure
        log line.

        Requirements: 9.5
        """
        assert _matches(line), (
            f"Filter regex did not match known failure line:\n  {line!r}"
        )

    def test_matches_pjsip_distributor_no_matching_endpoint(self) -> None:
        """
        Filter regex must match the exact pjsip_distributor format from the
        task specification.

        Requirements: 9.1, 9.5
        """
        line = (
            "[2024-01-15 10:23:45] NOTICE[1234] res_pjsip/pjsip_distributor.c: "
            "Request 'REGISTER' from '\"101\" <sip:101@pbx.local>' "
            "failed for '1.2.3.4:5061' (callid: abc123) - No matching endpoint found"
        )
        assert _matches(line), (
            f"Filter regex did not match pjsip_distributor failure line:\n  {line!r}"
        )

    def test_matches_chan_sip_wrong_password(self) -> None:
        """
        Filter regex must match the exact chan_sip format from the task
        specification.

        Requirements: 9.1, 9.5
        """
        line = (
            "[2024-01-15 10:23:45] NOTICE[1234] chan_sip.c: "
            "Registration from '\"101\" <sip:101@pbx.local>' "
            "failed for '1.2.3.4' - Wrong password"
        )
        assert _matches(line), (
            f"Filter regex did not match chan_sip failure line:\n  {line!r}"
        )

    def test_matches_pjsip_registrar_wrong_password(self) -> None:
        """
        Filter regex must match PJSIP registrar wrong password lines.

        Requirements: 9.5
        """
        line = (
            "[2024-01-01 12:00:00] NOTICE[1234] res_pjsip_registrar.c: "
            "Registration failed for '101' - Wrong password"
        )
        assert _matches(line), (
            f"Filter regex did not match pjsip_registrar failure line:\n  {line!r}"
        )


class TestFilterRegexDoesNotMatchSuccessLines:
    """
    Unit tests verifying the filter regex does NOT match successful
    registration log lines.

    Requirements: 9.5
    """

    @pytest.mark.parametrize("line", SUCCESS_LINES)
    def test_does_not_match_success_line(self, line: str) -> None:
        """
        Filter regex must NOT match successful registration or informational
        log lines.

        Requirements: 9.5
        """
        assert not _matches(line), (
            f"Filter regex incorrectly matched success/info line:\n  {line!r}"
        )

    def test_does_not_match_exact_successful_spec_line(self) -> None:
        """
        Filter regex must NOT match the exact successful line from the task
        specification.

        Requirements: 9.5
        """
        line = (
            "[2024-01-15 10:23:45] NOTICE[1234] res_pjsip/pjsip_distributor.c: "
            "Request 'REGISTER' from '\"101\" <sip:101@pbx.local>' - Successful"
        )
        assert not _matches(line), (
            f"Filter regex incorrectly matched the spec's successful line:\n  {line!r}"
        )
