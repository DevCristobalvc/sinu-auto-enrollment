"""SINU Auto-Enrollment — logging setup.

Logs go to stderr (human-readable) and optionally to a file.
JSON results always go to stdout — never mix logs into stdout.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

_LOGGER_NAME = "sinu_auto"
_FMT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def setup_logging(verbose: bool = False, log_file: str | None = None) -> logging.Logger:
    """Configure the package logger. Returns the logger."""
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    # Console handler → stderr (stdout is reserved for JSON output)
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(logging.Formatter(_FMT))
    logger.addHandler(console)

    # Optional file handler
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(_FMT))
        logger.addHandler(fh)

    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)
