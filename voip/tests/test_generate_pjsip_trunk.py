"""
test_generate_pjsip_trunk.py — Tests for trunk config generation in generate_pjsip.py.

Covers:
  Sub-task 8.1 — Property test: Caller ID Authenticity
    Property 2 (Caller ID Authenticity): For any trunk config, the generated
    `from_user` field always equals the verified DID passed as input — no
    arbitrary value is substituted.
    **Validates: Requirements 6.1, 6.2**

  Sub-task 8.2 — Unit tests for trunk config generation
    - expiry=60 is present in the registration section
    - trunk with no ulaw/alaw codec raises ValueError
    - qualify_frequency is set

Requirements: 5.1, 5.6, 6.1, 6.2, 6.3, 12.3
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Path setup — allow running from workspace root
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from generate_pjsip import (
    _validate_e164,
    append_trunk_config,
    generate_trunk_config,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

VALID_TRUNK: dict = {
    "trunk_name": "voipms-trunk",
    "host": "sip.voip.ms",
    "username": "myusername",
    "password": "mypassword",
    "from_user": "+12025551000",
    "from_domain": "sip.voip.ms",
    "transport": "transport-tls",
    "codecs": ["ulaw", "alaw"],
}


def _make_trunk(
    trunk_name: str = "voipms-trunk",
    host: str = "sip.voip.ms",
    username: str = "myusername",
    password: str = "mypassword",
    from_user: str = "+12025551000",
    from_domain: str = "sip.voip.ms",
    transport: str = "transport-tls",
    codecs: list[str] | None = None,
) -> dict:
    return {
        "trunk_name": trunk_name,
        "host": host,
        "username": username,
        "password": password,
        "from_user": from_user,
        "from_domain": from_domain,
        "transport": transport,
        "codecs": codecs if codecs is not None else ["ulaw", "alaw"],
    }


# ===========================================================================
# Sub-task 8.1 — Property test: Caller ID Authenticity
# **Validates: Requirements 6.1, 6.2**
# ===========================================================================


class TestCallerIDAuthenticityProperty:
    """
    Property 2 (Caller ID Authenticity):

    For any trunk config, the generated `from_user` field always equals the
    verified DID passed as input — no arbitrary value is substituted.

    **Validates: Requirements 6.1, 6.2**
    """

    # Strategy: generate valid E.164 numbers (+1–15 digits)
    _e164_strategy = st.builds(
        lambda country_code, subscriber: f"+{country_code}{subscriber}",
        country_code=st.integers(min_value=1, max_value=999).map(str),
        subscriber=st.text(
            alphabet="0123456789",
            min_size=1,
            max_size=12,
        ),
    ).filter(
        # Ensure total length is between 2 and 16 chars (+ plus 1–15 digits)
        lambda n: 2 <= len(n) <= 16
    )

    @given(did=_e164_strategy)
    @settings(max_examples=200)
    def test_from_user_equals_input_did(self, did: str) -> None:
        """
        For any valid E.164 DID, the generated config's from_user line must
        equal exactly the DID passed as input.

        **Validates: Requirements 6.1, 6.2**
        """
        trunk = _make_trunk(from_user=did)
        config = generate_trunk_config(trunk)

        # The from_user line must appear in the endpoint section
        assert f"from_user={did}" in config, (
            f"Expected 'from_user={did}' in config but got:\n{config}"
        )

    @given(did=_e164_strategy)
    @settings(max_examples=200)
    def test_from_user_not_substituted(self, did: str) -> None:
        """
        The from_user value in the generated config must not be any value
        other than the DID passed as input.

        **Validates: Requirements 6.1, 6.2**
        """
        trunk = _make_trunk(from_user=did)
        config = generate_trunk_config(trunk)

        # Extract all from_user= lines
        from_user_lines = [
            line for line in config.splitlines() if line.startswith("from_user=")
        ]
        assert len(from_user_lines) >= 1, (
            f"No 'from_user=' line found in config for DID={did!r}"
        )
        for line in from_user_lines:
            actual_value = line.split("=", 1)[1]
            assert actual_value == did, (
                f"from_user was substituted: expected {did!r}, got {actual_value!r}"
            )


# ===========================================================================
# Sub-task 8.2 — Unit tests for trunk config generation
# ===========================================================================


class TestTrunkRegistrationSection:
    """Tests for the [<trunk_name>-reg] registration section."""

    def test_registration_section_header_present(self) -> None:
        """Config must contain the registration section header."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "[voipms-trunk-reg]" in config

    def test_registration_type(self) -> None:
        """Registration section must have type=registration."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "type=registration" in config

    def test_expiry_is_60(self) -> None:
        """
        Registration section must have expiry=60.

        Requirements: 5.1
        """
        config = generate_trunk_config(VALID_TRUNK)
        assert "expiry=60" in config

    def test_outbound_auth_reference(self) -> None:
        """Registration section must reference the auth section."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "outbound_auth=voipms-trunk-auth" in config

    def test_server_uri(self) -> None:
        """Registration section must have server_uri pointing to the host."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "server_uri=sip:sip.voip.ms" in config

    def test_client_uri_contains_from_user_and_host(self) -> None:
        """Registration section must have client_uri with from_user@host."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "client_uri=sip:+12025551000@sip.voip.ms" in config

    def test_expiry_60_appears_in_registration_section(self) -> None:
        """
        expiry=60 must appear in the registration section, not elsewhere.

        Requirements: 5.1
        """
        config = generate_trunk_config(VALID_TRUNK)
        lines = config.splitlines()

        in_reg_section = False
        found_expiry = False
        for line in lines:
            if line.strip() == "[voipms-trunk-reg]":
                in_reg_section = True
            elif line.startswith("[") and in_reg_section:
                # Entered a new section — stop looking
                break
            elif in_reg_section and line.strip() == "expiry=60":
                found_expiry = True

        assert found_expiry, (
            "expiry=60 was not found inside the [voipms-trunk-reg] section"
        )


