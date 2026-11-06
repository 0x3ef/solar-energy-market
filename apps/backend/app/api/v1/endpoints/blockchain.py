"""Read-only blockchain status and transaction endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3
from web3.exceptions import Web3Exception

from app.api.deps import get_current_user, get_db
from app.blockchain.web3_client import get_chain_id, get_web3
from app.core.config import settings
from app.db.models.security import BlockchainTransaction

router = APIRouter(tags=["blockchain"])


@router.get("/blockchain/status")
async def blockchain_status(_: Any = Depends(get_current_user)) -> dict[str, Any]:
    """Return provider connectivity without exposing signer material."""
    try:
        client = get_web3()
        return {"connected": client.is_connected(), "chain_id": get_chain_id()}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="blockchain unavailable") from exc


@router.get("/blockchain/networks")
async def blockchain_networks(_: Any = Depends(get_current_user)) -> list[dict[str, int]]:
    """Return the configured network."""
    return [{"chain_id": settings.chain_id}]


@router.get("/blockchain/transactions/{tx_hash}")
async def transaction(
    tx_hash: str,
    _: Any = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return local audit state and, when available, the current receipt."""
    if not Web3.is_hexstr(tx_hash) or len(tx_hash) != 66:
        raise HTTPException(status_code=422, detail="invalid transaction hash")
    local = await session.scalar(
        select(BlockchainTransaction).where(
            BlockchainTransaction.transaction_hash == tx_hash
        )
    )
    return {
        "transaction_hash": tx_hash,
        "status": local.status if local else "unknown",
        "block_number": local.block_number if local else None,
    }


@router.get("/blockchain/wallets/{address}/balance")
async def balance(
    address: str, _: Any = Depends(get_current_user)
) -> dict[str, str]:
    """Return the native balance for a validated EVM address."""
    try:
        checksum = Web3.to_checksum_address(address)
        value = get_web3().eth.get_balance(checksum)
    except (ValueError, Web3Exception) as exc:
        raise HTTPException(status_code=422, detail="invalid wallet address") from exc
    return {"address": checksum, "balance_wei": str(value)}
