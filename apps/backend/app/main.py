"""FastAPI application factory and process entry point."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import get_engine
from app.core.exceptions import AuthorizationError, ConflictError, ResourceNotFoundError
from app.core.lifespan import lifespan


def create_app() -> FastAPI:
    """Create and configure the HTTP application."""
    application = FastAPI(
        title="Solar Energy Market API",
        version="0.1.0",
        description="Telemetry, energy credits, marketplace, and redemptions.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    origins = [
        origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()
    ]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=bool(origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix="/api/v1")

    @application.exception_handler(ResourceNotFoundError)
    async def handle_not_found(_: Any, exc: ResourceNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @application.exception_handler(ConflictError)
    async def handle_conflict(_: Any, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @application.exception_handler(AuthorizationError)
    async def handle_forbidden(_: Any, exc: AuthorizationError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @application.exception_handler(RequestValidationError)
    async def handle_validation(_: Any, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    @application.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        """Return liveness status without requiring external services."""
        return {"status": "ok"}

    @application.get("/ready", tags=["system"])
    async def ready() -> dict[str, str]:
        """Verify that the configured database is reachable."""
        async with get_engine().connect() as connection:
            await connection.exec_driver_sql("SELECT 1")
        return {"status": "ready"}

    return application


app = create_app()
