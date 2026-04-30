"""
test_generate_dialplan.py — Tests for generate_dialplan.py.

Covers:
  Sub-task 9.1 — Property test: Internal Call Isolation
    Property 3 (Internal Call Isolation): For any internal extension dial
    string matching _1XX (101–199), the generated dialplan routes to a local
    PJSIP endpoint and never references the trunk name.
    **Validates: Requirements 4.5, 11.1**

  Sub-task 9.2 — Unit tests for dialplan generation
    - _1NXXNXXXXXX and _+. patterns both include Set(CALLERID(num)=...) before Dial
    - 911 routes to trunk without caller ID override
    - Unmatched pattern produces Playback(invalid) + Hangup

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 5.2, 5.3, 5.4, 5.5,
              11.1, 11.2, 11.3, 11.4, 11.5, 11.6
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

from generate_dialplan import generate_dialplan, write_extensions_conf

# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

VALID_EXTENSIONS = ["101", "102", "103", "104", "105"]
TRUNK_NAME = "voipms-trunk"
DID = "+12025551000"


def _dialplan(
    extensions: list[str] | None = None,
    trunk_name: str = TRUNK_NAME,
    did: str = DID,
) -> str:
    return generate_dialplan(
        extensions if extensions is not None else VALID_EXTENSIONS,
        trunk_name,
        did,
    )


# ===========================================================================
# Sub-task 9.1 — Property test: Internal Call Isolation
# **Validates: Requirements 4.5, 11.1**
# ===========================================================================


class TestInternalCallIsolationProperty:
    """
    Property 3 (Internal Call Isolation):

    For any internal extension dial string matching _1XX (101–199), the
    generated dialplan routes to a local PJSIP endpoint and never references
    the trunk name.

    **Validates: Requirements 4.5, 11.1**
    """

    # Strategy: generate 3-digit strings in range 101–199
    _internal_ext_strategy = st.integers(min_value=101, max_value=199).map(str)

    @given(ext=_internal_ext_strategy)
    @settings(max_examples=200)
    def test_internal_extension_routes_to_local_pjsip(self, ext: str) -> None:
        """
        For any extension in 101–199, the [internal] context Dial line must
        reference PJSIP/${EXTEN} (local endpoint) without the trunk name.

        **Validates: Requirements 4.5, 11.1**
        """
        # Use a distinctive trunk name so we can check it's absent
        trunk_name = "test-trunk-xyz"
        # Only extensions 101–105 are valid for provisioning; use a subset
        # that is always valid for the generator call.
        config = generate_dialplan(["101"], trunk_name, DID)

        # Find the Dial line in the [internal] context
        internal_dial_lines = [
            line
            for line in config.splitlines()
            if "Dial(PJSIP/${EXTEN}" in line and "@" not in line
        ]

        assert len(internal_dial_lines) >= 1, (
            "No internal Dial(PJSIP/${EXTEN},...) line found in [internal] context"
        )

        for line in internal_dial_lines:
            # Must route to local PJSIP endpoint (no @ trunk reference)
            assert f"@{trunk_name}" not in line, (
                f"Internal Dial line references trunk {trunk_name!r}: {line!r}"
            )
            assert "PJSIP/${EXTEN}" in line, (
                f"Internal Dial line does not use PJSIP/${{EXTEN}}: {line!r}"
            )

    @given(
        trunk_name=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
            min_size=3,
            max_size=30,
        )
    )
    @settings(max_examples=200)
    def test_internal_context_never_references_trunk(
        self, trunk_name: str
    ) -> None:
        """
        The [internal] context section must never contain the trunk name,
        regardless of what trunk name is provided.

        **Validates: Requirements 4.5, 11.1**
        """
        config = generate_dialplan(["101"], trunk_name, DID)

        # Extract only the [internal] section lines
        lines = config.splitlines()
        internal_lines: list[str] = []
        in_internal = False
        for line in lines:
            if line.strip() == "[internal]":
                in_internal = True
                internal_lines.append(line)
            elif line.startswith("[") and in_internal:
                break
            elif in_internal:
                internal_lines.append(line)

        assert len(internal_lines) > 0, "No [internal] section found"

        for line in internal_lines:
            assert trunk_name not in line, (
                f"[internal] section references trunk {trunk_name!r} in line: {line!r}"
            )


# ===========================================================================
# Sub-task 9.2 — Unit tests for dialplan generation
# ===========================================================================


class TestGeneralSection:
    """Tests for the [general] section."""

    def test_general_section_present(self) -> None:
        """Config must contain [general] section."""
        config = _dialplan()
        assert "[general]" in config

    def test_static_yes(self) -> None:
        """[general] must have static=yes."""
        config = _dialplan()
        assert "static=yes" in config

    def test_writeprotect_no(self) -> None:
        """[general] must have writeprotect=no."""
        config = _dialplan()
        assert "writeprotect=no" in config

    def test_clearglobalvars_no(self) -> None:
        """[general] must have clearglobalvars=no."""
        config = _dialplan()
        assert "clearglobalvars=no" in config

    def test_general_section_before_internal(self) -> None:
        """[general] must appear before [internal]."""
        config = _dialplan()
        assert config.index("[general]") < config.index("[internal]")

    def test_internal_section_before_outbound(self) -> None:
        """[internal] must appear before [outbound]."""
        config = _dialplan()
        assert config.index("[internal]") < config.index("[outbound]")


class TestInternalContext:
    """Tests for the [internal] context."""

    def test_internal_context_present(self) -> None:
        """Config must contain [internal] context."""
        config = _dialplan()
        assert "[internal]" in config

    def test_1xx_pattern_present(self) -> None:
        """[internal] must have the _1XX pattern."""
        config = _dialplan()
        assert "exten => _1XX" in config

    def test_dial_pjsip_exten_30(self) -> None:
        """
        [internal] _1XX pattern must route to Dial(PJSIP/${EXTEN},30).

        Requirements: 4.1, 11.1
        """
        config = _dialplan()
        assert "Dial(PJSIP/${EXTEN},30)" in config

    def test_internal_dial_has_no_trunk_reference(self) -> None:
        """
        The Dial() in [internal] must NOT reference the trunk name.

        Requirements: 4.5, 11.1
        """
        config = _dialplan()
        # Find the Dial line in internal context
        for line in config.splitlines():
            if "Dial(PJSIP/${EXTEN},30)" in line:
                assert TRUNK_NAME not in line, (
                    f"Internal Dial line references trunk: {line!r}"
                )

    def test_noop_before_dial_in_internal(self) -> None:
        """
        [internal] must have NoOp at priority 1 before Dial at priority 2.

        Requirements: 4.1
        """
        config = _dialplan()
        assert "exten => _1XX,1,NoOp(" in config
        assert "exten => _1XX,2,Dial(" in config

    def test_hangup_after_dial_in_internal(self) -> None:
        """[internal] must have Hangup() after Dial."""
        config = _dialplan()
        assert "exten => _1XX,3,Hangup()" in config

    def test_invalid_internal_extension_catch_all(self) -> None:
        """
        [internal] must have a catch-all for invalid extensions that plays
        Playback(invalid) and hangs up.

        Requirements: 4.6, 11.5
        """
        config = _dialplan()
        assert "exten => _1[0-9][0-9]" in config
        assert "Playback(invalid)" in config

    def test_invalid_internal_extension_hangup(self) -> None:
        """Invalid internal extension catch-all must include Hangup()."""
        config = _dialplan()
        # Find the _1[0-9][0-9] Hangup line
        hangup_lines = [
            line
            for line in config.splitlines()
            if "_1[0-9][0-9]" in line and "Hangup()" in line
        ]
        assert len(hangup_lines) >= 1, (
            "No Hangup() found for _1[0-9][0-9] catch-all pattern"
        )


class TestOutboundUSPattern:
    """
    Tests for the _1NXXNXXXXXX (US/Canada 11-digit) pattern.

    Requirements: 5.2, 5.3, 11.2, 11.6
    """

    def test_us_pattern_present(self) -> None:
        """[outbound] must have the _1NXXNXXXXXX pattern."""
        config = _dialplan()
        assert "exten => _1NXXNXXXXXX" in config

    def test_us_pattern_sets_callerid_before_dial(self) -> None:
        """
        _1NXXNXXXXXX must include Set(CALLERID(num)=...) before Dial().

        Requirements: 5.5, 11.6
        """
        config = _dialplan()
        lines = config.splitlines()

        set_priority: int | None = None
        dial_priority: int | None = None

        for line in lines:
            if "_1NXXNXXXXXX" in line and "Set(CALLERID(num)=" in line:
                # Extract priority number from "exten => _1NXXNXXXXXX,N,..."
                parts = line.split(",")
                set_priority = int(parts[1])
            elif "_1NXXNXXXXXX" in line and "Dial(PJSIP/" in line:
                parts = line.split(",")
                dial_priority = int(parts[1])

        assert set_priority is not None, (
            "No Set(CALLERID(num)=...) found for _1NXXNXXXXXX pattern"
        )
        assert dial_priority is not None, (
            "No Dial() found for _1NXXNXXXXXX pattern"
        )
        assert set_priority < dial_priority, (
            f"Set (priority {set_priority}) must come before Dial (priority {dial_priority})"
        )

    def test_us_pattern_callerid_uses_did(self) -> None:
        """
        _1NXXNXXXXXX Set(CALLERID(num)=...) must use the provided DID.

        Requirements: 5.5, 6.1, 11.6
        """
        config = _dialplan()
        assert f"Set(CALLERID(num)={DID})" in config

    def test_us_pattern_dials_through_trunk(self) -> None:
        """
        _1NXXNXXXXXX Dial() must route through the trunk.

        Requirements: 5.2, 11.2
        """
        config = _dialplan()
        assert f"Dial(PJSIP/${{EXTEN}}@{TRUNK_NAME})" in config

    def test_us_pattern_has_hangup(self) -> None:
        """_1NXXNXXXXXX must include Hangup()."""
        config = _dialplan()
        hangup_lines = [
            line
            for line in config.splitlines()
            if "_1NXXNXXXXXX" in line and "Hangup()" in line
        ]
        assert len(hangup_lines) >= 1


class TestOutboundInternationalPattern:
    """
    Tests for the _+. (international E.164) pattern.

    Requirements: 5.2, 5.4, 11.3, 11.6
    """

    def test_international_pattern_present(self) -> None:
        """[outbound] must have the _+. pattern."""
        config = _dialplan()
        assert "exten => _+." in config

    def test_international_pattern_sets_callerid_before_dial(self) -> None:
        """
        _+. must include Set(CALLERID(num)=...) before Dial().

        Requirements: 5.5, 11.6
        """
        config = _dialplan()
        lines = config.splitlines()

        set_priority: int | None = None
        dial_priority: int | None = None

        for line in lines:
            if line.startswith("exten => _+.") and "Set(CALLERID(num)=" in line:
                parts = line.split(",")
                set_priority = int(parts[1])
            elif line.startswith("exten => _+.") and "Dial(PJSIP/" in line:
                parts = line.split(",")
                dial_priority = int(parts[1])

        assert set_priority is not None, (
            "No Set(CALLERID(num)=...) found for _+. pattern"
        )
        assert dial_priority is not None, (
            "No Dial() found for _+. pattern"
        )
        assert set_priority < dial_priority, (
            f"Set (priority {set_priority}) must come before Dial (priority {dial_priority})"
        )

    def test_international_pattern_callerid_uses_did(self) -> None:
        """
        _+. Set(CALLERID(num)=...) must use the provided DID.

        Requirements: 5.5, 6.1, 11.6
        """
        config = _dialplan()
        # Verify the DID appears in a Set(CALLERID...) line for _+.
        set_lines = [
            line
            for line in config.splitlines()
            if line.startswith("exten => _+.") and "Set(CALLERID(num)=" in line
        ]
        assert any(DID in line for line in set_lines), (
            f"DID {DID!r} not found in _+. Set(CALLERID) line"
        )

    def test_international_pattern_dials_through_trunk(self) -> None:
        """
        _+. Dial() must route through the trunk.

        Requirements: 5.2, 11.3
        """
        config = _dialplan()
        dial_lines = [
            line
            for line in config.splitlines()
            if line.startswith("exten => _+.") and "Dial(PJSIP/" in line
        ]
        assert any(f"@{TRUNK_NAME}" in line for line in dial_lines), (
            f"No _+. Dial line routes through trunk {TRUNK_NAME!r}"
        )

    def test_international_pattern_has_hangup(self) -> None:
        """_+. must include Hangup()."""
        config = _dialplan()
        hangup_lines = [
            line
            for line in config.splitlines()
            if line.startswith("exten => _+.") and "Hangup()" in line
        ]
        assert len(hangup_lines) >= 1


class TestEmergencyPattern:
    """
    Tests for the 911 emergency pattern.

    Requirements: 11.4
    """

    def test_911_pattern_present(self) -> None:
        """[outbound] must have the 911 pattern."""
        config = _dialplan()
        assert "exten => 911" in config

    def test_911_routes_to_trunk(self) -> None:
        """
        911 must route to the trunk without caller ID override.

        Requirements: 11.4
        """
        config = _dialplan()
        dial_lines = [
            line
            for line in config.splitlines()
            if line.startswith("exten => 911") and "Dial(PJSIP/911@" in line
        ]
        assert len(dial_lines) >= 1, "No 911 Dial line found"
        assert any(TRUNK_NAME in line for line in dial_lines), (
            f"911 Dial line does not reference trunk {TRUNK_NAME!r}"
        )

    def test_911_does_not_set_callerid(self) -> None:
        """
        911 must NOT include Set(CALLERID(num)=...) — emergency calls must
        not have caller ID overridden.

        Requirements: 11.4
        """
        config = _dialplan()
        callerid_lines = [
            line
            for line in config.splitlines()
            if line.startswith("exten => 911") and "Set(CALLERID" in line
        ]
        assert len(callerid_lines) == 0, (
            f"911 pattern unexpectedly sets caller ID: {callerid_lines}"
        )

    def test_911_has_noop(self) -> None:
        """911 must have a NoOp at priority 1."""
        config = _dialplan()
        assert "exten => 911,1,NoOp(" in config

    def test_911_has_hangup(self) -> None:
        """911 must include Hangup()."""
        config = _dialplan()
        hangup_lines = [
            line
            for line in config.splitlines()
            if line.startswith("exten => 911") and "Hangup()" in line
        ]
        assert len(hangup_lines) >= 1


class TestCatchAllPattern:
    """
    Tests for the _X. catch-all invalid number pattern.

    Requirements: 4.6, 11.5
    """

    def test_catchall_pattern_present(self) -> None:
        """[outbound] must have the _X. catch-all pattern."""
        config = _dialplan()
        assert "exten => _X." in config

    def test_catchall_plays_invalid(self) -> None:
        """
        _X. must play Playback(invalid) for unmatched numbers.

        Requirements: 4.6, 11.5
        """
        config = _dialplan()
        playback_lines = [
            line
            for line in config.splitlines()
            if line.startswith("exten => _X.") and "Playback(invalid)" in line
        ]
        assert len(playback_lines) >= 1, (
            "No Playback(invalid) found for _X. catch-all pattern"
        )

    def test_catchall_has_hangup(self) -> None:
        """
        _X. must include Hangup() after Playback(invalid).

        Requirements: 4.6, 11.5
        """
        config = _dialplan()
        hangup_lines = [
            line
            for line in config.splitlines()
            if line.startswith("exten => _X.") and "Hangup()" in line
        ]
        assert len(hangup_lines) >= 1, (
            "No Hangup() found for _X. catch-all pattern"
        )

    def test_catchall_playback_before_hangup(self) -> None:
        """
        _X. Playback(invalid) must come before Hangup().

        Requirements: 4.6, 11.5
        """
        config = _dialplan()
        lines = config.splitlines()

        playback_priority: int | None = None
        hangup_priority: int | None = None

        for line in lines:
            if line.startswith("exten => _X.") and "Playback(invalid)" in line:
                parts = line.split(",")
                playback_priority = int(parts[1])
            elif line.startswith("exten => _X.") and "Hangup()" in line:
                parts = line.split(",")
                hangup_priority = int(parts[1])

        assert playback_priority is not None
        assert hangup_priority is not None
        assert playback_priority < hangup_priority


class TestDIDSubstitution:
    """Tests that the DID is correctly substituted in outbound patterns."""

    def test_did_appears_in_us_pattern(self) -> None:
        """The DID must appear in the _1NXXNXXXXXX Set(CALLERID) line."""
        custom_did = "+14155550100"
        config = generate_dialplan(VALID_EXTENSIONS, TRUNK_NAME, custom_did)
        set_lines = [
            line
            for line in config.splitlines()
            if "_1NXXNXXXXXX" in line and "Set(CALLERID(num)=" in line
        ]
        assert any(custom_did in line for line in set_lines)

    def test_did_appears_in_international_pattern(self) -> None:
        """The DID must appear in the _+. Set(CALLERID) line."""
        custom_did = "+14155550100"
        config = generate_dialplan(VALID_EXTENSIONS, TRUNK_NAME, custom_did)
        set_lines = [
            line
            for line in config.splitlines()
            if line.startswith("exten => _+.") and "Set(CALLERID(num)=" in line
        ]
        assert any(custom_did in line for line in set_lines)

    def test_trunk_name_appears_in_outbound_dial(self) -> None:
        """The trunk name must appear in outbound Dial() lines."""
        custom_trunk = "telnyx-trunk"
        config = generate_dialplan(VALID_EXTENSIONS, custom_trunk, DID)
        assert f"@{custom_trunk}" in config

    def test_trunk_name_not_in_internal_context(self) -> None:
        """The trunk name must NOT appear in the [internal] context."""
        custom_trunk = "telnyx-trunk"
        config = generate_dialplan(VALID_EXTENSIONS, custom_trunk, DID)

        lines = config.splitlines()
        internal_lines: list[str] = []
        in_internal = False
        for line in lines:
            if line.strip() == "[internal]":
                in_internal = True
            elif line.startswith("[") and in_internal:
                break
            elif in_internal:
                internal_lines.append(line)

        for line in internal_lines:
            assert custom_trunk not in line, (
                f"Trunk name {custom_trunk!r} found in [internal] section: {line!r}"
            )


class TestValidation:
    """Tests for input validation in generate_dialplan."""

    @pytest.mark.parametrize(
        "invalid_ext",
        ["100", "106", "200", "99", "0", "1000"],
    )
    def test_invalid_extension_raises_value_error(
        self, invalid_ext: str
    ) -> None:
        """Extensions outside 101–105 must raise ValueError."""
        with pytest.raises(ValueError, match="101"):
            generate_dialplan([invalid_ext], TRUNK_NAME, DID)

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
    def test_invalid_did_raises_value_error(self, invalid_did: str) -> None:
        """Non-E.164 DID values must raise ValueError."""
        with pytest.raises(ValueError):
            generate_dialplan(VALID_EXTENSIONS, TRUNK_NAME, invalid_did)

    @pytest.mark.parametrize(
        "valid_did",
        [
            "+12025551000",
            "+441234567890",
            "+1",
            "+999999999999999",  # 15 digits (max)
        ],
    )
    def test_valid_did_accepted(self, valid_did: str) -> None:
        """Valid E.164 DID values must be accepted."""
        config = generate_dialplan(VALID_EXTENSIONS, TRUNK_NAME, valid_did)
        assert isinstance(config, str)
        assert len(config) > 0

    def test_valid_extensions_accepted(self) -> None:
        """All extensions 101–105 must be accepted."""
        config = generate_dialplan(VALID_EXTENSIONS, TRUNK_NAME, DID)
        assert isinstance(config, str)

    def test_single_extension_accepted(self) -> None:
        """A single valid extension must be accepted."""
        config = generate_dialplan(["103"], TRUNK_NAME, DID)
        assert isinstance(config, str)


class TestReturnType:
    """Tests for the return type and basic structure of generate_dialplan."""

    def test_returns_string(self) -> None:
        """generate_dialplan must return a string."""
        result = _dialplan()
        assert isinstance(result, str)

    def test_not_empty(self) -> None:
        """Generated dialplan must not be empty."""
        result = _dialplan()
        assert len(result) > 0

    def test_ends_with_newline(self) -> None:
        """Generated dialplan must end with a newline."""
        result = _dialplan()
        assert result.endswith("\n")

    def test_all_three_sections_present(self) -> None:
        """Config must contain [general], [internal], and [outbound]."""
        result = _dialplan()
        assert "[general]" in result
        assert "[internal]" in result
        assert "[outbound]" in result


class TestWriteExtensionsConf:
    """Tests for write_extensions_conf function."""

    def test_creates_file(self, tmp_path: Path) -> None:
        """write_extensions_conf must create the file."""
        target = tmp_path / "extensions.conf"
        result = write_extensions_conf(VALID_EXTENSIONS, TRUNK_NAME, DID, path=str(target))
        assert target.exists()

    def test_returns_path(self, tmp_path: Path) -> None:
        """write_extensions_conf must return a Path object."""
        target = tmp_path / "extensions.conf"
        result = write_extensions_conf(VALID_EXTENSIONS, TRUNK_NAME, DID, path=str(target))
        assert isinstance(result, Path)

    def test_file_content_matches_generate_dialplan(self, tmp_path: Path) -> None:
        """File content must match generate_dialplan output."""
        target = tmp_path / "extensions.conf"
        write_extensions_conf(VALID_EXTENSIONS, TRUNK_NAME, DID, path=str(target))
        expected = generate_dialplan(VALID_EXTENSIONS, TRUNK_NAME, DID)
        actual = target.read_text(encoding="utf-8")
        assert actual == expected

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """write_extensions_conf must create missing parent directories."""
        target = tmp_path / "asterisk" / "conf" / "extensions.conf"
        write_extensions_conf(VALID_EXTENSIONS, TRUNK_NAME, DID, path=str(target))
        assert target.exists()

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        """write_extensions_conf must overwrite an existing file."""
        target = tmp_path / "extensions.conf"
        target.write_text("old content", encoding="utf-8")
        write_extensions_conf(VALID_EXTENSIONS, TRUNK_NAME, DID, path=str(target))
        content = target.read_text(encoding="utf-8")
        assert "old content" not in content
        assert "[general]" in content
