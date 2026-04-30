"""
config_writer.py — File-writing utility used by all config-generation tasks.

Provides write_file(path, content) which creates or overwrites a file with
the given content and sets appropriate permissions (owner read/write only
for sensitive config files, or 0o644 for world-readable ones).

Requirements: 1.1, 1.6
"""

import os
import stat
from pathlib import Path


# Default permission for Asterisk config files: owner rw, group r, other r
DEFAULT_MODE: int = 0o644

# Stricter permission for files that may contain credentials (e.g. pjsip.conf)
SECURE_MODE: int = 0o640


def write_file(
    path: str | os.PathLike,
    content: str,
    mode: int = DEFAULT_MODE,
    make_parents: bool = True,
) -> Path:
    """
    Write *content* to *path*, creating parent directories as needed.

    Parameters
    ----------
    path:
        Destination file path (absolute or relative).
    content:
        Text content to write (UTF-8).
    mode:
        Unix permission bits applied after writing (default 0o644).
    make_parents:
        If True (default), create any missing parent directories.

    Returns
    -------
    Path
        The resolved Path object of the written file.

    Raises
    ------
    OSError
        If the file cannot be written or permissions cannot be set.
    """
    target = Path(path)

    if make_parents:
        target.parent.mkdir(parents=True, exist_ok=True)

    target.write_text(content, encoding="utf-8")

    # Apply the requested permission bits
    os.chmod(target, mode)

    return target


def write_secure_file(
    path: str | os.PathLike,
    content: str,
    make_parents: bool = True,
) -> Path:
    """
    Convenience wrapper that writes a file with SECURE_MODE (0o640).

    Use this for files that contain passwords or private keys.
    """
    return write_file(path, content, mode=SECURE_MODE, make_parents=make_parents)


def read_file(path: str | os.PathLike) -> str:
    """Read and return the text content of *path* (UTF-8)."""
    return Path(path).read_text(encoding="utf-8")


def file_has_permission(path: str | os.PathLike, expected_mode: int) -> bool:
    """
    Return True if the file at *path* has exactly *expected_mode* permission bits.

    Only the lower 12 bits (permissions) are compared.
    """
    actual = stat.S_IMODE(os.stat(path).st_mode)
    return actual == expected_mode
