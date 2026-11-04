"""Generic signed-transaction helper.

Every write to the chain (mint, transfer, trade settlement) goes through
:func:`send_transaction`, which handles nonce, gas estimation, signing,
broadcasting and receipt waiting in one place. Callers only build the
``ContractFunction`` and pass it in.
"""

from __future__ import annotations

import logging
from typing import Any

from hexbytes import HexBytes
from web3.contract.contract import ContractFunction
from web3.types import TxReceipt

from solar_market.blockchain.web3_client import (
    get_account,
    get_chain_id,
    get_web3,
)

logger = logging.getLogger(__name__)


def send_transaction(
    function: ContractFunction,
    *,
    value: int = 0,
    gas: int | None = None,
    gas_price: int | None = None,
    wait: bool = True,
) -> TxReceipt | HexBytes:
    """Build, sign, broadcast and (optionally) wait for a transaction.

    Args:
        function: Bound contract function, e.g.
            ``sun_contract.functions.mint(to, amount)``.
        value: Native token value in wei (rarely needed for ERC-20).
        gas: Explicit gas limit. If ``None``, estimated automatically.
        gas_price: Explicit gas price in wei. If ``None``, the node's
            ``eth_gasPrice`` is used.
        wait: When ``True``, block until the transaction is mined and
            return the receipt. When ``False``, return the tx hash.

    Returns:
        ``TxReceipt`` if ``wait`` is ``True``, otherwise the tx hash.
    """
    w3 = get_web3()
    account = get_account()

    tx = function.build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "chainId": get_chain_id(),
            "value": value,
            "gasPrice": gas_price or w3.eth.gas_price,
        }
    )

    if gas is not None:
        tx["gas"] = gas
    else:
        # Estimate against the *from* address so state overrides apply.
        tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.2)

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    logger.info("Sent transaction %s", tx_hash.hex())

    if not wait:
        return tx_hash

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt["status"] != 1:
        raise RuntimeError(
            f"Transaction {tx_hash.hex()} reverted "
            f"(block {receipt['blockNumber']})"
        )
    logger.info(
        "Transaction %s mined in block %d",
        tx_hash.hex(),
        receipt["blockNumber"],
    )
    return receipt