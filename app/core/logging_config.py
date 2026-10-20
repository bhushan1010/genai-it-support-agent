"""Structured logging configuration for the application."""

from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Set up root logger with a readable format.

    Call once at application startup. Safe to call multiple times.
    """
    numeric = getattr(logging, level.upper(), logging.INFO)
    # Reconfigure stdout to UTF-8 so Unicode characters (e.g. ✓) don't
    # fail on Windows terminals with cp1252 encoding.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    # Suppress noisy third-party loggers.
    for noisy in ("httpx", "httpcore", "chromadb", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Import this instead of logging.getLogger directly."""
    return logging.getLogger(name)
