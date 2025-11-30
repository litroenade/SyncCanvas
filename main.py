import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.db.database import init_db
from src.ws.sync import websocket_server, asgi_server, background_compaction_task
from src.config import HOST, PORT, ALLOWED_ORIGINS
from src.logger import get_logger, setup_logging
from src.auth.router import router as auth_router
from src.routers.ai import router as ai_router
from src.routers.upload import router as upload_router
from src.routers.rooms import router as rooms_router

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
        # 启动后台任务 (快照压缩)
        task = asyncio.create_task(background_compaction_task())

        logger.info("服务器启动完成")

        yield

        # 关闭时清理
        logger.info("服务器正在关闭")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


# 创建 FastAPI 应用
app = FastAPI(
    title="SyncCanvas",
    description="基于 CRDT 的实时协作白板系统",
    version="2.0.0",
    lifespan=lifespan,
)

# 挂载中间件 (CORS 等)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(upload_router)
app.include_router(rooms_router)


# 挂载 pycrdt-websocket 的 ASGI 服务器到 /ws 路径
app.mount("/ws", asgi_server)




# 图片上传目录
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "data", "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# 挂载图片静态服务
app.mount("/api/images", StaticFiles(directory=IMAGES_DIR), name="images")

# 前端构建产物路径
FRONTEND_DIST_DIR = os.path.join(os.path.dirname(__file__), "frontend", "dist")

if os.path.exists(FRONTEND_DIST_DIR):

    app.mount("/", StaticFiles(directory=FRONTEND_DIST_DIR, html=True), name="static")
else:
    logger.warning(
        "前端构建目录不存在: %s，无法提供静态文件服务。请先运行 'pnpm build'。",
        FRONTEND_DIST_DIR,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
