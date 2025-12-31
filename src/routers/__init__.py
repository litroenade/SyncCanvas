from .ai import router as ai_router
from .rooms import router as rooms_router
from .version_control import router as version_control_router
from .config import router as config_router
from .upload import router as upload_router

__all__ = [
    "ai_router",
    "rooms_router",
    "version_control_router",
    "config_router",
    "upload_router",
]
