# apps/backend/tests/test_token_service.py

from decimal import Decimal

import pytest

from app.blockchain.token_service import TokenService


@pytest.mark.integration
def test_mint_increases_balance(monkeypatch):
    """Requires a running Anvil with SUN deployed."""
    service = TokenService()
    before = service.balance_of("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266")
    service.mint(
        to="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
        amount_tokens=Decimal("1.5"),
    )
    after = service.balance_of("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266")
    assert after - before == Decimal("1.5")
