"""
setup_cdr.py — Configure CDR (Call Detail Record) logging for Asterisk (inside WSL2).

Writes cdr.conf and cdr_csv.conf, reloads the CDR module, and verifies the
CDR output directory is writable.

Also provides a CDRRecord dataclass and write_cdr_record() function for
writing individual CDR rows to a CSV file — used by property tests to verify
CDR completeness invariants.

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7
"""

from __future__ import annotations

import csv
import os
import subprocess
from dataclasses import dataclass, fields
from pathlib import Path

# ---------------------------------------------------------------------------
# CDR field names (in the order Asterisk writes them to Master.csv)
# ---------------------------------------------------------------------------

CDR_FIELDS: list[str] = [
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

# ---------------------------------------------------------------------------
# Configuration file contents
# ---------------------------------------------------------------------------

CDR_CONF_CONTENT: str = """\
[general]
enable=yes
unanswered=yes
congestion=yes
"""

CDR_CSV_CONF_CONTENT: str = """\
[csv]
usegmtime=yes
loguniqueid=yes
loguserfield=yes
accountcode=yes
"""

# ---------------------------------------------------------------------------
# Default file paths
# ---------------------------------------------------------------------------

DEFAULT_CDR_CONF_PATH: str = "/etc/asterisk/cdr.conf"
DEFAULT_CDR_CSV_CONF_PATH: str = "/etc/asterisk/cdr_csv.conf"
DEFAULT_CDR_CSV_DIR: str = "/var/log/asterisk/cdr-csv"
DEFAULT_CDR_CSV_FILE: str = "/var/log/asterisk/cdr-csv/Master.csv"


# ---------------------------------------------------------------------------
# CDRRecord dataclass
# ---------------------------------------------------------------------------


@dataclass
class CDRRecord:
    """
    Represents a single Asterisk Call Detail Record.

    All 15 standard CDR fields are present.  The ``billsec`` invariant
    requires that ``billsec == 0`` whenever ``disposition != "ANSWERED"``.

    Fields
    ------
    accountcode : str
        Account code associated with the call (extension or trunk identifier).
    src : str
        Source channel / originating number.
    dst : str
        Destination extension or number dialed.
    dcontext : str
        Dialplan context used for routing.
    clid : str
        Caller ID string (name and number).
    channel : str
        Asterisk channel name for the originating leg.
    dstchannel : str
        Asterisk channel name for the destination leg.
    lastapp : str
        Last dialplan application executed (e.g., "Dial", "Hangup").
    start : str
        ISO 8601 datetime string for call start time.
    answer : str
        ISO 8601 datetime string for call answer time, or empty string if
        the call was not answered.
    end : str
        ISO 8601 datetime string for call end time.
    duration : int
        Total call duration in seconds (from start to end).
    billsec : int
        Billable seconds (from answer to end).  Must be 0 if the call was
        not answered (disposition != "ANSWERED").
    disposition : str
        Call outcome: one of "ANSWERED", "NO ANSWER", "BUSY", "FAILED".
    amaflags : str
        AMA (Automatic Message Accounting) flag: "BILLING", "DOCUMENTATION",
        or "OMIT".

    Requirements: 10.1, 10.2, 10.3, 10.4, 10.7
    """

    accountcode: str
    src: str
    dst: str
    dcontext: str
    clid: str
    channel: str
    dstchannel: str
    lastapp: str
    start: str
    answer: str
    end: str
    duration: int
    billsec: int
    disposition: str
    amaflags: str

    def __post_init__(self) -> None:
        """
        Enforce the billsec invariant: if the call was not answered,
        billsec must be 0.

        Raises
        ------
        ValueError
            If ``disposition != "ANSWERED"`` and ``billsec != 0``.
        """
        if self.disposition != "ANSWERED" and self.billsec != 0:
            raise ValueError(
                f"billsec must be 0 for non-answered calls "
                f"(disposition={self.disposition!r}, billsec={self.billsec})"
            )

    def as_row(self) -> list[str]:
        """
        Return the CDR record as an ordered list of strings suitable for
        writing to a CSV file.

        The field order matches ``CDR_FIELDS``.
        """
        return [str(getattr(self, f)) for f in CDR_FIELDS]


# ---------------------------------------------------------------------------
# Public API — config file writers
# ---------------------------------------------------------------------------


def write_cdr_conf(path: str = DEFAULT_CDR_CONF_PATH) -> Path:
    """
    Write the Asterisk CDR general configuration to *path*.

    Creates parent directories as needed.

    Parameters
    ----------
    path:
        Destination file path.  Defaults to ``/etc/asterisk/cdr.conf``.

    Returns
    -------
    Path
        The resolved Path object of the written file.

    Raises
    ------
    OSError
        If the file cannot be written.

    Requirements: 10.1, 10.2
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(CDR_CONF_CONTENT, encoding="utf-8")
    return target


def write_cdr_csv_conf(path: str = DEFAULT_CDR_CSV_CONF_PATH) -> Path:
    """
    Write the Asterisk CDR CSV backend configuration to *path*.

    Creates parent directories as needed.

    Parameters
    ----------
    path:
        Destination file path.  Defaults to ``/etc/asterisk/cdr_csv.conf``.

    Returns
    -------
    Path
        The resolved Path object of the written file.

    Raises
    ------
    OSError
        If the file cannot be written.

    Requirements: 10.5
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(CDR_CSV_CONF_CONTENT, encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# Public API — CDR record writer
# ---------------------------------------------------------------------------


def write_cdr_record(record: CDRRecord, path: str) -> None:
    """
    Append a single CDR record as a CSV row to the file at *path*.

    Creates the file (and parent directories) if they do not exist.
    Appends to the file if it already exists so that multiple records
    accumulate in the same CSV file, matching Asterisk's Master.csv
    behaviour.

    Parameters
    ----------
    record:
        The :class:`CDRRecord` to write.
    path:
        Destination CSV file path.

    Raises
    ------
    OSError
        If the file cannot be written.

    Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    # Append mode — create if not present, append if it exists
    with target.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(record.as_row())


# ---------------------------------------------------------------------------
# Public API — module reload and verification
# ---------------------------------------------------------------------------


def reload_cdr_module() -> subprocess.CompletedProcess:
    """
    Reload the Asterisk CDR CSV module via the Asterisk CLI.

    Runs ``asterisk -rx "module reload cdr_csv.so"`` and returns the
    completed process result.

    Returns
    -------
    subprocess.CompletedProcess
        The result of the ``asterisk -rx`` invocation.

    Requirements: 10.5
    """
    result = subprocess.run(
        ["asterisk", "-rx", "module reload cdr_csv.so"],
        capture_output=True,
        text=True,
    )
    return result


def verify_cdr_dir_writable(
    cdr_csv_path: str = DEFAULT_CDR_CSV_FILE,
) -> bool:
    """
    Verify that the parent directory of the CDR CSV file is writable.

    Parameters
    ----------
    cdr_csv_path:
        Path to the CDR CSV file (e.g., ``/var/log/asterisk/cdr-csv/Master.csv``).
        The parent directory is checked for write access.

    Returns
    -------
    bool
        ``True`` if the parent directory exists and is writable; ``False``
        otherwise.

    Requirements: 10.5, 10.6
    """
    parent = Path(cdr_csv_path).parent
    return parent.exists() and os.access(parent, os.W_OK)


# ---------------------------------------------------------------------------
# Orchestration entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """
    Orchestrate all CDR setup steps:

    1. Write ``/etc/asterisk/cdr.conf``.
    2. Write ``/etc/asterisk/cdr_csv.conf``.
    3. Reload the CDR CSV module via the Asterisk CLI.
    4. Verify the CDR output directory is writable.
    """
    print("Step 1: Writing cdr.conf...")
    cdr_conf_path = write_cdr_conf()
    print(f"  Written to {cdr_conf_path}")

    print("Step 2: Writing cdr_csv.conf...")
    cdr_csv_conf_path = write_cdr_csv_conf()
    print(f"  Written to {cdr_csv_conf_path}")

    print("Step 3: Reloading CDR module...")
    result = reload_cdr_module()
    if result.returncode == 0:
        print("  CDR module reloaded successfully.")
    else:
        print(f"  WARNING: module reload returned code {result.returncode}")
        if result.stdout:
            print(f"  stdout: {result.stdout.strip()}")
        if result.stderr:
            print(f"  stderr: {result.stderr.strip()}")

    print("Step 4: Verifying CDR output directory is writable...")
    if verify_cdr_dir_writable():
        print(f"  {DEFAULT_CDR_CSV_DIR} is writable.")
    else:
        print(
            f"  WARNING: {DEFAULT_CDR_CSV_DIR} does not exist or is not writable. "
            "Asterisk will create it on first call."
        )

    print("\nCDR setup complete.")


if __name__ == "__main__":
    main()
