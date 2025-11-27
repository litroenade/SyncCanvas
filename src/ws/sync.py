"""模块名称: sync
主要功能: 基于 pycrdt-websocket 的实时同步功能

使用 pycrdt-websocket 库实现与 Yjs 客户端的完全兼容同步。
"""

from pycrdt.websocket import WebsocketServer, ASGIServer

from src.logger import get_logger

logger = get_logger(__name__)

# 创建 WebsocketServer 实例
# 这是 pycrdt-websocket 提供的核心类，处理所有 Yjs 协议细节
websocket_server = WebsocketServer()

# 创建 ASGI 应用，可以作为子应用挂载到 FastAPI
asgi_server = ASGIServer(websocket_server)


async def background_compaction_task():
    """后台压缩任务占位符

    pycrdt-websocket 内部会处理文档状态管理
    """
    import asyncio

    while True:
        await asyncio.sleep(3600)
        logger.debug("后台任务运行中...")
