"""Password hashing and JWT helpers.

This module centralises every cryptographic primitive the backend uses
for authentication:

* **Password hashing** — Argon2id via ``argon2-cffi``.
* **JWT creation / verification** — HS256 by default. Swap
  ``JWT_ALGORITHM`` to ``RS256`` once you generate a key pair.

The module is intentionally synchronous. Password hashing is CPU
bound, and running them in the event loop is fine for the request
volume this project targets. If you later see latency spikes, wrap
``hash_password`` / ``verify_password`` in ``asyncio.to_thread``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import settings

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
_password_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    """Return an Argon2id hash of ``plain_password``.

    Args:
        plain_password: The raw password supplied by the user.

    Returns:
        A string safe to store in ``users.password_hash``.

    Raises:
        ValueError: If ``plain_password`` is empty.
    """
    if not plain_password:
        raise ValueError("password cannot be empty")
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Return ``True`` when ``plain_password`` matches ``password_hash``."""
    if not plain_password or not password_hash:
        return False
    try:
        return _password_hasher.verify(password_hash, plain_password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def create_access_token(
    subject: str,
    *,
    expires_minutes: int | None = None,
) -> str:
    """Return a signed JWT for ``subject``.

    Args:
        subject: Typically the user id (UUID as string).
        expires_minutes: Override ``settings.jwt_expires_minutes``.

    Returns:
        A signed JWT string.
    """
    expire_delta = timedelta(minutes=expires_minutes or settings.jwt_expires_minutes)
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + expire_delta).timestamp()),
    }
    return cast(
        str,
        jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm),
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify ``token`` and return its payload.

    Raises:
        ValueError: If the token is invalid, expired, or tampered with.
    """
    try:
        return cast(
            dict[str, Any],
            jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            ),
        )
    except JWTError as exc:
        raise ValueError("invalid or expired token") from exc
