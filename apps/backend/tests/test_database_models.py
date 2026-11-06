"""Database metadata regression tests."""

from app.db.models import Base


def test_all_application_tables_are_registered() -> None:
    """Alembic metadata must contain every application-owned table."""
    expected = {
        "users",
        "homes",
        "devices",
        "telemetry_messages",
        "energy_intervals",
        "energy_credits",
        "token_issuances",
        "orders",
        "trades",
        "redemptions",
        "wallets",
        "audit_events",
        "blockchain_transactions",
        "blockchain_events",
        "outbox_events",
    }

    assert expected <= set(Base.metadata.tables)


def test_telemetry_and_credit_constraints_are_present() -> None:
    """Critical idempotency and credit constraints remain in the model."""
    telemetry = Base.metadata.tables["telemetry_messages"]
    credits = Base.metadata.tables["energy_credits"]

    assert any(
        constraint.name == "uq_telemetry_device_seq"
        for constraint in telemetry.constraints
    )
    assert any(
        constraint.name == "ck_credit_energy" for constraint in credits.constraints
    )
    assert any(
        constraint.name == "ck_credit_amount" for constraint in credits.constraints
    )
