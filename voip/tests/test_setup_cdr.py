"""
test_setup_cdr.py — Tests for setup_cdr.py.

Covers:
  Sub-task 10.1 — Property test for CDR completeness
    Property 4 (CDR Completeness): For any simulated call result (answered,
    no-answer, busy, failed), the CDR record written contains all required
    fields and ``billsec=0`` for non-answered calls.
    **Validates: Requirements 10.1, 10.2, 10.3**

  Sub-task 10.2 — Unit tests for CDR configuration
    - cdr.conf contains ``unanswered=yes``
    - All 15 required CDR fields are present in the backend config
    - write_cdr_conf / write_cdr_csv_conf create files with correct content

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7
"""

from __future__ import annotations

import csv
import sys
import tempfile
from dataclasses import fields as dataclass_fields
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Path setup — allow running from workspace root or voip/ directory
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from setup_cdr import (
    CDR_CONF_CONTENT,
    CDR_CSV_CONF_CONTENT,
    CDR_FIELDS,
    CDRRecord,
    write_cdr_conf,
    write_cdr_csv_conf,
    write_cdr_record,
)

# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Valid disposition values per Requirement 10.7
_DISPOSITIONS = st.sampled_from(["ANSWERED", "NO ANSWER", "BUSY", "FAILED"])

# Non-answered dispositions (billsec must be 0)
_NON_ANSWERED_DISPOSITIONS = st.sampled_from(["NO ANSWER", "BUSY", "FAILED"])

# Valid AMA flags
_AMA_FLAGS = st.sampled_from(["BILLING", "DOCUMENTATION", "OMIT"])

# Simple text strategy for string fields (printable ASCII, no commas/newlines
# to keep CSV rows well-formed)
_safe_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"),
        whitelist_characters="-_+@. ",
    ),
    min_size=0,
    max_size=40,
)

# ISO datetime string strategy (simplified)
_iso_dt = st.builds(
    lambda y, mo, d, h, mi, s: f"{y:04d}-{mo:02d}-{d:02d} {h:02d}:{mi:02d}:{s:02d}",
    y=st.integers(min_value=2020, max_value=2030),
    mo=st.integers(min_value=1, max_value=12),
    d=st.integers(min_value=1, max_value=28),
    h=st.integers(min_value=0, max_value=23),
    mi=st.integers(min_value=0, max_value=59),
    s=st.integers(min_value=0, max_value=59),
)

# Duration strategy (non-negative seconds)
_duration = st.integers(min_value=0, max_value=7200)

# Billsec for answered calls (1..duration)
_billsec_answered = st.integers(min_value=0, max_value=7200)


def _build_answered_record(
    accountcode, src, dst, dcontext, clid, channel, dstchannel,
    lastapp, start, answer, end, duration, billsec, amaflags,
) -> CDRRecord:
    return CDRRecord(
        accountcode=accountcode,
        src=src,
        dst=dst,
        dcontext=dcontext,
        clid=clid,
        channel=channel,
        dstchannel=dstchannel,
        lastapp=lastapp,
        start=start,
        answer=answer,
        end=end,
        duration=duration,
        billsec=billsec,
        disposition="ANSWERED",
        amaflags=amaflags,
    )


def _build_non_answered_record(
    accountcode, src, dst, dcontext, clid, channel, dstchannel,
    lastapp, start, end, duration, disposition, amaflags,
) -> CDRRecord:
    return CDRRecord(
        accountcode=accountcode,
        src=src,
        dst=dst,
        dcontext=dcontext,
        clid=clid,
        channel=channel,
        dstchannel=dstchannel,
        lastapp=lastapp,
        start=start,
        answer="",          # unanswered — empty answer time
        end=end,
        duration=duration,
        billsec=0,          # invariant: must be 0
        disposition=disposition,
        amaflags=amaflags,
    )


# ===========================================================================
# Sub-task 10.1 — Property test: CDR Completeness
# **Validates: Requirements 10.1, 10.2, 10.3**
# ===========================================================================


