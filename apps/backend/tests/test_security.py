"""Tests for password hashing and JWT helpers."""

from __future__ import annotations

import time

import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password() -> None:
    hashed = hash_password("super-secret")
    assert hashed != "super-secret"
    assert verify_password("super-secret", hashed)
    assert not verify_password("wrong", hashed)


def test_hash_empty_password_raises() -> None:
    with pytest.raises(ValueError):
        hash_password("")


def test_verify_with_empty_hash_returns_false() -> None:
    assert verify_password("x", "") is False


def test_create_and_decode_token() -> None:
    token = create_access_token("user-123")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert "iat" in payload
    assert "exp" in payload


def test_decode_tampered_token_raises() -> None:
    token = create_access_token("user-123")
    with pytest.raises(ValueError):
        decode_access_token(token + "tampered")


def test_decode_expired_token_raises() -> None:
    token = create_access_token("user-123", expires_minutes=-1)
    time.sleep(1)
    with pytest.raises(ValueError):
        decode_access_token(token)
