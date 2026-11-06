"""Logging configuration shared by every backend entry point."""

from __future__ import annotations

import logging
import sys

from app.core.config import settings

_FORMAT = "%(asctime)s %(levelname)s %(name)s - %(message)s"


def configure_logging() -> None:
    """Configure root logging exactly once.

    Safe to call from the API, ingest worker, and tests:
    repeated calls do not duplicate handlers.
    """
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())
