"""SUN token operations: mint and transfer.

This service is the only place in the backend that knows the SUN
contract address and ABI. It exposes two high-level operations:

* :meth:`mint` — used by :class:`CreditService` when a validated
  energy interval produces a credit.
* :meth:`transfer` — used by the marketplace when settling a trade.

Both delegate to :func:`send_transaction` for signing and broadcasting.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Any

from web3.contract import Contract
from web3.types import TxReceipt

from solar_market.blockchain.transaction_service import send_transaction
from solar_market.blockchain.web3_client import load_contract
from solar_market.core.config import settings

logger = logging.getLogger(__name__)

# Path to the ABI artifact produced by ``forge build``. The Dockerfile
# copies ``contracts/out`` into the backend image so this file exists at
# runtime.
_ABI_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "out"
    / "SUNToken.sol"
    / "SUNToken.json"
)

class TokenService:
    """High-level operations on the SUN ERC-20 token."""

    def __init__(self) -> None:
        self._contract = self._load_sun_contract()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def mint(self, *, to: str, amount_tokens: Decimal) -> TxReceipt:
        """Mint ``amount_tokens`` SUN to ``to``.

        Args:
            to: Recipient EVM address.
            amount_tokens: Amount in whole SUN tokens (1 SUN = 1 kWh).

        Returns:
            The mined transaction receipt.
        """
        amount_wei = self._to_wei(amount_tokens)
        logger.info(
            "Minting %s SUN to %s", amount_tokens, to
        )
        receipt = send_transaction(
            self._contract.functions.mint(to, amount_wei)
        )
        return receipt  # type: ignore[return-value]

    def transfer(self, *, to: str, amount_tokens: Decimal) -> TxReceipt:
        """Transfer ``amount_tokens`` SUN from the backend wallet to ``to``."""
        amount_wei = self._to_wei(amount_tokens)
        logger.info(
            "Transferring %s SUN to %s", amount_tokens, to
        )
        receipt = send_transaction(
            self._contract.functions.transfer(to, amount_wei)
        )
        return receipt  # type: ignore[return-value]

    def balance_of(self, address: str) -> Decimal:
        """Return the SUN balance of ``address`` as a decimal token amount."""
        raw = self._contract.functions.balanceOf(address).call()
        return Decimal(raw) / Decimal(10**18)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _load_sun_contract(self) -> Contract:
        if not settings.sun_token_address:
            raise RuntimeError(
                "SUN_TOKEN_ADDRESS is not set; cannot bind the token contract"
            )
        abi = self._load_abi()
        return load_contract(settings.sun_token_address, abi)

    @staticmethod
    def _load_abi() -> list[dict[str, Any]]:
        if not _ABI_PATH.exists():
            raise FileNotFoundError(
                f"SUNToken ABI not found at {_ABI_PATH}. "
                "Run `forge build` in contracts/ before starting the backend."
            )
        artifact = json.loads(_ABI_PATH.read_text())
        return artifact["abi"]

    @staticmethod
    def _to_wei(amount_tokens: Decimal) -> int:
        """Convert a decimal token amount to 18-decimals wei."""
        return int(amount_tokens * Decimal(10**18))