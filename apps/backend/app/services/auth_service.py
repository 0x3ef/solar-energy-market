"""Authentication use cases."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from eth_account import Account
from eth_account.messages import encode_defunct
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.db.models.security import PasswordResetToken, RefreshToken, WalletNonce
from app.db.models.user import User
from app.db.models.wallet import Wallet


class AuthenticationError(ValueError):
    """Raised when authentication credentials are invalid."""


def _is_expired(value: datetime, now: datetime) -> bool:
    """Compare database timestamps consistently across PostgreSQL and SQLite."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value <= now


class AuthService:
    """Implement registration, login, and refresh-token rotation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register(self, email: str, full_name: str, password: str) -> User:
        """Create an active user with an Argon2id password hash."""
        existing = await self._session.scalar(select(User).where(User.email == email))
        if existing is not None:
            raise ValueError("email is already registered")
        user = User(
            email=email.lower(),
            full_name=full_name,
            password_hash=hash_password(password),
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def authenticate(self, email: str, password: str) -> tuple[User, str]:
        """Validate credentials and return the user plus an access token."""
        user = await self._session.scalar(
            select(User).where(User.email == email.lower())
        )
        if (
            user is None
            or user.status != "active"
            or not verify_password(password, user.password_hash or "")
        ):
            raise AuthenticationError("invalid credentials")
        return user, create_access_token(str(user.id))

    async def issue_refresh_token(self, user_id: uuid.UUID) -> str:
        """Persist a hashed opaque refresh token."""
        raw_token = secrets.token_urlsafe(48)
        token = RefreshToken(
            user_id=user_id,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        self._session.add(token)
        await self._session.flush()
        return raw_token

    async def rotate_refresh_token(self, raw_token: str) -> tuple[User, str, str]:
        """Revoke a refresh token and issue replacement credentials."""
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        token = await self._session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        now = datetime.now(UTC)
        if token is None or token.revoked_at is not None or _is_expired(
            token.expires_at, now
        ):
            raise AuthenticationError("invalid refresh token")
        user = await self._session.get(User, token.user_id)
        if user is None or user.status != "active":
            raise AuthenticationError("invalid refresh token")
        token.revoked_at = now
        access_token = create_access_token(str(user.id))
        refresh_token = await self.issue_refresh_token(user.id)
        await self._session.flush()
        return user, access_token, refresh_token

    async def revoke_refresh_token(self, raw_token: str) -> None:
        """Revoke one refresh token without disclosing whether it existed."""
        token = await self._session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()
            )
        )
        if token is not None and token.revoked_at is None:
            token.revoked_at = datetime.now(UTC)

    async def create_password_reset_token(self, email: str) -> str | None:
        """Create a short-lived reset token for an existing active account."""
        user = await self._session.scalar(
            select(User).where(User.email == email.lower(), User.status == "active")
        )
        if user is None:
            return None
        raw_token = secrets.token_urlsafe(48)
        self._session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
                expires_at=datetime.now(UTC) + timedelta(minutes=30),
            )
        )
        await self._session.flush()
        return raw_token

    async def reset_password(self, raw_token: str, password: str) -> None:
        """Consume a reset token and revoke all refresh sessions."""
        token = await self._session.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash
                == hashlib.sha256(raw_token.encode()).hexdigest()
            )
        )
        now = datetime.now(UTC)
        if token is None or token.used_at is not None or _is_expired(
            token.expires_at, now
        ):
            raise AuthenticationError("invalid or expired password reset token")
        user = await self._session.get(User, token.user_id)
        if user is None or user.status != "active":
            raise AuthenticationError("invalid password reset token")
        user.password_hash = hash_password(password)
        token.used_at = now
        refresh_tokens = await self._session.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
            )
        )
        for refresh_token in refresh_tokens:
            refresh_token.revoked_at = now

    async def create_wallet_nonce(
        self, user_id: uuid.UUID, address: str, chain_id: int
    ) -> tuple[WalletNonce, str]:
        """Create a five-minute wallet ownership challenge."""
        normalized = address.lower()
        challenge = WalletNonce(
            user_id=user_id,
            address=normalized,
            nonce=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        self._session.add(challenge)
        await self._session.flush()
        return challenge, self.wallet_message(normalized, chain_id, challenge.nonce)

    @staticmethod
    def wallet_message(address: str, chain_id: int, nonce: str) -> str:
        """Return the domain-separated message clients must sign."""
        return (
            "Solar Energy Market wallet verification\n"
            f"Address: {address}\nChain ID: {chain_id}\nNonce: {nonce}"
        )

    async def verify_wallet(
        self,
        user_id: uuid.UUID,
        nonce: str,
        signature: str,
        chain_id: int,
    ) -> Wallet:
        """Recover and persist a wallet after a valid single-use signature."""
        challenge = await self._session.scalar(
            select(WalletNonce).where(
                WalletNonce.user_id == user_id, WalletNonce.nonce == nonce
            )
        )
        now = datetime.now(UTC)
        if challenge is None or challenge.used_at is not None or _is_expired(
            challenge.expires_at, now
        ):
            raise AuthenticationError("invalid or expired wallet challenge")
        message = encode_defunct(
            text=self.wallet_message(challenge.address, chain_id, challenge.nonce)
        )
        try:
            recovered = Account.recover_message(message, signature=signature)
        except ValueError as exc:
            raise AuthenticationError("invalid wallet signature") from exc
        if recovered.lower() != challenge.address:
            raise AuthenticationError("wallet signature does not match address")
        challenge.used_at = now
        wallet = await self._session.scalar(
            select(Wallet).where(Wallet.address == challenge.address)
        )
        if wallet is None:
            wallet = Wallet(
                user_id=user_id,
                address=challenge.address,
                chain_id=chain_id,
                is_verified=True,
            )
            self._session.add(wallet)
        elif wallet.user_id != user_id:
            raise AuthenticationError("wallet is already linked to another user")
        else:
            wallet.is_verified = True
        await self._session.flush()
        return wallet
