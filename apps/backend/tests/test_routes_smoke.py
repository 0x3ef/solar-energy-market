"""Smoke tests for the Chalice app wiring."""

from __future__ import annotations


def test_app_imports() -> None:
    """Importing ``app`` must not raise."""
    from app import app  # noqa: F401

    # Sanity: the Chalice app has routes registered.
    assert app.routes