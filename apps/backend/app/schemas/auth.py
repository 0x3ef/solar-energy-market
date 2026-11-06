"""Authentication request and response schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserOut


class LoginRequest(BaseModel):
    """Credentials submitted to the login endpoint."""

    email: str
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    """JWT and opaque refresh-token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshRequest(BaseModel):
    """Refresh token rotation request."""

    refresh_token: str = Field(min_length=20)


class PasswordForgotRequest(BaseModel):
    """Request a password reset without account enumeration."""

    email: EmailStr


class PasswordResetRequest(BaseModel):
    """Consume a single-use password reset token."""

    token: str = Field(min_length=20)
    password: str = Field(min_length=8, max_length=128)


class WalletNonceRequest(BaseModel):
    """Request a wallet ownership challenge."""

    address: str = Field(pattern=r"^0x[a-fA-F0-9]{40}$")
    chain_id: int = Field(gt=0)


class WalletNonceResponse(BaseModel):
    """Wallet challenge returned to the authenticated user."""

    nonce: str
    message: str
    expires_at: str


class WalletVerifyRequest(BaseModel):
    """Verify a signed wallet challenge."""

    nonce: str = Field(min_length=20)
    signature: str = Field(pattern=r"^0x[a-fA-F0-9]{130}$")
    chain_id: int = Field(gt=0)
