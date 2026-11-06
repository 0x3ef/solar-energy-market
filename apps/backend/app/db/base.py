"""SQLAlchemy declarative base for backend models."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class shared by all ORM models."""
