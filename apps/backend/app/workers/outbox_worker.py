"""Transactional outbox polling with retry and dead-letter handling."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.security import OutboxEvent

logger = logging.getLogger(__name__)
OutboxHandler = Callable[[OutboxEvent], Awaitable[None]]


class OutboxWorker:
    """Claim pending events atomically and retry transient failures."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        handlers: dict[str, OutboxHandler],
        *,
        max_attempts: int = 8,
    ) -> None:
        self._session_factory = session_factory
        self._handlers = handlers
        self._max_attempts = max_attempts

    async def process_once(self, limit: int = 50) -> int:
        """Process one bounded batch and return the number of claimed events."""
        async with self._session_factory() as session:
            result = await session.scalars(
                select(OutboxEvent)
                .where(
                    OutboxEvent.status == "pending",
                    OutboxEvent.available_at <= datetime.now(UTC),
                )
                .order_by(OutboxEvent.created_at)
                .with_for_update(skip_locked=True)
                .limit(limit)
            )
            events = list(result)
            for event in events:
                await self._process_event(session, event)
            await session.commit()
            return len(events)

    async def _process_event(
        self, session: AsyncSession, event: OutboxEvent
    ) -> None:
        handler = self._handlers.get(event.event_type)
        if handler is None:
            event.status = "dead_letter"
            event.last_error = f"no handler for {event.event_type}"
            return
        event.attempts += 1
        try:
            await handler(event)
        except Exception as exc:
            event.last_error = str(exc)[:1000]
            if event.attempts >= self._max_attempts:
                event.status = "dead_letter"
            else:
                event.status = "pending"
                event.available_at = datetime.now(UTC) + timedelta(
                    seconds=min(300, 2**event.attempts)
                )
            logger.exception("Outbox event %s failed", event.id)
        else:
            event.status = "processed"
            event.processed_at = datetime.now(UTC)
