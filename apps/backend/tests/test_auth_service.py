"""Unit tests for authentication and wallet-linking use cases."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.security import PasswordResetToken
from app.services.auth_service import AuthenticationError, AuthService


@pytest.mark.asyncio
async def test_register_normalizes_email_and_rejects_duplicate(
    session: AsyncSession,
) -> None:
    service = AuthService(session)

    user = await service.register("USER@EXAMPLE.COM", "User", "correct horse")

    assert user.email == "user@example.com"
    with pytest.raises(ValueError, match="already registered"):
        await service.register("user@example.com", "Other", "correct horse")


@pytest.mark.asyncio
async def test_authenticate_rejects_invalid_and_suspended_users(
    session: AsyncSession,
) -> None:
    service = AuthService(session)
    user = await service.register("active@example.com", "Active", "password")

    with pytest.raises(AuthenticationError, match="invalid credentials"):
        await service.authenticate("active@example.com", "wrong")

    user.status = "suspended"
    with pytest.raises(AuthenticationError, match="invalid credentials"):
        await service.authenticate("active@example.com", "password")


@pytest.mark.asyncio
async def test_refresh_token_rotation_revokes_previous_token(
    session: AsyncSession,
) -> None:
    service = AuthService(session)
    user = await service.register("refresh@example.com", "Refresh", "password")
    raw_token = await service.issue_refresh_token(user.id)

    rotated_user, access_token, replacement = await service.rotate_refresh_token(
        raw_token
    )

    assert rotated_user.id == user.id
    assert access_token
    assert replacement != raw_token
    with pytest.raises(AuthenticationError, match="invalid refresh token"):
        await service.rotate_refresh_token(raw_token)


@pytest.mark.asyncio
async def test_password_reset_consumes_token_and_revokes_sessions(
    session: AsyncSession,
) -> None:
    service = AuthService(session)
    user = await service.register("reset@example.com", "Reset", "old-password")
    refresh = await service.issue_refresh_token(user.id)
    reset = await service.create_password_reset_token("RESET@example.com")

    assert reset is not None
    await service.reset_password(reset, "new-password")

    authenticated, _ = await service.authenticate("reset@example.com", "new-password")
    assert authenticated.id == user.id
    with pytest.raises(AuthenticationError):
        await service.rotate_refresh_token(refresh)
    with pytest.raises(AuthenticationError):
        await service.reset_password(reset, "another-password")


@pytest.mark.asyncio
async def test_wallet_signature_verification_is_single_use(
    session: AsyncSession,
) -> None:
    service = AuthService(session)
    user = await service.register("wallet@example.com", "Wallet", "password")
    account = Account.create()
    challenge, message = await service.create_wallet_nonce(
        user.id, account.address, 31337
    )
    signature = account.sign_message(encode_defunct(text=message)).signature.hex()

    wallet = await service.verify_wallet(user.id, challenge.nonce, signature, 31337)

    assert wallet.address == account.address.lower()
    with pytest.raises(AuthenticationError, match="invalid or expired"):
        await service.verify_wallet(user.id, challenge.nonce, signature, 31337)


@pytest.mark.asyncio
async def test_expired_password_reset_is_rejected(session: AsyncSession) -> None:
    service = AuthService(session)
    user = await service.register("expired@example.com", "Expired", "password")
    token = PasswordResetToken(
        user_id=user.id,
        token_hash="expired",
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    session.add(token)
    await session.flush()

    import hashlib

    raw_token = "expired-token"
    token.token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    await session.flush()
    with pytest.raises(AuthenticationError, match="expired"):
        await service.reset_password(raw_token, "new-password")
