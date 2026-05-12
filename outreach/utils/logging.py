"""Logging configuration."""

import logging
from pathlib import Path

from outreach.utils.files import ensure_private_directory, set_private_permissions


def mask_email(email: object) -> str:
    """Return a log-safe email address that preserves enough context for debugging."""
    value = str(email)
    local, separator, domain = value.partition("@")
    if not separator:
        return "<invalid-email>"
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}***@{domain}"


def configure_logging(logs_dir: Path) -> logging.Logger:
    ensure_private_directory(logs_dir)
    logger = logging.getLogger("outreach")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    log_path = logs_dir / "outreach.log"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    set_private_permissions(log_path)
    return logger
