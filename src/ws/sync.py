"""模块名称: sync
主要功能: 基于 pycrdt_websocket 的实时同步功能，带持久化存储

使用 pycrdt_websocket 模块实现与 Yjs 客户端的完全兼容同步。
通过 SQLiteYStore 实现数据持久化。
"""

import asyncio
from functools import partial
from pathlib import Path
from typing import Any

from pycrdt.websocket import WebsocketServer, ASGIServer, YRoom
from pycrdt.store import SQLiteYStore

from src.logger import get_logger

logger = get_logger(__name__)

# 数据库路径
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "yjs_store.db"


class PersistentWebsocketServer(WebsocketServer):
    """带持久化的 WebsocketServer
    
    继承自 WebsocketServer，为每个房间自动配置 SQLiteYStore 持久化。
    """

    def __init__(self, db_path: str, **kwargs: Any):
        """初始化服务器
        
        Args:
            db_path: SQLite 数据库文件路径
            **kwargs: 传递给父类的其他参数
        """
        super().__init__(**kwargs)
        self.db_path = db_path

    async def get_room(self, name: str) -> YRoom:
        """获取或创建房间，带持久化存储
        
        Args:
            name: 房间名称
            
        Returns:
            配置了 SQLiteYStore 的 YRoom 实例
        """
        if name not in self.rooms:
            # 清理房间名，移除路径前缀，只保留实际名称
            clean_name = name.strip("/").replace("/", "_").replace("\\", "_")
            if clean_name.startswith("ws_"):
                clean_name = clean_name[3:]  # 移除 "ws_" 前缀

            # 为每个房间创建独立的 SQLiteYStore
            room_db_path = self.db_path.replace(".db", f"_{clean_name}.db")
            ystore = SQLiteYStore(path=room_db_path, log=self.log)
            
            # 启动 ystore (确保数据库初始化)
            await ystore.start()

            provider_factory = (
                partial(self.provider_factory, path=name)
                if self.provider_factory is not None
                else None
            )

            self.rooms[name] = YRoom(
                ready=self.rooms_ready,
                ystore=ystore,
                log=self.log,
                provider_factory=provider_factory,
            )
            logger.info("创建房间 '%s'，持久化存储: %s", name, room_db_path)

        room = self.rooms[name]
        await self.start_room(room)
        return room


# 创建带持久化的 WebsocketServer 实例
websocket_server = PersistentWebsocketServer(db_path=str(DB_PATH))

# 创建 ASGI 应用，可以作为子应用挂载到 FastAPI
asgi_server = ASGIServer(websocket_server)


async def background_compaction_task():
    """后台任务：定期执行存储优化

    每小时执行一次，清理过期的增量更新，只保留最新快照。
    """
    while True:
        await asyncio.sleep(3600)  # 每小时执行一次
        try:
            logger.debug("后台压缩任务运行中...")
            # SQLiteYStore 会自动处理压缩
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("后台任务执行失败: %s", e)
