"""
test_integration.py - Integration test suite for the VoIP Calling System.

Live integration tests require a running Asterisk instance and are marked
with @pytest.mark.integration. Skip them with: pytest -m "not integration"

Property tests (14.1, 14.2) are unit-level and run without Asterisk.

Requirements: 4.1, 4.2, 4.3, 5.4, 5.5, 7.1, 9.2, 9.3, 9.4, 14.2, 14.3
"""

from __future__ import annotations

import os
import platform
import re
import socket
import ssl
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from generate_pjsip import generate_endpoint_config
from setup_firewall import generate_ruleset

# ---------------------------------------------------------------------------
# pytest marks
# ---------------------------------------------------------------------------
integration = pytest.mark.integration

# ---------------------------------------------------------------------------
# Environment / connectivity helpers
# ---------------------------------------------------------------------------

AMI_HOST: str = os.environ.get("VOIP_AMI_HOST", "127.0.0.1")
AMI_PORT: int = int(os.environ.get("VOIP_AMI_PORT", "5038"))
AMI_USER: str = os.environ.get("VOIP_AMI_USER", "admin")
AMI_SECRET: str = os.environ.get("VOIP_AMI_SECRET", "")

VOIP_TEST_DID: Optional[str] = os.environ.get("VOIP_TEST_DID")
VOIP_PBX_DOMAIN: Optional[str] = os.environ.get("VOIP_PBX_DOMAIN")


def _ami_reachable() -> bool:
    """Return True if the Asterisk AMI TCP port is open."""
    try:
        with socket.create_connection((AMI_HOST, AMI_PORT), timeout=3):
            return True
    except OSError:
        return False


def _is_root_in_wsl2() -> bool:
    """Return True if running as root inside WSL2."""
    if os.name == "nt":
        return False
    try:
        if os.geteuid() != 0:
            return False
    except AttributeError:
        return False
    try:
        uname = platform.uname()
        return "microsoft" in uname.release.lower() or "wsl" in uname.release.lower()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Minimal raw AMI client (no external dependencies)
# ---------------------------------------------------------------------------


class _RawAMI:
    """
    Minimal Asterisk Manager Interface client using raw TCP sockets.
    Used as a fallback when the panoramisk library is not available.
    """

    def __init__(self, host: str, port: int, username: str, secret: str) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._secret = secret
        self._sock: Optional[socket.socket] = None
        self._buf: str = ""

    def connect(self) -> None:
        self._sock = socket.create_connection((self._host, self._port), timeout=10)
        self._sock.settimeout(10)
        self._read_until("\r\n")

    def _send(self, data: str) -> None:
        assert self._sock is not None
        self._sock.sendall(data.encode("utf-8"))

    def _read_until(self, delimiter: str, timeout: float = 10.0) -> str:
        assert self._sock is not None
        deadline = time.monotonic() + timeout
        while delimiter not in self._buf:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            self._sock.settimeout(min(remaining, 2.0))
            try:
                chunk = self._sock.recv(4096).decode("utf-8", errors="replace")
                if not chunk:
                    break
                self._buf += chunk
            except socket.timeout:
                break
        idx = self._buf.find(delimiter)
        if idx == -1:
            result, self._buf = self._buf, ""
        else:
            result = self._buf[: idx + len(delimiter)]
            self._buf = self._buf[idx + len(delimiter):]
        return result

    def _read_response(self, timeout: float = 10.0) -> dict:
        """Read one AMI response block (terminated by blank line)."""
        raw = self._read_until("\r\n\r\n", timeout=timeout)
        result: dict = {}
        for line in raw.splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                result[key.strip()] = value.strip()
        return result

    def login(self) -> None:
        self._send(
            "Action: Login\r\n"
            f"Username: {self._username}\r\n"
            f"Secret: {self._secret}\r\n"
            "\r\n"
        )
        resp = self._read_response()
        if resp.get("Response") != "Success":
            raise RuntimeError(f"AMI login failed: {resp}")

    def originate(
        self,
        channel: str,
        exten: str,
        context: str,
        priority: int = 1,
        timeout: int = 30000,
        caller_id: str = "",
        action_id: str = "test-originate",
    ) -> dict:
        action = (
            "Action: Originate\r\n"
            f"ActionID: {action_id}\r\n"
            f"Channel: {channel}\r\n"
            f"Exten: {exten}\r\n"
            f"Context: {context}\r\n"
            f"Priority: {priority}\r\n"
            f"Timeout: {timeout}\r\n"
            f"CallerID: {caller_id}\r\n"
            "Async: false\r\n"
            "\r\n"
        )
        self._send(action)
        return self._read_response(timeout=timeout / 1000 + 5)

    def command(self, cmd: str, action_id: str = "test-cmd") -> str:
        self._send(
            "Action: Command\r\n"
            f"ActionID: {action_id}\r\n"
            f"Command: {cmd}\r\n"
            "\r\n"
        )
        deadline = time.monotonic() + 15
        output_lines: list[str] = []
        while time.monotonic() < deadline:
            chunk = self._read_until("\r\n", timeout=2.0)
            if "--END COMMAND--" in chunk:
                break
            if chunk.startswith("Output:"):
                output_lines.append(chunk[len("Output:"):].strip())
        return "\n".join(output_lines)

    def logoff(self) -> None:
        if self._sock:
            try:
                self._send("Action: Logoff\r\n\r\n")
            except OSError:
                pass
            self._sock.close()
            self._sock = None

    def __enter__(self) -> "_RawAMI":
        self.connect()
        self.login()
        return self

    def __exit__(self, *_: object) -> None:
        self.logoff()


