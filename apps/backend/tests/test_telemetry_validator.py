"""Tests for the telemetry validator."""

from __future__ import annotations

from datetime import UTC, datetime

from app.iot.telemetry_validator import validate_envelope


def _valid() -> dict:
    return {
        "schema_version": "1.0",
        "device_id": "SM-CALI-001-001",
        "home_id": "HOME-CALI-001",
        "sensor_type": "smart_meter",
        "sequence_number": 1,
        "measured_at": datetime.now(UTC).isoformat(),
        "data": {"voltage_v": 120.5, "current_a": 5.0},
    }


def test_valid_envelope() -> None:
    envelope, errors = validate_envelope(_valid())
    assert envelope is not None
    assert errors == []


def test_naive_datetime_rejected() -> None:
    raw = _valid()
    raw["measured_at"] = "2026-01-01T12:00:00"
    envelope, errors = validate_envelope(raw)
    assert envelope is None
    assert any("timezone-aware" in e["msg"] for e in errors)


def test_bad_payload_returns_envelope() -> None:
    raw = _valid()
    raw["data"] = {"voltage_v": -1.0}
    envelope, errors = validate_envelope(raw)
    assert envelope is not None
    assert errors