class TestTrunkAuthSection:
    """Tests for the [<trunk_name>-auth] auth section."""

    def test_auth_section_header_present(self) -> None:
        """Config must contain the auth section header."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "[voipms-trunk-auth]" in config

    def test_auth_type(self) -> None:
        """Auth section must have type=auth."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "type=auth" in config

    def test_auth_type_userpass(self) -> None:
        """Auth section must have auth_type=userpass."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "auth_type=userpass" in config

    def test_username_in_auth_section(self) -> None:
        """Auth section must contain the trunk username."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "username=myusername" in config

    def test_password_in_auth_section(self) -> None:
        """Auth section must contain the trunk password."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "password=mypassword" in config


class TestTrunkAopSection:
    """Tests for the [<trunk_name>-aop] AOR section."""

    def test_aop_section_header_present(self) -> None:
        """Config must contain the AOR section header."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "[voipms-trunk-aop]" in config

    def test_aop_type(self) -> None:
        """AOR section must have type=aor."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "type=aor" in config

    def test_contact_points_to_host(self) -> None:
        """AOR section must have contact=sip:<host>."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "contact=sip:sip.voip.ms" in config


class TestTrunkEndpointSection:
    """Tests for the [<trunk_name>] endpoint section."""

    def test_endpoint_section_header_present(self) -> None:
        """Config must contain the endpoint section header."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "[voipms-trunk]\n" in config

    def test_endpoint_type(self) -> None:
        """Endpoint section must have type=endpoint."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "type=endpoint" in config

    def test_transport_set(self) -> None:
        """Endpoint section must have the configured transport."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "transport=transport-tls" in config

    def test_context_from_trunk(self) -> None:
        """Endpoint section must have context=from-trunk."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "context=from-trunk" in config

    def test_disallow_all(self) -> None:
        """Endpoint section must have disallow=all."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "disallow=all" in config

    def test_allow_ulaw_alaw(self) -> None:
        """
        Endpoint section must have allow=ulaw,alaw.

        Requirements: 12.3
        """
        config = generate_trunk_config(VALID_TRUNK)
        assert "allow=ulaw,alaw" in config

    def test_from_user_is_verified_did(self) -> None:
        """
        Endpoint section must have from_user set to the verified DID.

        Requirements: 6.1, 6.2, 6.3
        """
        config = generate_trunk_config(VALID_TRUNK)
        assert "from_user=+12025551000" in config

    def test_from_domain_set(self) -> None:
        """Endpoint section must have from_domain set."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "from_domain=sip.voip.ms" in config

    def test_qualify_frequency_30(self) -> None:
        """
        Endpoint section must have qualify_frequency=30 (qualify=yes equivalent).

        Requirements: 5.1
        """
        config = generate_trunk_config(VALID_TRUNK)
        assert "qualify_frequency=30" in config

    def test_qualify_frequency_in_endpoint_section(self) -> None:
        """
        qualify_frequency=30 must appear in the endpoint section.

        Requirements: 5.1
        """
        config = generate_trunk_config(VALID_TRUNK)
        lines = config.splitlines()

        in_endpoint_section = False
        found_qualify = False
        for line in lines:
            if line.strip() == "[voipms-trunk]":
                in_endpoint_section = True
            elif line.startswith("[") and in_endpoint_section:
                break
            elif in_endpoint_section and line.strip() == "qualify_frequency=30":
                found_qualify = True

        assert found_qualify, (
            "qualify_frequency=30 was not found inside the [voipms-trunk] endpoint section"
        )

    def test_outbound_auth_reference_in_endpoint(self) -> None:
        """Endpoint section must reference the auth section."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "outbound_auth=voipms-trunk-auth" in config

    def test_aors_reference_in_endpoint(self) -> None:
        """Endpoint section must reference the AOR section."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "aors=voipms-trunk-aop" in config