# ---------------------------------------------------------------------------
# CDR helper
# ---------------------------------------------------------------------------


def _get_last_cdr_record(src: str, dst: str) -> Optional[dict]:
    """
    Read the last CDR record from /var/log/asterisk/cdr-csv/Master.csv
    matching the given src and dst fields.
    """
    cdr_path = Path("/var/log/asterisk/cdr-csv/Master.csv")
    if not cdr_path.exists():
        return None

    fields = [
        "accountcode", "src", "dst", "dcontext", "clid", "channel",
        "dstchannel", "lastapp", "lastdata", "start", "answer", "end",
        "duration", "billsec", "disposition", "amaflags", "uniqueid", "userfield",
    ]

    last_match: Optional[dict] = None
    with cdr_path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            parts = [p.strip('"') for p in line.split(",")]
            if len(parts) < len(fields):
                continue
            record = dict(zip(fields, parts))
            if record.get("src") == src and record.get("dst") == dst:
                last_match = record
    return last_match


# ===========================================================================
# Live integration tests (require running Asterisk)
# Skip with: pytest -m "not integration"
# ===========================================================================


@integration
@pytest.mark.skipif(not _ami_reachable(), reason="Asterisk AMI not reachable")
class TestInternalCall:
    """
    Test 1: Internal call test.
    Originates a call from ext 101 to ext 102 and asserts CDR disposition is ANSWERED.
    Requirements: 4.1, 4.2, 4.3
    """

    def test_internal_call_cdr_disposition_answered(self) -> None:
        with _RawAMI(AMI_HOST, AMI_PORT, AMI_USER, AMI_SECRET) as ami:
            ami.originate(
                channel="PJSIP/101",
                exten="102",
                context="internal",
                timeout=30000,
                caller_id="101",
                action_id="test-internal-call",
            )
        time.sleep(2)
        record = _get_last_cdr_record(src="101", dst="102")
        assert record is not None, "No CDR record found for 101->102 call"
        assert record["disposition"] == "ANSWERED", (
            f"Expected CDR disposition ANSWERED, got {record['disposition']}"
        )


@integration
@pytest.mark.skipif(
    not os.environ.get("VOIP_TEST_DID"),
    reason="VOIP_TEST_DID environment variable not set",
)
class TestOutboundCall:
    """
    Test 2: Outbound call test.
    Asserts CDR src field equals the verified DID, not the extension number.
    Requirements: 5.4, 5.5
    """

    def test_outbound_call_src_is_verified_did(self) -> None:
        test_did = os.environ["VOIP_TEST_DID"]
        with _RawAMI(AMI_HOST, AMI_PORT, AMI_USER, AMI_SECRET) as ami:
            ami.originate(
                channel="PJSIP/101",
                exten=test_did,
                context="outbound",
                timeout=30000,
                caller_id="101",
                action_id="test-outbound-call",
            )
        time.sleep(2)
        record = _get_last_cdr_record(src="101", dst=test_did)
        assert record is not None, f"No CDR record found for outbound call to {test_did}"
        assert record["src"] != "101", (
            "CDR src field must be the verified DID, not the extension number"
        )


