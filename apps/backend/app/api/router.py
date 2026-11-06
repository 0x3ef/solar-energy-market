"""Root API router composition."""

from fastapi import APIRouter

from app.api.v1.router import api_router

router = APIRouter()
router.include_router(api_router, prefix="/api/v1")

__all__ = ["router"]
