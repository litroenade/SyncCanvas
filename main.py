"""SyncCanvas 主应用模块

提供 FastAPI 应用实例、WebSocket 集成和静态文件服务。
"""

import os
import subprocess
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.db.database import init_db
from src.ws.sync import websocket_server, asgi_server
from src.ws.message_router import message_router
from src.utils.async_task import async_task_manager
from src.config import config
from src.logger import get_logger, setup_logging
from src.auth.router import router as auth_router
from src.routers.ai import router as ai_router
from src.routers.upload import router as upload_router
from src.routers.rooms import router as rooms_router
from src.routers.version_control import version_control_router
from src.routers.config import router as config_router

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期管理

    Args:
        _app: FastAPI 应用实例（未使用）
    """
    # 启动时初始化数据库
    logger.info("初始化数据库")
    init_db()

    # 启动 pycrdt-websocket 服务器
    async with websocket_server:
        # 启动消息路由器
        await message_router.start()
        logger.info("消息路由器已启动")

        # 启动后台任务
        await async_task_manager.start_all()

        logger.info("服务器启动完成")

        yield

        # 关闭时清理
        logger.info("服务器正在关闭")
        await async_task_manager.stop_all()
        await message_router.stop()


# 创建 FastAPI 应用
app = FastAPI(
    title="SyncCanvas",
    description="基于 CRDT 的实时协作白板系统",
    version="0.1.0",
    lifespan=lifespan,
)

# 挂载中间件 (CORS 等)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由 (所有 API 都使用 /api 前缀)
app.include_router(auth_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(upload_router)  # upload_router 自带 /api/upload 前缀
app.include_router(rooms_router, prefix="/api")
app.include_router(version_control_router, prefix="/api/rooms")
app.include_router(config_router, prefix="/api")


# 挂载 pycrdt-websocket 的 ASGI 服务器到 /ws 路径
app.mount("/ws", asgi_server)


# 图片上传目录
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "data", "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# 挂载图片静态服务
app.mount("/api/images", StaticFiles(directory=IMAGES_DIR), name="images")

# 前端构建产物路径
FRONTEND_DIST_DIR = os.path.join(os.path.dirname(__file__), "frontend", "dist")
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")


def build_frontend():
    """自动构建前端"""

    logger.info("检测到前端构建目录不存在，开始自动构建...")

    try:
        # 检查是否有 pnpm
        result = subprocess.run(
            ["pnpm", "--version"],
            capture_output=True,
            text=True,
            cwd=FRONTEND_DIR,
            shell=True,
            check=False,
        )
        if result.returncode != 0:
            logger.warning("未找到 pnpm，尝试使用 npm")
            pkg_manager = "npm"
        else:
            pkg_manager = "pnpm"

        # 安装依赖
        logger.info("使用 %s 安装依赖...", pkg_manager)
        subprocess.run(
            [pkg_manager, "install"],
            cwd=FRONTEND_DIR,
            check=True,
            shell=True,
        )

        # 构建
        logger.info("使用 %s 构建前端...", pkg_manager)
        subprocess.run(
            [pkg_manager, "run", "build"],
            cwd=FRONTEND_DIR,
            check=True,
            shell=True,
        )

        logger.info("前端构建完成！")
        return True
    except subprocess.CalledProcessError as e:
        logger.error("前端构建失败: %s", e)
        return False
    except FileNotFoundError as e:
        logger.error("包管理器未找到: %s", e)
        return False


# 检查前端构建目录，如果不存在则自动构建
if not os.path.exists(FRONTEND_DIST_DIR):
    build_frontend()

if os.path.exists(FRONTEND_DIST_DIR):
    # 挂载静态资源 (assets 目录)
    assets_dir = os.path.join(FRONTEND_DIST_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # SPA fallback: 所有未匹配的路由返回 index.html
    @app.get("/{full_path:path}")
    async def serve_spa(_request: Request, full_path: str):
        """处理 SPA 路由，返回 index.html"""
        # 如果是请求静态文件（有文件扩展名），尝试返回对应文件
        if "." in full_path:
            file_path = os.path.join(FRONTEND_DIST_DIR, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
        # 否则返回 index.html (SPA fallback)
        index_path = os.path.join(FRONTEND_DIST_DIR, "index.html")
        return FileResponse(index_path)
else:
    logger.warning(
        "前端构建目录不存在: %s，无法提供静态文件服务。请先运行 'pnpm build'。",
        FRONTEND_DIST_DIR,
    )


if __name__ == "__main__":
    uvicorn.run(app, host=config.host, port=config.port)
