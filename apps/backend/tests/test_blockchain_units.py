"""Deterministic blockchain service unit tests."""

from decimal import Decimal

import pytest

from app.blockchain.token_service import TokenService


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("0"), 0),
        (Decimal("1"), 10**18),
        (Decimal("1.5"), 15 * 10**17),
        (Decimal("0.000000000000000001"), 1),
    ],
)
def test_token_amount_conversion(amount: Decimal, expected: int) -> None:
    assert TokenService._to_wei(amount) == expected


def test_token_amount_conversion_truncates_sub_wei_precision() -> None:
    assert TokenService._to_wei(Decimal("1.0000000000000000009")) == 10**18


def test_token_contract_requires_address(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.blockchain import token_service

    monkeypatch.setattr(token_service.settings, "sun_token_address", "")
    with pytest.raises(RuntimeError, match="SUN_TOKEN_ADDRESS"):
        TokenService()