class TestCDRCompletenessProperty:
    """
    Property 4 (CDR Completeness):

    For any simulated call result (answered, no-answer, busy, failed), the
    CDR record written contains all required fields and ``billsec=0`` for
    non-answered calls.

    **Validates: Requirements 10.1, 10.2, 10.3**
    """

    @given(
        accountcode=_safe_text,
        src=_safe_text,
        dst=_safe_text,
        dcontext=_safe_text,
        clid=_safe_text,
        channel=_safe_text,
        dstchannel=_safe_text,
        lastapp=_safe_text,
        start=_iso_dt,
        answer=_iso_dt,
        end=_iso_dt,
        duration=_duration,
        billsec=_billsec_answered,
        amaflags=_AMA_FLAGS,
    )
    @settings(max_examples=100)
    def test_answered_record_has_all_fields(
        self,
        accountcode: str,
        src: str,
        dst: str,
        dcontext: str,
        clid: str,
        channel: str,
        dstchannel: str,
        lastapp: str,
        start: str,
        answer: str,
        end: str,
        duration: int,
        billsec: int,
        amaflags: str,
    ) -> None:
        """
        Property: An ANSWERED CDR record written to CSV contains all 15
        required fields.

        **Validates: Requirements 10.1, 10.2**
        """
        record = CDRRecord(
            accountcode=accountcode,
            src=src,
            dst=dst,
            dcontext=dcontext,
            clid=clid,
            channel=channel,
            dstchannel=dstchannel,
            lastapp=lastapp,
            start=start,
            answer=answer,
            end=end,
            duration=duration,
            billsec=billsec,
            disposition="ANSWERED",
            amaflags=amaflags,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = str(Path(tmpdir) / "Master.csv")
            write_cdr_record(record, csv_path)

            # Read back and verify all 15 fields are present
            with open(csv_path, newline="", encoding="utf-8") as fh:
                rows = list(csv.reader(fh))

        assert len(rows) == 1, "Expected exactly one CSV row"
        row = rows[0]
        assert len(row) == len(CDR_FIELDS), (
            f"Expected {len(CDR_FIELDS)} fields, got {len(row)}: {row}"
        )

    @given(
        accountcode=_safe_text,
        src=_safe_text,
        dst=_safe_text,
        dcontext=_safe_text,
        clid=_safe_text,
        channel=_safe_text,
        dstchannel=_safe_text,
        lastapp=_safe_text,
        start=_iso_dt,
        end=_iso_dt,
        duration=_duration,
        disposition=_NON_ANSWERED_DISPOSITIONS,
        amaflags=_AMA_FLAGS,
    )
    @settings(max_examples=100)
    def test_non_answered_record_has_billsec_zero(
        self,
        accountcode: str,
        src: str,
        dst: str,
        dcontext: str,
        clid: str,
        channel: str,
        dstchannel: str,
        lastapp: str,
        start: str,
        end: str,
        duration: int,
        disposition: str,
        amaflags: str,
    ) -> None:
        """
        Property: For any non-answered call (NO ANSWER, BUSY, FAILED), the
        CDR record written to CSV has ``billsec=0``.

        **Validates: Requirements 10.3**
        """
        record = CDRRecord(
            accountcode=accountcode,
            src=src,
            dst=dst,
            dcontext=dcontext,
            clid=clid,
            channel=channel,
            dstchannel=dstchannel,
            lastapp=lastapp,
            start=start,
            answer="",
            end=end,
            duration=duration,
            billsec=0,
            disposition=disposition,
            amaflags=amaflags,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = str(Path(tmpdir) / "Master.csv")
            write_cdr_record(record, csv_path)

            # Read back and verify billsec is 0
            with open(csv_path, newline="", encoding="utf-8") as fh:
                rows = list(csv.reader(fh))

        assert len(rows) == 1, "Expected exactly one CSV row"
        row = rows[0]
        assert len(row) == len(CDR_FIELDS), (
            f"Expected {len(CDR_FIELDS)} fields, got {len(row)}"
        )

        billsec_idx = CDR_FIELDS.index("billsec")
        assert row[billsec_idx] == "0", (
            f"billsec must be '0' for disposition={disposition!r}, "
            f"got {row[billsec_idx]!r}"
        )

    @given(
        accountcode=_safe_text,
        src=_safe_text,
        dst=_safe_text,
        dcontext=_safe_text,
        clid=_safe_text,
        channel=_safe_text,
        dstchannel=_safe_text,
        lastapp=_safe_text,
        start=_iso_dt,
        end=_iso_dt,
        duration=_duration,
        disposition=_NON_ANSWERED_DISPOSITIONS,
        amaflags=_AMA_FLAGS,
    )
    @settings(max_examples=100)
    def test_non_answered_record_has_all_fields(
        self,
        accountcode: str,
        src: str,
        dst: str,
        dcontext: str,
        clid: str,
        channel: str,
        dstchannel: str,
        lastapp: str,
        start: str,
        end: str,
        duration: int,
        disposition: str,
        amaflags: str,
    ) -> None:
        """
        Property: A non-answered CDR record written to CSV contains all 15
        required fields.

        **Validates: Requirements 10.1, 10.2**
        """
        record = CDRRecord(
            accountcode=accountcode,
            src=src,
            dst=dst,
            dcontext=dcontext,
            clid=clid,
            channel=channel,
            dstchannel=dstchannel,
            lastapp=lastapp,
            start=start,
            answer="",
            end=end,
            duration=duration,
            billsec=0,
            disposition=disposition,
            amaflags=amaflags,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = str(Path(tmpdir) / "Master.csv")
            write_cdr_record(record, csv_path)

            with open(csv_path, newline="", encoding="utf-8") as fh:
                rows = list(csv.reader(fh))

        assert len(rows) == 1
        assert len(rows[0]) == len(CDR_FIELDS), (
            f"Expected {len(CDR_FIELDS)} fields, got {len(rows[0])}"
        )

    def test_billsec_invariant_raises_for_non_answered_with_nonzero_billsec(
        self,
    ) -> None:
        """
        CDRRecord.__post_init__ must raise ValueError when billsec != 0 and
        disposition is not ANSWERED.

        **Validates: Requirements 10.3**
        """
        for disposition in ("NO ANSWER", "BUSY", "FAILED"):
            with pytest.raises(ValueError, match="billsec must be 0"):
                CDRRecord(
                    accountcode="101",
                    src="101",
                    dst="102",
                    dcontext="internal",
                    clid='"Alice" <101>',
                    channel="PJSIP/101-00000001",
                    dstchannel="PJSIP/102-00000002",
                    lastapp="Dial",
                    start="2024-01-15 10:00:00",
                    answer="",
                    end="2024-01-15 10:00:30",
                    duration=30,
                    billsec=30,  # non-zero — must raise
                    disposition=disposition,
                    amaflags="BILLING",
                )


# ===========================================================================
# Sub-task 10.2 — Unit tests for CDR configuration
# ===========================================================================


class TestCDRConfContent:
    """
    Unit tests verifying the content of cdr.conf.

    Requirements: 10.1, 10.2
    """

    def test_cdr_conf_has_enable_yes(self) -> None:
        """cdr.conf must contain ``enable=yes``."""
        assert "enable=yes" in CDR_CONF_CONTENT, (
            "CDR_CONF_CONTENT does not contain 'enable=yes'"
        )

    def test_cdr_conf_has_unanswered_yes(self) -> None:
        """
        cdr.conf must contain ``unanswered=yes`` so that CDR records are
        written for unanswered calls.

        Requirements: 10.2
        """
        assert "unanswered=yes" in CDR_CONF_CONTENT, (
            "CDR_CONF_CONTENT does not contain 'unanswered=yes'"
        )

    def test_cdr_conf_has_congestion_yes(self) -> None:
        """cdr.conf must contain ``congestion=yes``."""
        assert "congestion=yes" in CDR_CONF_CONTENT, (
            "CDR_CONF_CONTENT does not contain 'congestion=yes'"
        )

    def test_cdr_conf_has_general_section(self) -> None:
        """cdr.conf must have a [general] section header."""
        assert "[general]" in CDR_CONF_CONTENT, (
            "CDR_CONF_CONTENT does not contain '[general]' section header"
        )

    def test_write_cdr_conf_creates_file(self, tmp_path: Path) -> None:
        """write_cdr_conf should create the file at the given path."""
        target = tmp_path / "cdr.conf"
        result = write_cdr_conf(str(target))
        assert result == target
        assert target.exists()
        assert target.read_text(encoding="utf-8") == CDR_CONF_CONTENT

    def test_write_cdr_conf_creates_parent_dirs(self, tmp_path: Path) -> None:
        """write_cdr_conf should create parent directories as needed."""
        target = tmp_path / "asterisk" / "cdr.conf"
        write_cdr_conf(str(target))
        assert target.exists()


class TestCDRCsvConfContent:
    """
    Unit tests verifying the content of cdr_csv.conf.

    Requirements: 10.5
    """

    def test_cdr_csv_conf_has_csv_section(self) -> None:
        """cdr_csv.conf must have a [csv] section header."""
        assert "[csv]" in CDR_CSV_CONF_CONTENT, (
            "CDR_CSV_CONF_CONTENT does not contain '[csv]' section header"
        )

    def test_cdr_csv_conf_has_usegmtime(self) -> None:
        """cdr_csv.conf must contain ``usegmtime=yes``."""
        assert "usegmtime=yes" in CDR_CSV_CONF_CONTENT, (
            "CDR_CSV_CONF_CONTENT does not contain 'usegmtime=yes'"
        )

    def test_write_cdr_csv_conf_creates_file(self, tmp_path: Path) -> None:
        """write_cdr_csv_conf should create the file at the given path."""
        target = tmp_path / "cdr_csv.conf"
        result = write_cdr_csv_conf(str(target))
        assert result == target
        assert target.exists()
        assert target.read_text(encoding="utf-8") == CDR_CSV_CONF_CONTENT

    def test_write_cdr_csv_conf_creates_parent_dirs(self, tmp_path: Path) -> None:
        """write_cdr_csv_conf should create parent directories as needed."""
        target = tmp_path / "asterisk" / "cdr_csv.conf"
        write_cdr_csv_conf(str(target))
        assert target.exists()


class TestCDRFields:
    """
    Unit tests verifying that all 15 required CDR fields are defined.

    Requirements: 10.2, 10.5
    """

    REQUIRED_FIELDS = [
        "accountcode",
        "src",
        "dst",
        "dcontext",
        "clid",
        "channel",
        "dstchannel",
        "lastapp",
        "start",
        "answer",
        "end",
        "duration",
        "billsec",
        "disposition",
        "amaflags",
    ]

    def test_cdr_fields_list_has_15_entries(self) -> None:
        """CDR_FIELDS must contain exactly 15 entries."""
        assert len(CDR_FIELDS) == 15, (
            f"CDR_FIELDS has {len(CDR_FIELDS)} entries, expected 15"
        )

    @pytest.mark.parametrize("field", REQUIRED_FIELDS)
    def test_required_field_present_in_cdr_fields(self, field: str) -> None:
        """
        Each of the 15 required CDR fields must be present in CDR_FIELDS.

        Requirements: 10.2, 10.5
        """
        assert field in CDR_FIELDS, (
            f"Required CDR field {field!r} is missing from CDR_FIELDS"
        )

    def test_cdr_record_dataclass_has_all_required_fields(self) -> None:
        """
        CDRRecord dataclass must have all 15 required fields as dataclass
        fields.

        Requirements: 10.2
        """
        dc_field_names = {f.name for f in dataclass_fields(CDRRecord)}
        for field in self.REQUIRED_FIELDS:
            assert field in dc_field_names, (
                f"CDRRecord dataclass is missing required field {field!r}"
            )

    def test_cdr_record_as_row_returns_15_values(self) -> None:
        """CDRRecord.as_row() must return exactly 15 values."""
        record = CDRRecord(
            accountcode="101",
            src="101",
            dst="102",
            dcontext="internal",
            clid='"Alice" <101>',
            channel="PJSIP/101-00000001",
            dstchannel="PJSIP/102-00000002",
            lastapp="Dial",
            start="2024-01-15 10:00:00",
            answer="2024-01-15 10:00:05",
            end="2024-01-15 10:01:05",
            duration=65,
            billsec=60,
            disposition="ANSWERED",
            amaflags="BILLING",
        )
        row = record.as_row()
        assert len(row) == 15, f"as_row() returned {len(row)} values, expected 15"


class TestWriteCDRRecord:
    """
    Unit tests for the write_cdr_record() function.

    Requirements: 10.1, 10.5
    """

    def _make_answered_record(self) -> CDRRecord:
        return CDRRecord(
            accountcode="101",
            src="101",
            dst="102",
            dcontext="internal",
            clid='"Alice" <101>',
            channel="PJSIP/101-00000001",
            dstchannel="PJSIP/102-00000002",
            lastapp="Dial",
            start="2024-01-15 10:00:00",
            answer="2024-01-15 10:00:05",
            end="2024-01-15 10:01:05",
            duration=65,
            billsec=60,
            disposition="ANSWERED",
            amaflags="BILLING",
        )

    def _make_no_answer_record(self) -> CDRRecord:
        return CDRRecord(
            accountcode="101",
            src="101",
            dst="103",
            dcontext="internal",
            clid='"Alice" <101>',
            channel="PJSIP/101-00000003",
            dstchannel="",
            lastapp="Dial",
            start="2024-01-15 10:05:00",
            answer="",
            end="2024-01-15 10:05:30",
            duration=30,
            billsec=0,
            disposition="NO ANSWER",
            amaflags="DOCUMENTATION",
        )

    def test_write_creates_csv_file(self, tmp_path: Path) -> None:
        """write_cdr_record should create the CSV file if it does not exist."""
        path = str(tmp_path / "Master.csv")
        write_cdr_record(self._make_answered_record(), path)
        assert Path(path).exists()

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        """write_cdr_record should create parent directories as needed."""
        path = str(tmp_path / "cdr-csv" / "Master.csv")
        write_cdr_record(self._make_answered_record(), path)
        assert Path(path).exists()

    def test_write_appends_multiple_records(self, tmp_path: Path) -> None:
        """write_cdr_record should append rows, not overwrite."""
        path = str(tmp_path / "Master.csv")
        write_cdr_record(self._make_answered_record(), path)
        write_cdr_record(self._make_no_answer_record(), path)

        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))

        assert len(rows) == 2, f"Expected 2 rows, got {len(rows)}"

    def test_answered_record_billsec_written_correctly(
        self, tmp_path: Path
    ) -> None:
        """Answered record must have billsec=60 in the CSV."""
        path = str(tmp_path / "Master.csv")
        write_cdr_record(self._make_answered_record(), path)

        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))

        billsec_idx = CDR_FIELDS.index("billsec")
        assert rows[0][billsec_idx] == "60"

    def test_no_answer_record_billsec_is_zero(self, tmp_path: Path) -> None:
        """
        NO ANSWER record must have billsec=0 in the CSV.

        Requirements: 10.3
        """
        path = str(tmp_path / "Master.csv")
        write_cdr_record(self._make_no_answer_record(), path)

        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))

        billsec_idx = CDR_FIELDS.index("billsec")
        assert rows[0][billsec_idx] == "0"

    def test_disposition_written_correctly(self, tmp_path: Path) -> None:
        """Disposition field must be written verbatim to the CSV."""
        path = str(tmp_path / "Master.csv")
        write_cdr_record(self._make_no_answer_record(), path)

        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))

        disp_idx = CDR_FIELDS.index("disposition")
        assert rows[0][disp_idx] == "NO ANSWER"

    def test_all_dispositions_can_be_written(self, tmp_path: Path) -> None:
        """
        All four valid dispositions (ANSWERED, NO ANSWER, BUSY, FAILED) can
        be written to a CDR CSV file.

        Requirements: 10.7
        """
        path = str(tmp_path / "Master.csv")
        dispositions = ["ANSWERED", "NO ANSWER", "BUSY", "FAILED"]

        for i, disposition in enumerate(dispositions):
            billsec = 30 if disposition == "ANSWERED" else 0
            answer = "2024-01-15 10:00:05" if disposition == "ANSWERED" else ""
            record = CDRRecord(
                accountcode="101",
                src="101",
                dst="102",
                dcontext="internal",
                clid='"Alice" <101>',
                channel=f"PJSIP/101-{i:08d}",
                dstchannel="",
                lastapp="Dial",
                start="2024-01-15 10:00:00",
                answer=answer,
                end="2024-01-15 10:00:30",
                duration=30,
                billsec=billsec,
                disposition=disposition,
                amaflags="BILLING",
            )
            write_cdr_record(record, path)

        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))

        assert len(rows) == 4, f"Expected 4 rows, got {len(rows)}"
        disp_idx = CDR_FIELDS.index("disposition")
        written_dispositions = [row[disp_idx] for row in rows]
        assert written_dispositions == dispositions