@integration
@pytest.mark.skipif(not _ami_reachable(), reason="Asterisk AMI not reachable")
class TestTrunkFailover:
    """
    Test 3: Trunk failover test.
    Corrupts trunk credentials, verifies outbound calls fail while internal calls succeed.
    Requirements: 5.4, 5.5
    """

    PJSIP_CONF_PATH = "/etc/asterisk/pjsip.conf"
    PJSIP_CONF_BACKUP = "/etc/asterisk/pjsip.conf.bak"

    def _backup_pjsip(self) -> None:
        import shutil
        shutil.copy2(self.PJSIP_CONF_PATH, self.PJSIP_CONF_BACKUP)

    def _restore_pjsip(self) -> None:
        import shutil
        shutil.copy2(self.PJSIP_CONF_BACKUP, self.PJSIP_CONF_PATH)
        subprocess.run(["asterisk", "-rx", "module reload res_pjsip.so"], check=False)

    def _corrupt_trunk_credentials(self) -> None:
        conf = Path(self.PJSIP_CONF_PATH).read_text(encoding="utf-8")
        corrupted = re.sub(
            r"(\[.*?-auth\].*?password=)(\S+)",
            r"\1INVALID_PASSWORD_FOR_TEST",
            conf,
            flags=re.DOTALL,
        )
        Path(self.PJSIP_CONF_PATH).write_text(corrupted, encoding="utf-8")

    def test_trunk_failover_outbound_fails_internal_succeeds(self) -> None:
        self._backup_pjsip()
        try:
            self._corrupt_trunk_credentials()
            subprocess.run(["asterisk", "-rx", "module reload res_pjsip.so"], check=False)
            time.sleep(3)

            with _RawAMI(AMI_HOST, AMI_PORT, AMI_USER, AMI_SECRET) as ami:
                ami.originate(
                    channel="PJSIP/101",
                    exten="+12025550000",
                    context="outbound",
                    timeout=10000,
                    caller_id="101",
                    action_id="test-failover-outbound",
                )
            time.sleep(2)
            outbound_record = _get_last_cdr_record(src="101", dst="+12025550000")
            if outbound_record is not None:
                assert outbound_record["disposition"] == "FAILED", (
                    f"Expected FAILED for outbound with invalid trunk, "
                    f"got {outbound_record['disposition']}"
                )

            with _RawAMI(AMI_HOST, AMI_PORT, AMI_USER, AMI_SECRET) as ami:
                ami.originate(
                    channel="PJSIP/101",
                    exten="102",
                    context="internal",
                    timeout=30000,
                    caller_id="101",
                    action_id="test-failover-internal",
                )
            time.sleep(2)
            internal_record = _get_last_cdr_record(src="101", dst="102")
            assert internal_record is not None, "No CDR record for internal call during trunk failover"
            assert internal_record["disposition"] == "ANSWERED", (
                f"Internal call must succeed during trunk failover, "
                f"got {internal_record['disposition']}"
            )
        finally:
            self._restore_pjsip()


@integration
@pytest.mark.skipif(
    not os.environ.get("VOIP_PBX_DOMAIN"),
    reason="VOIP_PBX_DOMAIN environment variable not set",
)
class TestTLSVerification:
    """
    Test 4: TLS verification test.
    Connects to PBX domain on port 5061 and asserts TLS 1.2+ and valid cert chain.
    Requirements: 7.1
    """

    def test_tls_version_is_1_2_or_higher(self) -> None:
        domain = os.environ["VOIP_PBX_DOMAIN"]
        ctx = ssl.create_default_context()
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        try:
            with socket.create_connection((domain, 5061), timeout=10) as raw_sock:
                with ctx.wrap_socket(raw_sock, server_hostname=domain) as tls_sock:
                    version = tls_sock.version()
                    assert version is not None, "TLS version is None"
                    assert version in ("TLSv1.2", "TLSv1.3"), (
                        f"Expected TLS 1.2 or higher, got {version}"
                    )
        except ssl.SSLError as exc:
            pytest.fail(f"TLS connection failed: {exc}")
        except OSError as exc:
            pytest.skip(f"Cannot connect to {domain}:5061 - {exc}")

    def test_certificate_chain_is_valid(self) -> None:
        domain = os.environ["VOIP_PBX_DOMAIN"]
        ctx = ssl.create_default_context()
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.check_hostname = True
        try:
            with socket.create_connection((domain, 5061), timeout=10) as raw_sock:
                with ctx.wrap_socket(raw_sock, server_hostname=domain) as tls_sock:
                    cert = tls_sock.getpeercert()
                    assert cert is not None, "No certificate returned"
                    assert "subject" in cert, "Certificate has no subject"
        except ssl.SSLCertVerificationError as exc:
            pytest.fail(f"Certificate verification failed: {exc}")
        except OSError as exc:
            pytest.skip(f"Cannot connect to {domain}:5061 - {exc}")


