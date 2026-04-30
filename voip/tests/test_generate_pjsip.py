"""
test_generate_pjsip.py — Tests for generate_pjsip.py.

Covers:
  Sub-task 7.1 — Property test: Extension Uniqueness
    Property 8 (Extension Uniqueness): For any list of endpoint configs,
    no two generated endpoint sections share the same extension number.
    **Validates: Requirements 2.3**

  Sub-task 7.2 — Property test: Password Validation
    Property 1 (Authentication Integrity): The password validator accepts
    only passwords ≥ 12 chars with mixed alphanumeric content and rejects
    all others.
    **Validates: Requirements 2.2**

  Sub-task 7.3 — Unit tests for pjsip endpoint generation
    - transport=transport-tls, dtmf_mode=rfc4733, max_contacts=1 present
    - NAT settings rtp_symmetric=yes, force_rport=yes, direct_media=no present
    - Invalid extension numbers (100, 106) raise ValueError

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 7.1, 7.5, 12.1, 13.4
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Path setup — allow running from workspace root
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from generate_pjsip import (
    _validate_e164,
    _validate_extension,
    _validate_password,
    generate_endpoint_config,
)

# ---------------------------------------------------------------------------
# Shared test fixtures / helpers
# ---------------------------------------------------------------------------

VALID_ENDPOINT = {
    "extension": 101,
    "display_name": "Alice Smith",
    "password": "Str0ngP@ssw0rd1",
    "caller_id_num": "+12025551001",
}


def _make_endpoint(
    extension: int = 101,
    display_name: str = "Alice Smith",
    password: str = "Str0ngP@ssw0rd1",
    caller_id_num: str = "+12025551001",
) -> dict:
    return {
        "extension": extension,
        "display_name": display_name,
        "password": password,
        "caller_id_num": caller_id_num,
    }


def _unique_endpoints(extensions: list[int]) -> list[dict]:
    """Build a list of valid endpoint dicts for the given unique extension numbers."""
    return [
        _make_endpoint(
            extension=ext,
            display_name=f"User {ext}",
            password=f"Str0ngP@ss{ext:03d}",
            caller_id_num=f"+1202555{ext:04d}",
        )
        for ext in extensions
    ]


# ===========================================================================
# Sub-task 7.1 — Property test: Extension Uniqueness
# **Validates: Requirements 2.3**
# ===========================================================================


class TestExtensionUniquenessProperty:
    """
    Property 8 (Extension Uniqueness):

    For any list of endpoint configs with unique extension numbers in 101–105,
    no two generated [endpoint] sections share the same extension number.

    **Validates: Requirements 2.3**
    """

    # Strategy: draw a non-empty subset of [101, 102, 103, 104, 105]
    _valid_extensions = st.lists(
        st.integers(min_value=101, max_value=105),
        min_size=1,
        max_size=5,
        unique=True,
    )

    @given(ext_list=_valid_extensions)
    @settings(max_examples=200)
    def test_no_duplicate_endpoint_sections(self, ext_list: list[int]) -> None:
        """
        For any list of unique extensions in 101–105, the generated config
        contains each extension section header exactly once.

        **Validates: Requirements 2.3**
        """
        endpoints = _unique_endpoints(ext_list)
        config = generate_endpoint_config(endpoints)

        for ext in ext_list:
            # Count occurrences of the endpoint section header [<ext>]
            # (not auth or aor sections)
            pattern = re.compile(
                r"^\[" + str(ext) + r"\]\s*$", re.MULTILINE
            )
            matches = pattern.findall(config)
            assert len(matches) == 1, (
                f"Extension [{ext}] section appears {len(matches)} times "
                f"(expected exactly 1) for ext_list={ext_list}"
            )

    @given(ext_list=_valid_extensions)
    @settings(max_examples=200)
    def test_all_requested_extensions_present(
        self, ext_list: list[int]
    ) -> None:
        """
        Every extension in the input list must appear in the generated config.

        **Validates: Requirements 2.3**
        """
        endpoints = _unique_endpoints(ext_list)
        config = generate_endpoint_config(endpoints)

        for ext in ext_list:
            assert f"[{ext}]" in config, (
                f"Extension [{ext}] not found in config for ext_list={ext_list}"
            )

    def test_duplicate_extensions_raise_value_error(self) -> None:
        """
        Passing duplicate extension numbers must raise ValueError.

        **Validates: Requirements 2.3**
        """
        endpoints = [
            _make_endpoint(extension=101),
            _make_endpoint(extension=101),  # duplicate
        ]
        with pytest.raises(ValueError, match="[Dd]uplicate"):
            generate_endpoint_config(endpoints)


# ===========================================================================
# Sub-task 7.2 — Property test: Password Validation
# **Validates: Requirements 2.2**
# ===========================================================================


class TestPasswordValidationProperty:
    """
    Property 1 (Authentication Integrity):

    The password validator accepts only passwords ≥ 12 chars with mixed
    alphanumeric content and rejects all others.

    **Validates: Requirements 2.2**
    """

    # Strategy: generate passwords that are too short (< 12 chars)
    _short_password = st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
        ),
        min_size=0,
        max_size=11,
    )

    # Strategy: generate passwords ≥ 12 chars with at least one letter and one digit
    _valid_password = st.builds(
        lambda letters, digits, rest: letters + digits + rest,
        st.text(
            alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
            min_size=1,
            max_size=4,
        ),
        st.text(alphabet="0123456789", min_size=1, max_size=4),
        st.text(
            alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
            min_size=10,
            max_size=20,
        ),
    ).filter(lambda p: len(p) >= 12)

    # Strategy: passwords with only letters (no digits)
    _letters_only = st.text(
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        min_size=12,
        max_size=30,
    )

    # Strategy: passwords with only digits (no letters)
    _digits_only = st.text(
        alphabet="0123456789",
        min_size=12,
        max_size=30,
    )

    @given(password=_short_password)
    @settings(max_examples=200)
    def test_short_passwords_are_rejected(self, password: str) -> None:
        """
        Any password shorter than 12 characters must be rejected.

        **Validates: Requirements 2.2**
        """
        assume(len(password) < 12)
        with pytest.raises(ValueError):
            _validate_password(password)

    @given(password=_valid_password)
    @settings(max_examples=200)
    def test_valid_passwords_are_accepted(self, password: str) -> None:
        """
        Any password ≥ 12 chars with at least one letter and one digit
        must be accepted (no exception raised).

        **Validates: Requirements 2.2**
        """
        assume(len(password) >= 12)
        assume(any(c.isalpha() for c in password))
        assume(any(c.isdigit() for c in password))
        # Should not raise
        _validate_password(password)

    @given(password=_letters_only)
    @settings(max_examples=100)
    def test_letters_only_passwords_are_rejected(self, password: str) -> None:
        """
        Passwords with only letters (no digits) must be rejected even if
        they are ≥ 12 characters long.

        **Validates: Requirements 2.2**
        """
        assume(len(password) >= 12)
        assume(not any(c.isdigit() for c in password))
        with pytest.raises(ValueError):
            _validate_password(password)

    @given(password=_digits_only)
    @settings(max_examples=100)
    def test_digits_only_passwords_are_rejected(self, password: str) -> None:
        """
        Passwords with only digits (no letters) must be rejected even if
        they are ≥ 12 characters long.

        **Validates: Requirements 2.2**
        """
        assume(len(password) >= 12)
        assume(not any(c.isalpha() for c in password))
        with pytest.raises(ValueError):
            _validate_password(password)


# ===========================================================================
# Sub-task 7.3 — Unit tests for pjsip endpoint generation
# ===========================================================================


class TestTransportTLS:
    """Tests that the transport-tls section is generated correctly."""

    def test_transport_tls_section_present(self) -> None:
        """Config must contain a [transport-tls] section."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "[transport-tls]" in config

    def test_transport_type_is_transport(self) -> None:
        """transport-tls section must have type=transport."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "type=transport" in config

    def test_protocol_is_tls(self) -> None:
        """transport-tls section must have protocol=tls."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "protocol=tls" in config

    def test_bind_address(self) -> None:
        """transport-tls section must bind to 0.0.0.0:5061."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "bind=0.0.0.0:5061" in config

    def test_cert_file_path(self) -> None:
        """transport-tls section must reference the correct cert file."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "cert_file=/etc/asterisk/keys/fullchain.pem" in config

    def test_priv_key_file_path(self) -> None:
        """transport-tls section must reference the correct private key file."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "priv_key_file=/etc/asterisk/keys/privkey.pem" in config

    def test_method_is_tlsv1_2(self) -> None:
        """transport-tls section must specify method=tlsv1_2."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "method=tlsv1_2" in config


