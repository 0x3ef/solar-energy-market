"""Configuration safety tests."""

from app.core.config import Settings


def test_local_defaults_are_usable() -> None:
    settings = Settings(_env_file=None)

    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.chain_id == 31337
    assert settings.db_pool_size > 0


def test_jwt_secret_requires_minimum_length() -> None:
    from pydantic import ValidationError

    try:
        Settings(_env_file=None, jwt_secret="too-short")
    except ValidationError:
        return
    raise AssertionError("short JWT secrets must be rejected")
