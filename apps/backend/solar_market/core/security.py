"""Password hashing and JWT helpers.

This module centralises every cryptographic primitive the backend uses
for authentication:

* **Password hashing** — bcrypt via ``passlib``. Chosen over PBKDF2
  because bcrypt is memory-hard-ish and widely supported by auditors.
* **JWT creation / verification** — HS256 by default. Swap
  ``JWT_ALGORITHM`` to ``RS256`` once you generate a key pair.

The module is intentionally synchronous. Chalice and bcrypt are CPU
bound, and running them in the event loop is fine for the request
volume this project targets. If you later see latency spikes, wrap
``hash_password`` / ``verify_password`` in ``asyncio.to_thread``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from solar_market.core.config import settings

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of ``plain_password``.

    Args:
        plain_password: The raw password supplied by the user.

    Returns:
        A string safe to store in ``users.password_hash``.

    Raises:
        ValueError: If ``plain_password`` is empty.
    """
    if not plain_password:
        raise ValueError("password cannot be empty")
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Return ``True`` when ``plain_password`` matches ``password_hash``."""
    if not plain_password or not password_hash:
        return False
    return _pwd_context.verify(plain_password, password_hash)


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
    expire_delta = timedelta(
        minutes=expires_minutes or settings.jwt_expires_minutes
    )
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + expire_delta).timestamp()),
    }
    return jwt.encode(
        payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> dict:
    """Verify ``token`` and return its payload.

    Raises:
        ValueError: If the token is invalid, expired, or tampered with.
    """
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise ValueError("invalid or expired token") from exc