class TestEndpointSection:
    """Tests for the [endpoint] section of each extension."""

    def test_endpoint_section_header(self) -> None:
        """Config must contain [101] section header."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "[101]" in config

    def test_endpoint_type(self) -> None:
        """Endpoint section must have type=endpoint."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "type=endpoint" in config

    def test_transport_is_transport_tls(self) -> None:
        """
        Endpoint section must have transport=transport-tls.

        Requirements: 7.1
        """
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "transport=transport-tls" in config

    def test_context_is_internal(self) -> None:
        """Endpoint section must have context=internal."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "context=internal" in config

    def test_disallow_all(self) -> None:
        """Endpoint section must have disallow=all before allow."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "disallow=all" in config

    def test_allow_ulaw_alaw(self) -> None:
        """
        Endpoint section must have allow=ulaw,alaw.

        Requirements: 12.1
        """
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "allow=ulaw,alaw" in config

    def test_auth_reference(self) -> None:
        """Endpoint section must reference auth101."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "auth=auth101" in config

    def test_aors_reference(self) -> None:
        """Endpoint section must reference aor101."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "aors=aor101" in config

    def test_callerid_format(self) -> None:
        """
        Endpoint section must have callerid=<display_name> <caller_id_num>.

        Requirements: 2.4
        """
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "callerid=Alice Smith <+12025551001>" in config

    def test_media_encryption_sdes(self) -> None:
        """
        Endpoint section must have media_encryption=sdes.

        Requirements: 7.5
        """
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "media_encryption=sdes" in config

    def test_dtmf_mode_rfc4733(self) -> None:
        """
        Endpoint section must have dtmf_mode=rfc4733.

        Requirements: 2.6
        """
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "dtmf_mode=rfc4733" in config

    def test_rtp_symmetric_yes(self) -> None:
        """
        Endpoint section must have rtp_symmetric=yes.

        Requirements: 13.4
        """
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "rtp_symmetric=yes" in config

    def test_force_rport_yes(self) -> None:
        """
        Endpoint section must have force_rport=yes.

        Requirements: 13.4
        """
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "force_rport=yes" in config

    def test_direct_media_no(self) -> None:
        """
        Endpoint section must have direct_media=no.

        Requirements: 13.4
        """
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "direct_media=no" in config


