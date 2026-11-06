"""Smoke tests for FastAPI application wiring."""

from __future__ import annotations


def test_app_imports() -> None:
    """Importing ``app`` must not raise."""
    from app import app

    # Sanity: the FastAPI app has routes registered.
    assert app.routes
