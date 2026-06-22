"""Main API router aggregating all endpoint routers."""

from fastapi import APIRouter

from src.bcd_api.core.config import settings
from src.shared.constants import API_PREFIX

# Create main API router
api_router = APIRouter(prefix=API_PREFIX)


# Placeholder routes will be added in Phase 3
@api_router.get("/health")
async def health_check():
    """Health check endpoint for API v1."""
    return {"status": "healthy", "version": settings.app_version}


# Include routers
from src.bcd_api.api.v1 import (
    admin,
    borrowers,
    catalog,
    circulation,
    classes,
    collections,
    holds,
    inventory,
    reports,
)

api_router.include_router(circulation.router)
api_router.include_router(catalog.router)
api_router.include_router(borrowers.router)
api_router.include_router(classes.router)
api_router.include_router(holds.router)
api_router.include_router(reports.router)
api_router.include_router(admin.router)
api_router.include_router(collections.router)
api_router.include_router(inventory.router)
