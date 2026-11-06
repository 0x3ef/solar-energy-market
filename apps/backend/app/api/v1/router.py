"""Version-one API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    blockchain,
    credits,
    devices,
    energy,
    homes,
    iot,
    marketplace,
    redemptions,
    users,
    wallets,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(homes.router, tags=["homes"])
api_router.include_router(devices.router, tags=["devices"])
api_router.include_router(energy.router, tags=["energy"])
api_router.include_router(marketplace.router, tags=["marketplace"])
api_router.include_router(redemptions.router, tags=["redemptions"])
api_router.include_router(credits.router, tags=["credits"])
api_router.include_router(blockchain.router, tags=["blockchain"])
api_router.include_router(iot.router, tags=["iot"])
api_router.include_router(wallets.router, tags=["wallets"])