class TestTrunkCodecValidation:
    """Tests for codec validation in trunk config."""

    def test_no_ulaw_or_alaw_raises_value_error(self) -> None:
        """
        A trunk with no ulaw or alaw codec must raise ValueError.

        Requirements: 5.6, 12.3
        """
        trunk = _make_trunk(codecs=["g729", "g722"])
        with pytest.raises(ValueError, match="ulaw|alaw"):
            generate_trunk_config(trunk)

    def test_empty_codecs_raises_value_error(self) -> None:
        """An empty codecs list must raise ValueError."""
        trunk = _make_trunk(codecs=[])
        with pytest.raises(ValueError):
            generate_trunk_config(trunk)

    def test_ulaw_only_accepted(self) -> None:
        """A trunk with only ulaw must be accepted."""
        trunk = _make_trunk(codecs=["ulaw"])
        config = generate_trunk_config(trunk)
        assert "allow=ulaw,alaw" in config

    def test_alaw_only_accepted(self) -> None:
        """A trunk with only alaw must be accepted."""
        trunk = _make_trunk(codecs=["alaw"])
        config = generate_trunk_config(trunk)
        assert "allow=ulaw,alaw" in config

    def test_ulaw_alaw_with_extras_accepted(self) -> None:
        """A trunk with ulaw, alaw, and other codecs must be accepted."""
        trunk = _make_trunk(codecs=["ulaw", "alaw", "g729"])
        config = generate_trunk_config(trunk)
        assert "allow=ulaw,alaw" in config

    def test_codec_case_insensitive(self) -> None:
        """Codec names should be matched case-insensitively."""
        trunk = _make_trunk(codecs=["ULAW"])
        config = generate_trunk_config(trunk)
        assert "allow=ulaw,alaw" in config


class TestTrunkFromUserValidation:
    """Tests for from_user E.164 validation."""

    @pytest.mark.parametrize(
        "invalid_did",
        [
            "12025551000",       # missing +
            "+",                 # + with no digits
            "+1202555100a",      # contains letter
            "++12025551000",     # double +
            "+1 202 555 1000",   # spaces
            "",                  # empty
            "+1234567890123456", # 16 digits (too long)
        ],
    )
    def test_invalid_from_user_raises_value_error(self, invalid_did: str) -> None:
        """
        A trunk with an invalid from_user (non-E.164) must raise ValueError.

        Requirements: 6.1
        """
        trunk = _make_trunk(from_user=invalid_did)
        with pytest.raises(ValueError):
            generate_trunk_config(trunk)

    @pytest.mark.parametrize(
        "valid_did",
        [
            "+12025551000",
            "+441234567890",
            "+1",
            "+999999999999999",  # 15 digits (max)
        ],
    )
    def test_valid_from_user_accepted(self, valid_did: str) -> None:
        """Valid E.164 from_user values must be accepted."""
        trunk = _make_trunk(from_user=valid_did)
        config = generate_trunk_config(trunk)
        assert f"from_user={valid_did}" in config


class TestTrunkMissingKeys:
    """Tests for missing required keys in trunk dict."""

    @pytest.mark.parametrize(
        "missing_key",
        [
            "trunk_name",
            "host",
            "username",
            "password",
            "from_user",
            "from_domain",
            "transport",
            "codecs",
        ],
    )
    def test_missing_required_key_raises_key_error(self, missing_key: str) -> None:
        """A trunk dict missing any required key must raise KeyError."""
        trunk = dict(VALID_TRUNK)
        del trunk[missing_key]
        with pytest.raises(KeyError):
            generate_trunk_config(trunk)


