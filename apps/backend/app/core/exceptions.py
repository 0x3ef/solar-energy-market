"""Application exception types."""

from __future__ import annotations


class ResourceNotFoundError(LookupError):
    """Raised when a requested resource is not visible or does not exist."""


class ConflictError(ValueError):
    """Raised when a request violates a uniqueness or state constraint."""


class AuthorizationError(PermissionError):
    """Raised when an authenticated principal lacks permission."""
