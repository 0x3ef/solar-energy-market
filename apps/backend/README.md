# Solar Market Backend

The backend is a FastAPI application using SQLAlchemy 2.x, Pydantic v2, PostgreSQL/TimescaleDB, MQTT ingestion, and Web3.py. Run it from `apps/backend` with:

```bash
uvicorn app.main:app --reload
pytest
ruff check .
mypy .
```

The local Docker stack is still the preferred integration environment. The API is versioned under `/api/v1`; `/health` is liveness and `/ready` checks database connectivity.

## Runtime boundaries

HTTP routes depend on services, services depend on repositories and integrations, and the MQTT worker persists telemetry independently of HTTP requests. Approved blockchain and redemption operations should be dispatched through `outbox_events`, not executed directly in a request.