class TestAuthSection:
    """Tests for the [auth<ext>] section."""

    def test_auth_section_header(self) -> None:
        """Config must contain [auth101] section header."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "[auth101]" in config

    def test_auth_type(self) -> None:
        """Auth section must have type=auth."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "type=auth" in config

    def test_auth_type_userpass(self) -> None:
        """Auth section must have auth_type=userpass."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "auth_type=userpass" in config

    def test_username_is_extension(self) -> None:
        """Auth section must have username=101."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "username=101" in config

    def test_password_in_auth_section(self) -> None:
        """Auth section must contain the endpoint password."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert f"password={VALID_ENDPOINT['password']}" in config


class TestAorSection:
    """Tests for the [aor<ext>] section."""

    def test_aor_section_header(self) -> None:
        """Config must contain [aor101] section header."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "[aor101]" in config

    def test_aor_type(self) -> None:
        """AOR section must have type=aor."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "type=aor" in config

    def test_max_contacts_is_1(self) -> None:
        """
        AOR section must have max_contacts=1.

        Requirements: 2.5
        """
        config = generate_endpoint_config([VALID_ENDPOINT])
        assert "max_contacts=1" in config


class TestMultipleEndpoints:
    """Tests for generating config with multiple endpoints."""

    def test_all_five_extensions(self) -> None:
        """Config for all 5 extensions must contain all section headers."""
        endpoints = _unique_endpoints([101, 102, 103, 104, 105])
        config = generate_endpoint_config(endpoints)

        for ext in range(101, 106):
            assert f"[{ext}]" in config, f"Missing endpoint section [{ext}]"
            assert f"[auth{ext}]" in config, f"Missing auth section [auth{ext}]"
            assert f"[aor{ext}]" in config, f"Missing aor section [aor{ext}]"

    def test_transport_section_appears_once(self) -> None:
        """The [transport-tls] section must appear exactly once."""
        endpoints = _unique_endpoints([101, 102, 103])
        config = generate_endpoint_config(endpoints)
        assert config.count("[transport-tls]") == 1

    def test_each_endpoint_has_correct_callerid(self) -> None:
        """Each endpoint must have its own callerid line."""
        endpoints = [
            _make_endpoint(101, "Alice Smith", "Str0ngP@ssw0rd1", "+12025551001"),
            _make_endpoint(102, "Bob Jones", "Str0ngP@ssw0rd2", "+12025551002"),
        ]
        config = generate_endpoint_config(endpoints)
        assert "callerid=Alice Smith <+12025551001>" in config
        assert "callerid=Bob Jones <+12025551002>" in config


class TestInvalidExtensionNumbers:
    """Tests that invalid extension numbers raise ValueError."""

    @pytest.mark.parametrize("ext", [100, 106, 0, 200, 99, 110, -1])
    def test_out_of_range_extension_raises_value_error(self, ext: int) -> None:
        """
        Extension numbers outside 101–105 must raise ValueError.

        Requirements: 2.1
        """
        ep = _make_endpoint(extension=ext)
        with pytest.raises(ValueError, match="[Oo]ut of range|range"):
            generate_endpoint_config([ep])

    def test_extension_100_raises_value_error(self) -> None:
        """Extension 100 (just below range) must raise ValueError."""
        ep = _make_endpoint(extension=100)
        with pytest.raises(ValueError):
            generate_endpoint_config([ep])

    def test_extension_106_raises_value_error(self) -> None:
        """Extension 106 (just above range) must raise ValueError."""
        ep = _make_endpoint(extension=106)
        with pytest.raises(ValueError):
            generate_endpoint_config([ep])

    def test_non_integer_extension_raises_type_error(self) -> None:
        """Non-integer extension values must raise TypeError."""
        ep = _make_endpoint(extension="abc")  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            generate_endpoint_config([ep])

    def test_empty_extensions_list_raises_value_error(self) -> None:
        """Empty extensions list must raise ValueError."""
        with pytest.raises(ValueError):
            generate_endpoint_config([])


class TestPasswordValidationUnit:
    """Unit tests for password validation edge cases."""

    def test_exactly_12_chars_mixed_accepted(self) -> None:
        """A 12-character mixed alphanumeric password must be accepted."""
        _validate_password("Abcdefghij12")  # 12 chars, has letter and digit

    def test_11_chars_rejected(self) -> None:
        """An 11-character password must be rejected."""
        with pytest.raises(ValueError):
            _validate_password("Abcdefghij1")  # 11 chars

    def test_12_letters_only_rejected(self) -> None:
        """12 letters with no digits must be rejected."""
        with pytest.raises(ValueError):
            _validate_password("Abcdefghijkl")

    def test_12_digits_only_rejected(self) -> None:
        """12 digits with no letters must be rejected."""
        with pytest.raises(ValueError):
            _validate_password("123456789012")

    def test_long_mixed_password_accepted(self) -> None:
        """A long mixed password must be accepted."""
        _validate_password("Str0ngP@ssw0rd!ExtraLong123")

    def test_empty_password_rejected(self) -> None:
        """Empty password must be rejected."""
        with pytest.raises(ValueError):
            _validate_password("")


class TestE164Validation:
    """Unit tests for E.164 caller_id_num validation."""

    @pytest.mark.parametrize(
        "valid_num",
        [
            "+12025551001",
            "+441234567890",
            "+1",
            "+999999999999999",  # 15 digits (max)
        ],
    )
    def test_valid_e164_numbers_accepted(self, valid_num: str) -> None:
        """Valid E.164 numbers must be accepted."""
        _validate_e164(valid_num)  # Should not raise

    @pytest.mark.parametrize(
        "invalid_num",
        [
            "12025551001",       # missing +
            "+",                 # + with no digits
            "+1202555100a",      # contains letter
            "++12025551001",     # double +
            "+1 202 555 1001",   # spaces
            "",                  # empty
            "+1234567890123456", # 16 digits (too long)
        ],
    )
    def test_invalid_e164_numbers_rejected(self, invalid_num: str) -> None:
        """Invalid E.164 numbers must raise ValueError."""
        with pytest.raises(ValueError):
            _validate_e164(invalid_num)


class TestExtensionValidation:
    """Unit tests for extension number validation."""

    @pytest.mark.parametrize("ext", [101, 102, 103, 104, 105])
    def test_valid_extensions_accepted(self, ext: int) -> None:
        """Extensions 101–105 must be accepted."""
        result = _validate_extension(ext)
        assert result == ext

    @pytest.mark.parametrize("ext", [100, 106, 0, 99, 200])
    def test_invalid_extensions_rejected(self, ext: int) -> None:
        """Extensions outside 101–105 must raise ValueError."""
        with pytest.raises(ValueError):
            _validate_extension(ext)

    def test_string_extension_converted(self) -> None:
        """String extension '101' must be accepted and converted to int."""
        result = _validate_extension("101")
        assert result == 101

    def test_non_numeric_string_raises_type_error(self) -> None:
        """Non-numeric string extension must raise TypeError."""
        with pytest.raises(TypeError):
            _validate_extension("abc")


class TestConfigStructure:
    """Tests for the overall structure of the generated config."""

    def test_transport_section_comes_first(self) -> None:
        """The [transport-tls] section must appear before any endpoint sections."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        transport_pos = config.index("[transport-tls]")
        endpoint_pos = config.index("[101]")
        assert transport_pos < endpoint_pos

    def test_endpoint_before_auth_before_aor(self) -> None:
        """For each extension, [ext] must come before [auth<ext>] and [aor<ext>]."""
        config = generate_endpoint_config([VALID_ENDPOINT])
        endpoint_pos = config.index("[101]")
        auth_pos = config.index("[auth101]")
        aor_pos = config.index("[aor101]")
        assert endpoint_pos < auth_pos < aor_pos

    def test_config_is_string(self) -> None:
        """generate_endpoint_config must return a string."""
        result = generate_endpoint_config([VALID_ENDPOINT])
        assert isinstance(result, str)

    def test_config_not_empty(self) -> None:
        """Generated config must not be empty."""
        result = generate_endpoint_config([VALID_ENDPOINT])
        assert len(result) > 0

    def test_missing_required_key_raises_key_error(self) -> None:
        """Endpoint dict missing a required key must raise KeyError."""
        incomplete = {"extension": 101, "display_name": "Alice"}
        with pytest.raises(KeyError):
            generate_endpoint_config([incomplete])
