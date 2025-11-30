"""模块名称: sync
主要功能: 基于 pycrdt_websocket 的实时同步功能，带持久化存储

使用 pycrdt_websocket 模块实现与 Yjs 客户端的完全兼容同步。
通过自定义 SQLModelYStore 实现数据持久化，与业务数据统一存储。
支持用户连接追踪和自动提交功能。
"""

import asyncio
import time
import hashlib
from functools import partial
from typing import Any

from anyio import create_task_group
from pycrdt import Channel
from pycrdt.websocket import WebsocketServer, ASGIServer, YRoom
from pycrdt import Doc
from sqlmodel import Session, select, delete

from src.db.ystore import SQLModelYStore
from src.db.database import engine
from src.db.models import Room, Snapshot, Update, Commit
from src.logger import get_logger

logger = get_logger(__name__)


def generate_commit_hash(commit_id: int, timestamp: int) -> str:
    """生成提交哈希"""
    data = f"{commit_id}-{timestamp}"
    full_hash = hashlib.sha1(data.encode()).hexdigest()
    return full_hash[:7]


class PersistentWebsocketServer(WebsocketServer):
    """带持久化的 WebsocketServer
    
    继承自 WebsocketServer，为每个房间自动配置 SQLModelYStore 持久化。
    所有房间数据存储在同一个 SQLite 数据库 (sync_canvas.db) 中。
    支持用户连接追踪和自动提交功能。
    """

    def __init__(self, **kwargs: Any):
        """初始化服务器"""
        # 禁用自动清理房间，我们自己管理
        kwargs['auto_clean_rooms'] = False
        super().__init__(**kwargs)
        self._ystores: dict[str, SQLModelYStore] = {}
        # 追踪每个房间的连接数
        self._room_connections: dict[str, int] = {}
        # 追踪房间最后活动时间 (用于空闲检测)
        self._room_last_activity: dict[str, float] = {}

    async def serve(self, websocket: Channel) -> None:
        """重写 serve 方法以追踪连接
        
        Args:
            websocket: WebSocket 通道
        """
        name = websocket.path

        try:
            async with create_task_group():
                room = await self.get_room(name)
                await self.start_room(room)
                await room.serve(websocket)
        except Exception as exception:  # pylint: disable=broad-except
            self._handle_exception(exception)
        finally:
            # 连接断开后处理
            await self._on_client_disconnect(name)

    async def get_room(self, name: str) -> YRoom:
        """获取或创建房间，带持久化存储
        
        Args:
            name: 房间名称 (WebSocket 路径，如 /ws/room-uuid)
            
        Returns:
            配置了 SQLModelYStore 的 YRoom 实例
        """
        if name not in self.rooms:
            # 从路径中提取房间 ID
            # 路径格式: /ws/{room_id} 或 /{room_id}
            room_id = name.strip("/").split("/")[-1]

            # 创建 YStore
            ystore = SQLModelYStore(room_id=room_id, log=self.log)
            self._ystores[name] = ystore

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
            logger.info("创建房间 '%s'，房间 ID: %s", name, room_id)

        room = self.rooms[name]
        await self.start_room(room)

        # 增加连接计数
        self._room_connections[name] = self._room_connections.get(name, 0) + 1
        self._room_last_activity[name] = time.time()
        logger.debug("房间 '%s' 连接数: %d", name, self._room_connections[name])

        return room

    async def _on_client_disconnect(self, name: str) -> None:
        """处理客户端断开连接
        
        Args:
            name: 房间名称
        """
        if name in self._room_connections:
            self._room_connections[name] = max(0, self._room_connections[name] - 1)
            logger.debug("房间 '%s' 断开连接，剩余连接数: %d", name, self._room_connections[name])

            # 如果是最后一个用户离开，触发自动提交
            if self._room_connections[name] == 0:
                await self._auto_commit_on_last_leave(name)

    async def _auto_commit_on_last_leave(self, name: str) -> None:
        """最后一个用户离开时自动提交
        
        Args:
            name: 房间名称
        """
        try:
            room_id = name.strip("/").split("/")[-1]
            logger.info("房间 '%s' 最后用户离开，触发自动提交", room_id)

            # 先刷新缓冲区
            if name in self._ystores:
                ystore = self._ystores[name]
                ystore.stop()

            # 等待一小段时间确保数据已写入
            await asyncio.sleep(0.5)

            # 创建自动提交
            await self._create_auto_commit(room_id, "Auto save on disconnect")

        except Exception as e:  # pylint: disable=broad-except
            logger.error("房间 '%s' 自动提交失败: %s", name, e)

    async def _create_auto_commit(self, room_id: str, message: str) -> bool:
        """创建自动提交
        
        Args:
            room_id: 房间 ID
            message: 提交消息
            
        Returns:
            bool: 是否成功创建提交
        """
        try:
            with Session(engine) as session:
                # 检查房间是否存在
                room = session.get(Room, room_id)
                if not room:
                    logger.warning("自动提交失败: 房间 %s 不存在", room_id)
                    return False

                # 构建完整文档状态
                ydoc = Doc()

                # 获取最新快照
                snapshot_stmt = (
                    select(Snapshot)
                    .where(Snapshot.room_id == room_id)
                    .order_by(Snapshot.timestamp.desc())
                    .limit(1)
                )
                snapshot = session.exec(snapshot_stmt).first()

                if snapshot:
                    ydoc.apply_update(snapshot.data)

                # 获取增量更新
                if snapshot:
                    updates_stmt = (
                        select(Update)
                        .where(Update.room_id == room_id)
                        .where(Update.timestamp > snapshot.timestamp)
                        .order_by(Update.timestamp)
                    )
                else:
                    updates_stmt = (
                        select(Update)
                        .where(Update.room_id == room_id)
                        .order_by(Update.timestamp)
                    )

                updates = session.exec(updates_stmt).all()
                for update in updates:
                    ydoc.apply_update(update.data)

                # 检查是否有数据
                doc_data = ydoc.get_update()
                if not doc_data or len(doc_data) <= 2:
                    logger.debug("房间 %s 没有数据可提交", room_id)
                    return False

                # 检查是否有新的更改 (如果没有 Update 且有快照，说明没有新更改)
                if not updates and snapshot:
                    logger.debug("房间 %s 没有新的更改", room_id)
                    return False

                # 创建提交
                current_time = int(time.time() * 1000)
                commit = Commit(
                    room_id=room_id,
                    parent_id=room.head_commit_id,
                    author_id=None,
                    author_name="System",
                    message=message,
                    data=doc_data,
                    timestamp=current_time,
                )
                session.add(commit)
                session.flush()

                commit.hash = generate_commit_hash(commit.id, current_time)

                # 更新 HEAD
                room.head_commit_id = commit.id
                session.add(room)

                # 清理 Update 表
                delete_stmt = delete(Update).where(Update.room_id == room_id)
                session.exec(delete_stmt)

                # 更新 Snapshot
                delete_snapshot_stmt = delete(Snapshot).where(Snapshot.room_id == room_id)
                session.exec(delete_snapshot_stmt)

                new_snapshot = Snapshot(
                    room_id=room_id,
                    data=doc_data,
                    timestamp=current_time
                )
                session.add(new_snapshot)

                session.commit()

                logger.info("自动提交成功: 房间 %s, 哈希 %s", room_id, commit.hash)
                return True

        except Exception as e:  # pylint: disable=broad-except
            logger.error("自动提交失败: 房间 %s, 错误: %s", room_id, e)
            return False

    def update_room_activity(self, name: str) -> None:
        """更新房间活动时间
        
        Args:
            name: 房间名称
        """
        self._room_last_activity[name] = time.time()

    def get_room_connections(self, name: str) -> int:
        """获取房间连接数
        
        Args:
            name: 房间名称
            
        Returns:
            连接数
        """
        return self._room_connections.get(name, 0)

    async def check_idle_rooms(self, idle_threshold: float = 300.0) -> None:
        """检查并处理空闲房间
        
        Args:
            idle_threshold: 空闲阈值 (秒)
        """
        current_time = time.time()
        for name, last_activity in list(self._room_last_activity.items()):
            idle_time = current_time - last_activity
            if idle_time >= idle_threshold:
                room_id = name.strip("/").split("/")[-1]
                logger.info("房间 '%s' 空闲 %.0f 秒，触发自动提交", room_id, idle_time)
                await self._create_auto_commit(room_id, "Auto save on idle")
                # 更新活动时间避免重复提交
                self._room_last_activity[name] = current_time

    async def close_room(self, name: str) -> None:
        """关闭房间并创建自动提交
        
        Args:
            name: 房间名称
        """
        room_id = name.strip("/").split("/")[-1]

        if name in self._ystores:
            ystore = self._ystores[name]
            try:
                # 停止缓冲区定时器并刷新
                ystore.stop()

                # 创建自动提交
                await self._create_auto_commit(room_id, "Auto save on room close")

                logger.info("房间 '%s' 已关闭并保存", name)
            except Exception as e:  # pylint: disable=broad-except
                logger.error("房间 '%s' 保存失败: %s", name, e)
            del self._ystores[name]

        # 清理连接追踪
        if name in self._room_connections:
            del self._room_connections[name]
        if name in self._room_last_activity:
            del self._room_last_activity[name]

        if name in self.rooms:
            del self.rooms[name]


# 创建带持久化的 WebsocketServer 实例
websocket_server = PersistentWebsocketServer()

# 创建 ASGI 应用，可以作为子应用挂载到 FastAPI
asgi_server = ASGIServer(websocket_server)


async def background_compaction_task():
    """后台任务：定期执行存储优化和空闲房间自动提交

    每5分钟检查空闲房间，触发自动提交。
    """
    idle_check_interval = 300  # 5分钟检查一次空闲
    idle_threshold = 300.0  # 5分钟无活动视为空闲
    last_idle_check = time.time()

    while True:
        await asyncio.sleep(60)  # 每分钟检查一次
        current_time = time.time()

        try:
            # 检查空闲房间
            if current_time - last_idle_check >= idle_check_interval:
                last_idle_check = current_time
                logger.debug("检查空闲房间...")
                await websocket_server.check_idle_rooms(idle_threshold)

        except Exception as e:  # pylint: disable=broad-except
            logger.error("后台任务执行失败: %s", e)
