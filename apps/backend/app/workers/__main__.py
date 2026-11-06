"""Run the durable outbox worker."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from app.blockchain.token_service import TokenService
from app.core.database import get_session_factory
from app.db.models.credit import EnergyCredit, TokenIssuance
from app.db.models.security import OutboxEvent
from app.db.models.wallet import Wallet
from app.workers.outbox_worker import OutboxWorker

logger = logging.getLogger(__name__)


async def issue_credit(event: OutboxEvent) -> None:
    """Mint one approved credit to its verified owner wallet."""
    async with get_session_factory()() as session:
        credit = await session.get(EnergyCredit, event.aggregate_id)
        if credit is None or credit.status not in {"approved", "issuance_pending"}:
            raise ValueError("credit is unavailable for issuance")
        wallet = await session.scalar(
            select(Wallet).where(
                Wallet.user_id == credit.owner_id, Wallet.is_verified.is_(True)
            )
        )
        if wallet is None:
            raise ValueError("owner has no verified wallet")
        existing = await session.scalar(
            select(TokenIssuance).where(TokenIssuance.credit_id == credit.id)
        )
        if existing is not None and existing.status in {"submitted", "confirmed"}:
            return
        token_service = TokenService()
        receipt = token_service.mint(
            to=wallet.address, amount_tokens=credit.token_amount
        )
        if existing is None:
            existing = TokenIssuance(
                credit_id=credit.id,
                wallet_id=wallet.id,
                chain_id=wallet.chain_id,
                token_amount=credit.token_amount,
            )
            session.add(existing)
        existing.status = "confirmed"
        existing.transaction_hash = receipt["transactionHash"].hex()
        existing.block_number = receipt["blockNumber"]
        credit.status = "issued"
        await session.commit()


async def run() -> None:
    """Poll the outbox until the process is stopped."""
    worker = OutboxWorker(get_session_factory(), {"credit.issue": issue_credit})
    while True:
        processed = await worker.process_once()
        if processed == 0:
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(run())