class TestTrunkConfigStructure:
    """Tests for the overall structure of the generated trunk config."""

    def test_config_is_string(self) -> None:
        """generate_trunk_config must return a string."""
        result = generate_trunk_config(VALID_TRUNK)
        assert isinstance(result, str)

    def test_config_not_empty(self) -> None:
        """Generated trunk config must not be empty."""
        result = generate_trunk_config(VALID_TRUNK)
        assert len(result) > 0

    def test_registration_section_before_endpoint(self) -> None:
        """The registration section must appear before the endpoint section."""
        config = generate_trunk_config(VALID_TRUNK)
        reg_pos = config.index("[voipms-trunk-reg]")
        endpoint_pos = config.index("[voipms-trunk]\n")
        assert reg_pos < endpoint_pos

    def test_auth_section_before_endpoint(self) -> None:
        """The auth section must appear before the endpoint section."""
        config = generate_trunk_config(VALID_TRUNK)
        auth_pos = config.index("[voipms-trunk-auth]")
        endpoint_pos = config.index("[voipms-trunk]\n")
        assert auth_pos < endpoint_pos

    def test_aop_section_before_endpoint(self) -> None:
        """The AOR section must appear before the endpoint section."""
        config = generate_trunk_config(VALID_TRUNK)
        aop_pos = config.index("[voipms-trunk-aop]")
        endpoint_pos = config.index("[voipms-trunk]\n")
        assert aop_pos < endpoint_pos

    def test_all_four_sections_present(self) -> None:
        """All four sections must be present in the generated config."""
        config = generate_trunk_config(VALID_TRUNK)
        assert "[voipms-trunk-reg]" in config
        assert "[voipms-trunk-auth]" in config
        assert "[voipms-trunk-aop]" in config
        assert "[voipms-trunk]\n" in config

    def test_different_trunk_name(self) -> None:
        """Config sections must use the provided trunk_name."""
        trunk = _make_trunk(trunk_name="telnyx-trunk")
        config = generate_trunk_config(trunk)
        assert "[telnyx-trunk-reg]" in config
        assert "[telnyx-trunk-auth]" in config
        assert "[telnyx-trunk-aop]" in config
        assert "[telnyx-trunk]\n" in config


class TestAppendTrunkConfig:
    """Tests for append_trunk_config function."""

    def test_append_creates_file_if_not_exists(self, tmp_path: Path) -> None:
        """append_trunk_config must create the file if it does not exist."""
        target = tmp_path / "pjsip.conf"
        assert not target.exists()
        result = append_trunk_config(VALID_TRUNK, path=str(target))
        assert result.exists()

    def test_append_returns_path(self, tmp_path: Path) -> None:
        """append_trunk_config must return a Path object."""
        target = tmp_path / "pjsip.conf"
        result = append_trunk_config(VALID_TRUNK, path=str(target))
        assert isinstance(result, Path)

    def test_append_adds_trunk_config_to_file(self, tmp_path: Path) -> None:
        """append_trunk_config must write the trunk config into the file."""
        target = tmp_path / "pjsip.conf"
        append_trunk_config(VALID_TRUNK, path=str(target))
        content = target.read_text(encoding="utf-8")
        assert "[voipms-trunk-reg]" in content
        assert "expiry=60" in content
        assert "qualify_frequency=30" in content
        assert "from_user=+12025551000" in content

    def test_append_does_not_overwrite_existing_content(
        self, tmp_path: Path
    ) -> None:
        """append_trunk_config must not overwrite existing file content."""
        target = tmp_path / "pjsip.conf"
        existing_content = "; existing pjsip.conf content\n[transport-tls]\ntype=transport\n"
        target.write_text(existing_content, encoding="utf-8")

        append_trunk_config(VALID_TRUNK, path=str(target))
        content = target.read_text(encoding="utf-8")

        # Original content must still be present
        assert "; existing pjsip.conf content" in content
        assert "[transport-tls]" in content
        # Trunk config must also be present
        assert "[voipms-trunk-reg]" in content

    def test_append_multiple_trunks(self, tmp_path: Path) -> None:
        """Appending two trunks must result in both being present."""
        target = tmp_path / "pjsip.conf"
        trunk1 = _make_trunk(trunk_name="trunk-a", from_user="+12025551001")
        trunk2 = _make_trunk(trunk_name="trunk-b", from_user="+12025551002")

        append_trunk_config(trunk1, path=str(target))
        append_trunk_config(trunk2, path=str(target))

        content = target.read_text(encoding="utf-8")
        assert "[trunk-a-reg]" in content
        assert "[trunk-b-reg]" in content
        assert "from_user=+12025551001" in content
        assert "from_user=+12025551002" in content
