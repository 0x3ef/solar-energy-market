"""Web3 connection and account management.

The backend holds a single hot wallet whose private key comes from
``BACKEND_PRIVATE_KEY``. That wallet is the *minter* role of the
``SUNToken`` contract and the *signer* of every backend-initiated
transaction (mint, transfer, trade settlement).

Design notes:

* The ``Web3`` instance is created lazily so importing this module from
  the client does not open a connection until the first call.
* The private key is never logged.
* ``chain_id`` is read from the node on first use and cached, so the
  backend works against Anvil (31337), Sepolia (11155111) or any EVM
  chain without code changes.
"""

from __future__ import annotations

import logging
from threading import Lock

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.contract import Contract
from web3.middleware import ExtraDataToPOAMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)

_lock = Lock()
_web3: Web3 | None = None
_account: LocalAccount | None = None
_chain_id: int | None = None


def get_web3() -> Web3:
    """Return the process-wide ``Web3`` instance, creating it on first call."""
    global _web3
    with _lock:
        if _web3 is None:
            logger.info(
                "Connecting to Web3 provider at %s",
                settings.web3_provider_url,
            )
            _web3 = Web3(Web3.HTTPProvider(settings.web3_provider_url))
            # Anvil and many testnets are PoA chains; this middleware
            # is required for web3.py to handle their block headers.
            _web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        return _web3


def get_account() -> LocalAccount:
    """Return the backend hot wallet derived from ``BACKEND_PRIVATE_KEY``."""
    global _account
    with _lock:
        if _account is None:
            if not settings.backend_private_key:
                raise RuntimeError(
                    "BACKEND_PRIVATE_KEY is not set; the backend "
                    "cannot sign transactions"
                )
            _account = Account.from_key(settings.backend_private_key)
            logger.info("Backend signer address: %s", _account.address)
        return _account


def get_chain_id() -> int:
    """Return the connected chain id, cached after the first call."""
    global _chain_id
    with _lock:
        if _chain_id is None:
            _chain_id = get_web3().eth.chain_id
            logger.info("Connected chain id: %d", _chain_id)
        return _chain_id


def load_contract(address: str, abi: list[dict]) -> Contract:
    """Build a ``Contract`` instance bound to ``address``.

    Args:
        address: Checksummed contract address.
        abi: Contract ABI as returned by ``forge build``.

    Returns:
        A web3 ``Contract`` ready for ``.functions.*`` calls.
    """
    checksummed = Web3.to_checksum_address(address)
    return get_web3().eth.contract(address=checksummed, abi=abi)


def reset() -> None:
    """Drop cached instances. Intended for tests."""
    global _web3, _account, _chain_id
    with _lock:
        _web3 = None
        _account = None
        _chain_id = None
