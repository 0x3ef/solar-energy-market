"""Logging configuration shared by every backend entry point."""

from __future__ import annotations

import logging
import sys

from solar_market.core.config import settings

_FORMAT = "%(asctime)s %(levelname)s %(name)s - %(message)s"


def configure_logging() -> None:
    """Configure root logging exactly once.

    Safe to call from Chalice, from the ingest worker, and from tests:
    repeated calls do not duplicate handlers.
    """
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())