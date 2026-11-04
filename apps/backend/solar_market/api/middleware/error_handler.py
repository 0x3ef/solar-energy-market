"""Decorator that turns exceptions into Chalice JSON responses."""

from __future__ import annotations

import functools
import logging
from typing import Any, Awaitable, Callable

from chalice import Response

logger = logging.getLogger(__name__)


def handle_errors(
    func: Callable[..., Awaitable[Any]],
) -> Callable[..., Awaitable[Any]]:
    """Wrap ``func`` so known exceptions become JSON responses."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except ValueError as exc:
            logger.warning("Validation error: %s", exc)
            return Response(
                body={"error": str(exc)},
                status_code=400,
                headers={"Content-Type": "application/json"},
            )
        except LookupError as exc:
            logger.info("Not found: %s", exc)
            return Response(
                body={"error": str(exc)},
                status_code=404,
                headers={"Content-Type": "application/json"},
            )
        except Exception:
            logger.exception("Unhandled error in %s", func.__name__)
            return Response(
                body={"error": "internal server error"},
                status_code=500,
                headers={"Content-Type": "application/json"},
            )

    return wrapper