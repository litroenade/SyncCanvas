"""Canonical API router exports."""

from src.api.routers.ai.handlers import router as ai_router
from src.api.routers.admin import router as admin_router
from src.api.routers.auth import router as auth_router
from src.api.routers.config import router as config_router
from src.api.routers.rooms import router as rooms_router
from src.api.routers.upload import router as upload_router
from src.api.routers.version_control import router as version_control_router

__all__ = [
    "ai_router",
    "admin_router",
    "auth_router",
    "config_router",
    "rooms_router",
    "upload_router",
    "version_control_router",
]
