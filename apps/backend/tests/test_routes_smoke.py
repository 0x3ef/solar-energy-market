"""Smoke tests for FastAPI application wiring."""

from __future__ import annotations


def test_app_imports() -> None:
    """Importing ``app`` must not raise."""
    from app import app

    # Sanity: the FastAPI app has routes registered.
    assert app.routes


def test_registration_has_one_canonical_route() -> None:
    """Registration is owned exclusively by the authentication router."""
    from app import app

    paths = app.openapi()["paths"]

    assert "post" in paths["/api/v1/auth/register"]
    assert "/api/v1/users" not in paths or "post" not in paths["/api/v1/users"]
