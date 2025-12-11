"""包名称: routers
功能说明: API 路由模块导出
"""

from .ai import router as ai_router
from .rooms import router as rooms_router
from .igit import igit_router
from .config import router as config_router
from .upload import router as upload_router

__all__ = [
    "ai_router",
    "rooms_router",
    "igit_router",
    "config_router",
    "upload_router",
]
