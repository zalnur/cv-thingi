"""Filesystem helpers."""

import os
import re
import stat
from pathlib import Path


def ensure_directories(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def ensure_private_directory(path: Path) -> None:
    """Create a directory and restrict permissions where the platform supports it."""
    path.mkdir(parents=True, exist_ok=True)
    set_private_permissions(path, directory=True)


def write_private_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Write sensitive text and make the file owner-readable/writable where possible."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding)
    set_private_permissions(path)


def write_private_bytes(path: Path, data: bytes) -> None:
    """Write sensitive bytes and make the file owner-readable/writable where possible."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    set_private_permissions(path)


def set_private_permissions(path: Path, *, directory: bool = False) -> None:
    """Best-effort chmod for local artifacts that may contain personal data or secrets."""
    try:
        mode = stat.S_IRWXU if directory else stat.S_IRUSR | stat.S_IWUSR
        os.chmod(path, mode)
    except OSError:
        # Windows and some mounted filesystems may not honor POSIX modes.
        pass


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-")
    return slug[:120] or "outreach-email"
