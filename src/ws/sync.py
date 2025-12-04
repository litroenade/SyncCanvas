"""模块名称: sync
主要功能: 基于 pycrdt_websocket 的实时同步功能，带持久化存储

使用 pycrdt_websocket 模块实现与 Yjs 客户端的完全兼容同步。
通过自定义 SQLModelYStore 实现数据持久化，与业务数据统一存储。
支持用户连接追踪和自动提交功能。
"""

import asyncio
import hashlib
import time
from functools import partial
from typing import Any

from anyio import get_cancelled_exc_class
from pycrdt import Channel, Doc
from pycrdt.websocket import WebsocketServer, ASGIServer, YRoom
from sqlmodel import Session, select, delete

from src.db.ystore import SQLModelYStore
from src.db.database import engine
from src.db.models import Commit, Update, Room
from src.logger import get_logger

logger = get_logger(__name__)


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

        # 增加连接计数（在连接建立时）
        self._room_connections[name] = self._room_connections.get(name, 0) + 1
        self._room_last_activity[name] = time.time()
        logger.debug(f"房间 '{name}' 新连接，当前连接数: {self._room_connections[name]}")

        try:
            # 调用父类的 serve 方法
            await super().serve(websocket)
        except get_cancelled_exc_class():
            # 客户端正常断开，不需要处理
            logger.debug(f"客户端主动取消: {name}")
        except Exception as eg:
            # 展开异常组，判断是否存在真实错误
            unhandled = [
                exc for exc in self._iter_exceptions(eg)
                if not self._is_disconnect_error(exc)
            ]
            if unhandled:
                for exc in unhandled:
                    logger.exception(f"WebSocket 服务异常 [{name}]: {exc}")
            else:
                logger.debug(f"客户端断开连接: {name}")
        except Exception as exception:  # pylint: disable=broad-except
            if not self._is_disconnect_error(exception):
                logger.exception(f"WebSocket 异常 [{name}]")
            else:
                logger.debug(f"客户端断开连接: {name}")
        finally:
            # 连接断开后处理
            try:
                await self._on_client_disconnect(name)
            except asyncio.CancelledError:
                # 服务器关闭时忽略
                pass
            except Exception as e:
                logger.debug(f"断开处理异常: {e}")

    def _is_disconnect_error(self, exception: Exception) -> bool:
        """检查是否是断开连接相关的错误"""
        error_str = str(exception).lower()
        disconnect_keywords = [
            'clientdisconnected', 
            'connectionclosed', 
            'no close frame',
            'websocket.close',
            'websocket.send',
            'response already completed',
            'unexpected asgi message'
        ]
        return any(keyword in error_str for keyword in disconnect_keywords)

    def _iter_exceptions(
            self,
            exception: BaseException | Exception
            ) -> list[BaseException]:
        """展开 BaseExceptionGroup，返回所有底层异常"""
        if isinstance(exception, Exception):
            exceptions: list[BaseException] = []
            for inner in exception.exceptions:
                exceptions.extend(self._iter_exceptions(inner))
            return exceptions
        return [exception]

    async def get_room(self, name: str) -> YRoom:
        """获取或创建房间，带持久化存储
        
        Args:
            name: 房间名称 (WebSocket)
            
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
            logger.info(f"创建房间 '{name}'，房间 ID: {room_id}")

        return self.rooms[name]

    async def _on_client_disconnect(self, name: str) -> None:
        """处理客户端断开连接
        
        Args:
            name: 房间名称
        """
        if name in self._room_connections:
            self._room_connections[name] = max(0, self._room_connections[name] - 1)
            logger.debug(f"房间 '{name}' 断开连接，剩余连接数: {self._room_connections[name]}")

            # 如果是最后一个用户离开，延迟检查后再触发自动提交
            # 这样可以避免因为短暂的重连导致误判
            if self._room_connections[name] == 0:
                # 延迟 2 秒再检查，给重连留出时间
                await asyncio.sleep(2.0)

                # 再次检查连接数，如果仍然为 0 才触发自动提交
                if self._room_connections.get(name, 0) == 0:
                    await self._auto_commit_on_last_leave(name)

    async def _auto_commit_on_last_leave(self, name: str) -> None:
        """最后一个用户离开时自动提交
        
        Args:
            name: 房间名称
        """
        try:
            room_id = name.strip("/").split("/")[-1]
            logger.info(f"房间 '{room_id}' 最后用户离开，触发自动提交")
            # 先刷新缓冲区
            if name in self._ystores:
                ystore = self._ystores[name]
                ystore.stop()

            # 等待一小段时间确保数据已写入
            await asyncio.sleep(0.5)

            # 创建自动提交
            await self._create_auto_commit(room_id, "Auto save on disconnect")

        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"房间 '{name}' 自动提交失败: {e}")

    async def _create_auto_commit(self, room_id: str, message: str) -> bool:
        """创建自动提交（内联实现，避免循环依赖）"""
        try:
            with Session(engine) as session:
                room = session.exec(select(Room).where(Room.id == room_id)).first()
                if not room:
                    return False

                # 获取最新提交
                latest = session.exec(
                    select(Commit)
                    .where(Commit.room_id == room_id)
                    .order_by(Commit.timestamp.desc())
                    .limit(1)
                ).first()

                # 获取增量更新
                if latest:
                    updates = session.exec(
                        select(Update)
                        .where(Update.room_id == room_id)
                        .where(Update.timestamp > latest.timestamp)
                        .order_by(Update.timestamp)
                    ).all()
                else:
                    updates = session.exec(
                        select(Update)
                        .where(Update.room_id == room_id)
                        .order_by(Update.timestamp)
                    ).all()

                if not updates:
                    return False

                # 构建文档
                ydoc = Doc()
                if latest:
                    ydoc.apply_update(latest.data)
                for u in updates:
                    ydoc.apply_update(u.data)

                doc_data = ydoc.get_update()
                current_time = int(time.time() * 1000)

                # 生成哈希
                hash_input = f"{room_id}:{current_time}:{len(doc_data)}"
                commit_hash = hashlib.sha1(hash_input.encode()).hexdigest()[:7]

                commit = Commit(
                    room_id=room_id,
                    parent_id=room.head_commit_id,
                    author_name="System",
                    message=message,
                    data=doc_data,
                    timestamp=current_time,
                    hash=commit_hash,
                )
                session.add(commit)
                session.flush()

                room.head_commit_id = commit.id
                session.add(room)

                # 清理 updates
                session.exec(delete(Update).where(Update.room_id == room_id))
                session.commit()

                logger.info(f"自动提交: 房间 {room_id}, 哈希 {commit_hash}")
                return True

        except Exception as e:
            logger.debug(f"自动提交跳过: 房间 {room_id}, 原因: {e}")
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
                logger.info(f"房间 '{room_id}' 空闲 {idle_time:.0f} 秒，触发自动提交")
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

                logger.info(f"房间 '{name}' 已关闭并保存")
            except Exception as e:  # pylint: disable=broad-except
                logger.error(f"房间 '{name}' 保存失败: {e}")
            del self._ystores[name]

        # 清理连接追踪
        if name in self._room_connections:
            del self._room_connections[name]
        if name in self._room_last_activity:
            del self._room_last_activity[name]

        if name in self.rooms:
            del self.rooms[name]

    async def flush_room(self, room_id: str) -> None:
        """强制刷新房间数据到数据库
        
        Args:
            room_id: 房间 ID
        """
        # 查找房间名称
        target_name = None
        for name in self.rooms:
            if name.endswith(f"/{room_id}") or name == room_id:
                target_name = name
                break

        if target_name and target_name in self._ystores:
            self._ystores[target_name].flush()
            logger.debug(f"房间 {room_id} 已强制刷新")

    async def evict_room(self, room_id: str, discard_changes: bool = False) -> None:
        """从内存中移除房间（用于强制重载）
        
        Args:
            room_id: 房间 ID
            discard_changes: 是否丢弃未保存的更改
        """
        # 查找房间名称
        target_name = None
        for name in self.rooms:
            if name.endswith(f"/{room_id}") or name == room_id:
                target_name = name
                break

        if not target_name:
            return

        if target_name in self._ystores:
            ystore = self._ystores[target_name]
            if discard_changes:
                ystore.discard()
            # stop 会触发 flush，但如果已经 discard 了，就只会 flush 空缓冲
            ystore.stop()
            del self._ystores[target_name]

        if target_name in self.rooms:
            del self.rooms[target_name]

        # 清理统计信息
        self._room_connections.pop(target_name, None)
        self._room_last_activity.pop(target_name, None)

        logger.info(f"房间 {room_id} 已从内存移除 (discard={discard_changes})")


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
            logger.error(f"后台任务执行失败: {e}")