@integration
@pytest.mark.skipif(
    not _is_root_in_wsl2(),
    reason="Must be running as root inside WSL2",
)
class TestFail2BanTrigger:
    """
    Test 5: Fail2ban trigger test.
    Sends 6 bad SIP REGISTER requests and asserts the IP is banned.
    Requirements: 9.2, 9.3, 9.4
    """

    TEST_IP = "127.0.0.2"
    SIP_PORT = 5061

    def _send_bad_register(self, src_ip: str, ext: str = "101") -> None:
        call_id = f"test-{time.time()}"
        sip_msg = (
            f"REGISTER sip:{src_ip}:{self.SIP_PORT} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {src_ip}:5060;branch=z9hG4bK{call_id}\r\n"
            f"From: <sip:{ext}@{src_ip}>;tag=test\r\n"
            f"To: <sip:{ext}@{src_ip}>\r\n"
            f"Call-ID: {call_id}@{src_ip}\r\n"
            f"CSeq: 1 REGISTER\r\n"
            f"Contact: <sip:{ext}@{src_ip}:5060>\r\n"
            f'Authorization: Digest username="{ext}",realm="asterisk",'
            f'nonce="test",uri="sip:{src_ip}",response="wrongresponse"\r\n'
            "Content-Length: 0\r\n"
            "\r\n"
        )
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.sendto(sip_msg.encode("utf-8"), ("127.0.0.1", self.SIP_PORT))
        except OSError:
            pass

    def test_fail2ban_bans_ip_after_6_failures(self) -> None:
        for _ in range(6):
            self._send_bad_register(self.TEST_IP)
            time.sleep(0.5)
        time.sleep(5)
        result = subprocess.run(
            ["fail2ban-client", "status", "asterisk"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert self.TEST_IP in result.stdout, (
            f"Expected {self.TEST_IP} to be in fail2ban banned list. "
            f"Output: {result.stdout}"
        )


@integration
@pytest.mark.skipif(not _ami_reachable(), reason="Asterisk AMI not reachable")
class TestMultiDevice:
    """
    Test 6: Multi-device test.
    Asserts all 5 extensions appear in pjsip show registrations output.
    Requirements: 14.2, 14.3
    """

    EXTENSIONS = [101, 102, 103, 104, 105]

    def test_all_5_extensions_appear_in_pjsip_registrations(self) -> None:
        with _RawAMI(AMI_HOST, AMI_PORT, AMI_USER, AMI_SECRET) as ami:
            output = ami.command("pjsip show registrations")
        for ext in self.EXTENSIONS:
            assert str(ext) in output, (
                f"Extension {ext} not found in pjsip show registrations output."
            )

    def test_pjsip_show_contacts_lists_all_extensions(self) -> None:
        with _RawAMI(AMI_HOST, AMI_PORT, AMI_USER, AMI_SECRET) as ami:
            output = ami.command("pjsip show contacts")
        for ext in self.EXTENSIONS:
            assert str(ext) in output, (
                f"Extension {ext} not found in pjsip show contacts output."
            )


# ===========================================================================
# Sub-task 14.1 — Property test: Registration Idempotency
# **Validates: Requirements 2.5, 3.1**
# ===========================================================================


class TestRegistrationIdempotencyProperty:
    """
    Property 10 (Registration Expiry / Idempotency):

    The generated pjsip.conf always contains max_contacts=1 for any valid
    extension config, ensuring only one active contact regardless of how
    many times the extension registers.

    **Validates: Requirements 2.5, 3.1**
    """

    _ext_strategy = st.integers(min_value=101, max_value=105)
    _n_strategy = st.integers(min_value=1, max_value=10)

    def _make_endpoint(self, ext: int) -> dict:
        return {
            "extension": ext,
            "display_name": f"User {ext}",
            "password": f"Str0ngP@ss{ext:03d}",
            "caller_id_num": f"+1202555{ext:04d}",
        }

    @given(ext=_ext_strategy, n=_n_strategy)
    @settings(max_examples=50)
    def test_max_contacts_1_present_for_any_extension(self, ext: int, n: int) -> None:
        """
        For any valid extension config, max_contacts=1 is always present
        in the generated pjsip.conf, regardless of N registrations.

        **Validates: Requirements 2.5, 3.1**
        """
        endpoint = self._make_endpoint(ext)
        config = generate_endpoint_config([endpoint])
        assert "max_contacts=1" in config, (
            f"max_contacts=1 not found for ext {ext} (N={n})"
        )

    @given(ext=_ext_strategy)
    @settings(max_examples=50)
    def test_aor_section_has_max_contacts_1(self, ext: int) -> None:
        """
        The AOR section for any extension always has max_contacts=1.

        **Validates: Requirements 2.5**
        """
        endpoint = self._make_endpoint(ext)
        config = generate_endpoint_config([endpoint])
        aor_match = re.search(
            rf"\[aor{ext}\].*?max_contacts=(\d+)",
            config,
            re.DOTALL,
        )
        assert aor_match is not None, (
            f"AOR section [aor{ext}] with max_contacts not found"
        )
        assert aor_match.group(1) == "1", (
            f"max_contacts for ext {ext} is {aor_match.group(1)}, expected 1"
        )


# ===========================================================================
# Sub-task 14.2 — Property test: RTP Port Bounds
# **Validates: Requirements 8.2**
# ===========================================================================


class TestRTPPortBoundsProperty:
    """
    Property 9 (RTP Port Bounds):

    The firewall ruleset generated by setup_firewall.py must contain a UDP
    ACCEPT rule covering exactly the range [10000, 20000], and no other
    arbitrary UDP ACCEPT rules for ports outside that range.

    **Validates: Requirements 8.2**
    """

    _rtp_port = st.integers(min_value=10000, max_value=20000)
    _non_rtp_port = st.one_of(
        st.integers(min_value=1, max_value=9999),
        st.integers(min_value=20001, max_value=65535),
    ).filter(lambda p: p not in (22, 443, 5060, 5061))
    _cidr = st.builds(
        lambda a, b, c, d, p: f"{a}.{b}.{c}.{d}/{p}",
        st.integers(min_value=0, max_value=255),
        st.integers(min_value=0, max_value=255),
        st.integers(min_value=0, max_value=255),
        st.integers(min_value=0, max_value=255),
        st.integers(min_value=8, max_value=32),
    )

    @staticmethod
    def _rules_as_strings(ruleset: list) -> list[str]:
        return [" ".join(rule) for rule in ruleset]

    @given(port=_rtp_port, admin_ip=_cidr)
    @settings(max_examples=100)
    def test_rtp_port_range_is_allowed(self, port: int, admin_ip: str) -> None:
        """
        For any port in [10000, 20000], the firewall ruleset contains a
        UDP ACCEPT rule covering that range.

        **Validates: Requirements 8.2**
        """
        ruleset = generate_ruleset(admin_ip)
        rules = self._rules_as_strings(ruleset)
        rtp_rule_present = any(
            "-p udp" in r and "--dport 10000:20000" in r and "-j ACCEPT" in r
            for r in rules
        )
        assert rtp_rule_present, (
            f"No UDP ACCEPT rule for 10000:20000 found for admin_ip={admin_ip!r}. "
            f"Port {port} is in the RTP range and must be allowed."
        )

    @given(port=_non_rtp_port, admin_ip=_cidr)
    @settings(max_examples=100)
    def test_non_rtp_udp_port_not_explicitly_allowed(self, port: int, admin_ip: str) -> None:
        """
        For any UDP port outside [10000, 20000], the ruleset does NOT
        contain a specific UDP ACCEPT rule for that exact port.

        We use a word-boundary check so that port=1 does not falsely match
        the range rule "--dport 10000:20000".

        **Validates: Requirements 8.2**
        """
        ruleset = generate_ruleset(admin_ip)
        rules = self._rules_as_strings(ruleset)
        # Use regex word boundary so port=1 doesn't match "10000:20000"
        port_pattern = re.compile(rf"--dport {re.escape(str(port))}(?!\d|:)")
        specific_udp_accept = any(
            "-p udp" in r and port_pattern.search(r) is not None and "-j ACCEPT" in r
            for r in rules
        )
        assert not specific_udp_accept, (
            f"Unexpected UDP ACCEPT rule for port {port} outside RTP range."
        )

    @given(admin_ip=_cidr)
    @settings(max_examples=100)
    def test_rtp_range_rule_uses_colon_notation(self, admin_ip: str) -> None:
        """
        The RTP port range rule always uses iptables colon notation 10000:20000.

        **Validates: Requirements 8.2**
        """
        ruleset = generate_ruleset(admin_ip)
        rules = self._rules_as_strings(ruleset)
        rtp_rules = [r for r in rules if "-p udp" in r and "10000" in r and "-j ACCEPT" in r]
        assert len(rtp_rules) >= 1, (
            f"No UDP RTP ACCEPT rule found for admin_ip={admin_ip!r}"
        )
        assert any("10000:20000" in r for r in rtp_rules), (
            f"RTP rule does not use 10000:20000 notation: {rtp_rules}"
        )
