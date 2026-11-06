"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.schemas.auth import (
    LoginRequest,
    PasswordForgotRequest,
    PasswordResetRequest,
    RefreshRequest,
    TokenResponse,
    WalletNonceRequest,
    WalletNonceResponse,
    WalletVerifyRequest,
)
from app.schemas.user import UserCreate, UserOut, WalletOut
from app.services.auth_service import AuthenticationError, AuthService

router = APIRouter()


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    payload: UserCreate, session: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Register a user and return initial access credentials."""
    service = AuthService(session)
    try:
        user = await service.register(
            payload.email, payload.full_name, payload.password
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=await service.issue_refresh_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Authenticate a user."""
    service = AuthService(session)
    try:
        user, access_token = await service.authenticate(payload.email, payload.password)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return TokenResponse(
        access_token=access_token,
        refresh_token=await service.issue_refresh_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest, session: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Rotate a refresh token."""
    try:
        user, access_token, refresh_token = await AuthService(
            session
        ).rotate_refresh_token(payload.refresh_token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserOut.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshRequest, session: AsyncSession = Depends(get_db)
) -> None:
    """Revoke a refresh token."""
    await AuthService(session).revoke_refresh_token(payload.refresh_token)


@router.get("/me", response_model=UserOut)
async def me(user=Depends(get_current_user)) -> UserOut:
    """Return the authenticated user."""
    return UserOut.model_validate(user)


@router.post("/password/forgot")
async def forgot_password(
    payload: PasswordForgotRequest, session: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """Create a reset token without revealing whether the email exists."""
    token = await AuthService(session).create_password_reset_token(payload.email)
    response = {"detail": "If the account exists, reset instructions were created."}
    if settings.environment != "production" and token is not None:
        response["reset_token"] = token
    return response


@router.post("/password/reset")
async def reset_password(
    payload: PasswordResetRequest, session: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """Reset a password with a single-use token."""
    try:
        await AuthService(session).reset_password(payload.token, payload.password)
    except AuthenticationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"detail": "password reset"}


@router.post("/wallet/nonce", response_model=WalletNonceResponse)
async def wallet_nonce(
    payload: WalletNonceRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WalletNonceResponse:
    """Issue a short-lived challenge for wallet ownership."""
    challenge, message = await AuthService(session).create_wallet_nonce(
        user.id, payload.address, payload.chain_id
    )
    return WalletNonceResponse(
        nonce=challenge.nonce,
        message=message,
        expires_at=challenge.expires_at.isoformat(),
    )


@router.post("/wallet/verify", response_model=WalletOut)
async def verify_wallet(
    payload: WalletVerifyRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WalletOut:
    """Verify and link a wallet using the signed challenge."""
    try:
        wallet = await AuthService(session).verify_wallet(
            user.id, payload.nonce, payload.signature, payload.chain_id
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return WalletOut.model_validate(wallet)
