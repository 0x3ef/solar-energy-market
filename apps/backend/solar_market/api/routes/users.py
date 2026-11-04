"""User and wallet endpoints."""

from __future__ import annotations

import uuid

from chalice import Blueprint

from solar_market.api.deps import db_session
from solar_market.api.middleware.error_handler import handle_errors
from solar_market.core.security import hash_password, create_access_token
from solar_market.repositories.user_repository import UserRepository
from solar_market.schemas.user import (
    UserCreate,
    UserOut,
    WalletCreate,
    WalletOut,
)

users_bp = Blueprint(__name__)


@users_bp.route("/users", methods=["POST"])
@handle_errors
async def create_user() -> dict:
    """Register a new user and return the user plus an access token."""
    body = UserCreate.model_validate(users_bp.current_request.json_body)
    async with db_session() as session:
        repo = UserRepository(session)
        user = await repo.create(
            email=body.email,
            full_name=body.full_name,
            password_hash=hash_password(body.password),
        )
        await session.commit()
        return {
            "user": UserOut.model_validate(user).model_dump(mode="json"),
            "access_token": create_access_token(str(user.id)),
            "token_type": "bearer",
        }


@users_bp.route("/users/{user_id}", methods=["GET"])
@handle_errors
async def get_user(user_id: str) -> UserOut:
    """Return a user by id."""
    async with db_session() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(uuid.UUID(user_id))
        if user is None:
            raise LookupError(f"User {user_id} not found")
        return UserOut.model_validate(user)


@users_bp.route("/users/{user_id}/wallets", methods=["GET"])
@handle_errors
async def list_wallets(user_id: str) -> list[WalletOut]:
    """List the wallets of a user."""
    async with db_session() as session:
        repo = UserRepository(session)
        wallets = await repo.list_wallets(uuid.UUID(user_id))
        return [WalletOut.model_validate(w) for w in wallets]


@users_bp.route("/users/{user_id}/wallets", methods=["POST"])
@handle_errors
async def add_wallet(user_id: str) -> WalletOut:
    """Link an EVM wallet to a user."""
    body = WalletCreate.model_validate(
        users_bp.current_request.json_body
    )
    async with db_session() as session:
        repo = UserRepository(session)
        wallet = await repo.add_wallet(
            user_id=uuid.UUID(user_id),
            address=body.address,
            chain_id=body.chain_id,
        )
        await session.commit()
        return WalletOut.model_validate(wallet)