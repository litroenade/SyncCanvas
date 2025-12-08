"""包名称: routers
功能说明: 统一管理 API 路由、中间件和静态文件挂载
"""

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.config import config
from src.logger import get_logger
from .ai import router as ai_router
from .rooms import router as rooms_router
from .igit import igit_router


logger = get_logger(__name__)


def mount_middlewares(app: FastAPI):
    """
    挂载中间件
    
    配置 CORS 中间件,允许跨域请求
    
    @param app - FastAPI 应用实例
    """
    origins = config.allowed_origins
    allow_all = "*" in origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_all else origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def mount_api_routes(app: FastAPI):
    """
    挂载 API 路由
    
    统一管理所有 API 端点,前缀为 /api

    """
    api = APIRouter(prefix="/api", tags=["API"])

    @api.get("/health")
    async def health_check():
        """
        健康检查端点
        
        @returns 服务状态信息
        """
        return {
            "code": 0,
            "msg": "Board Service Running...",
            "data": {
                "status": "healthy",
                "version": "1.0.0"
            }
        }

    @api.get("/stats")
    async def get_stats():
        """
        获取统计信息
        
        @returns 在线用户数等统计数据
        """
        from src.ws.sync import websocket_server
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "online_rooms": len(websocket_server.rooms)
            }
        }

    # 挂载 API 路由到主应用
    app.include_router(api)
    app.include_router(ai_router, prefix="/api")
    app.include_router(rooms_router, prefix="/api")
    # igit_router 需要挂载到 /api/rooms 下，因为它的端点是 /{room_id}/history 等
    app.include_router(igit_router, prefix="/api/rooms")

    # 挂载前端静态文件到 /webui 路径
    static_dir = Path("frontend/dist")
    if static_dir.exists():
        app.mount("/webui", StaticFiles(directory=str(static_dir), html=True), name="webui")
        logger.info("前端静态文件已挂载", extra={"path": str(static_dir)})

        # 根路径重定向到前端界面
        @app.get("/", include_in_schema=False)
        async def redirect_to_webui():
            """根路径重定向到前端界面"""
            return RedirectResponse(url="/webui", status_code=302)

        @app.get("/index.html", include_in_schema=False)
        async def redirect_index_to_webui():
            """index.html 重定向到前端界面"""
            return RedirectResponse(url="/webui", status_code=302)

        logger.info("根路径重定向已配置", extra={"from": "/", "to": "/webui/"})
    else:
        logger.warning("前端静态文件目录不存在", extra={"path": str(static_dir)})
        logger.warning("请先构建前端", extra={"command": "cd frontend && pnpm build"})
