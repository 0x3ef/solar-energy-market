"""Tests for Pydantic schemas."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from solar_market.schemas.order import OrderCreate, RedemptionCreate
from solar_market.schemas.user import UserCreate, WalletCreate


def test_user_create_valid() -> None:
    body = UserCreate(
        email="a@b.com", full_name="Test", password="12345678"
    )
    assert body.email == "a@b.com"


def test_user_create_short_password() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", full_name="T", password="short")


def test_wallet_create_valid_address() -> None:
    body = WalletCreate(
        address="0x" + "a" * 40, chain_id=31337
    )
    assert body.chain_id == 31337


def test_wallet_create_bad_address() -> None:
    with pytest.raises(ValidationError):
        WalletCreate(address="not-an-address", chain_id=1)


def test_order_create_valid() -> None:
    body = OrderCreate(
        seller_id="11111111-1111-1111-1111-111111111111",
        order_type="sell",
        token_amount=Decimal("10"),
        price_per_token=Decimal("0.5"),
    )
    assert body.token_amount == Decimal("10")


def test_order_create_negative_amount() -> None:
    with pytest.raises(ValidationError):
        OrderCreate(
            seller_id="11111111-1111-1111-1111-111111111111",
            order_type="sell",
            token_amount=Decimal("-1"),
            price_per_token=Decimal("0.5"),
        )


def test_redemption_create_valid() -> None:
    body = RedemptionCreate(
        user_id="11111111-1111-1111-1111-111111111111",
        wallet_id="22222222-2222-2222-2222-222222222222",
        token_amount=Decimal("5"),
    )
    assert body.token_amount == Decimal("5")