"""模块名称: ystore
主要功能: 基于 SQLModel 的 Yjs 持久化存储

实现自定义 YStore，将 Yjs 文档更新存储到 SQLModel 数据库中，
与其他业务数据统一在同一个数据库文件中。

类似 Git 的设计思路：
- Snapshot: 相当于 Git 的 commit，存储完整状态
- Update: 相当于 Git 的 diff，存储增量变更
- 写入缓冲：累积更新后批量写入，减少数据库交互
- 定期压缩：将多个 Update 合并成一个 Snapshot
"""

import asyncio
import threading
import time
from collections.abc import AsyncIterator
from logging import Logger, getLogger
from typing import Callable, Awaitable

from anyio import Lock
from sqlmodel import Session, select, delete

from pycrdt import Doc
from pycrdt.store.base import BaseYStore, YDocNotFound

from src.db.database import engine
from src.db.models import Snapshot, Update


class WriteBuffer:
    """线程安全的写入缓冲区
    
    用于累积 Yjs 更新，减少数据库写入次数。
    """

    def __init__(
            self,
            flush_callback: Callable[[], None], flush_interval: float = 5.0, max_size: int = 50
            ):
        self._buffer: list[tuple[bytes, int]] = []
        self._lock = threading.Lock()
        self._flush_callback = flush_callback
        self._flush_interval = flush_interval
        self._max_size = max_size
        self._last_flush_time = time.time()
        self._timer: threading.Timer | None = None

    def add(self, data: bytes, timestamp: int) -> bool:
        """添加数据到缓冲区
        
        Returns:
            bool: 是否需要立即刷新
        """
        with self._lock:
            self._buffer.append((data, timestamp))
            should_flush = len(self._buffer) >= self._max_size

            # 取消之前的定时器
            if self._timer:
                self._timer.cancel()

            if should_flush:
                return True

            # 启动新的定时器
            self._timer = threading.Timer(self._flush_interval, self._flush_callback)
            self._timer.daemon = True
            self._timer.start()
            return False

    def get_and_clear(self) -> list[tuple[bytes, int]]:
        """获取并清空缓冲区"""
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            data = self._buffer.copy()
            self._buffer.clear()
            self._last_flush_time = time.time()
            return data

    def get_copy(self) -> list[tuple[bytes, int]]:
        """获取缓冲区副本（不清空）"""
        with self._lock:
            return self._buffer.copy()

    def size(self) -> int:
        """获取缓冲区大小"""
        with self._lock:
            return len(self._buffer)

    def stop(self):
        """停止定时器"""
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None


class SQLModelYStore(BaseYStore):
    """基于 SQLModel 的 YStore 实现
    
    将 Yjs 文档的快照和增量更新存储到 SQLModel 数据库中。
    所有房间数据共享同一个数据库，通过 room_id 字段区分。
    
    设计特点：
    - 统一数据库：与用户、房间等业务数据共用 sync_canvas.db
    - Git 式存储：Snapshot (完整状态) + Update (增量变更)
    - 写入缓冲：在内存中累积更新，定时或达到阈值时批量写入
    - 自动压缩：当 Update 数量超过阈值时自动创建 Snapshot
    """

    # 当 Update 数量超过此值时，触发压缩生成新 Snapshot
    COMPACTION_THRESHOLD = 100

    # 写入缓冲阈值：达到此数量时强制写入
    BUFFER_SIZE_THRESHOLD = 50

    # 写入缓冲时间间隔（秒）：超过此时间后自动写入
    BUFFER_FLUSH_INTERVAL = 5.0

    # 文档 TTL，超过此时间(秒)的历史会被压缩，None 表示不自动压缩
    document_ttl: int | None = None

    def __init__(
        self,
        room_id: str,
        metadata_callback: Callable[[], Awaitable[bytes] | bytes] | None = None,
        log: Logger | None = None,
    ) -> None:
        """初始化 YStore
        
        Args:
            room_id: 房间 ID，用于在数据库中区分不同房间的数据
            metadata_callback: 可选的元数据回调
            log: 可选的日志记录器
        """
        self.room_id = room_id
        self.metadata_callback = metadata_callback
        self.log = log or getLogger(__name__)
        self.lock = Lock()

        # 写入缓冲区
        self._buffer = WriteBuffer(
            flush_callback=self._sync_flush,
            flush_interval=self.BUFFER_FLUSH_INTERVAL,
            max_size=self.BUFFER_SIZE_THRESHOLD,
        )

    def _sync_flush(self):
        """同步刷新缓冲区（由定时器调用）"""
        try:
            buffer_data = self._buffer.get_and_clear()
            if not buffer_data:
                return

            with Session(engine) as session:
                for data, timestamp in buffer_data:
                    update = Update(
                        room_id=self.room_id,
                        data=data,
                        timestamp=timestamp,
                    )
                    session.add(update)
                session.commit()
                self.log.debug("房间 %s 刷新缓冲区：写入 %d 个更新", self.room_id, len(buffer_data))

                # 检查是否需要压缩
                count_stmt = select(Update).where(Update.room_id == self.room_id)
                update_count = len(session.exec(count_stmt).all())

                if update_count >= self.COMPACTION_THRESHOLD:
                    self.log.info("房间 %s 的更新数量达到 %d，触发压缩", self.room_id, update_count)
                    self._compact_sync(session)
        except Exception as e:  # pylint: disable=broad-except
            self.log.error("房间 %s 刷新缓冲区失败: %s", self.room_id, e)

    async def read(self) -> AsyncIterator[tuple[bytes, bytes, float]]:
        """读取房间的所有更新
        
        首先读取最新的 Snapshot，然后读取之后的所有 Update，
        最后返回缓冲区中尚未写入的更新。
        
        Yields:
            (update_data, metadata, timestamp) 元组
            
        Raises:
            YDocNotFound: 房间数据不存在
        """
        found = False

        async with self.lock:
            with Session(engine) as session:
                # 1. 获取最新的 Snapshot
                snapshot_stmt = (
                    select(Snapshot)
                    .where(Snapshot.room_id == self.room_id)
                    .order_by(Snapshot.timestamp.desc())
                    .limit(1)
                )
                snapshot = session.exec(snapshot_stmt).first()

                if snapshot:
                    found = True
                    yield snapshot.data, b"", snapshot.timestamp / 1000.0

                    # 2. 获取 Snapshot 之后的所有 Update
                    updates_stmt = (
                        select(Update)
                        .where(
                            Update.room_id == self.room_id,
                            Update.timestamp > snapshot.timestamp
                        )
                        .order_by(Update.timestamp)
                    )
                else:
                    # 没有 Snapshot，获取所有 Update
                    updates_stmt = (
                        select(Update)
                        .where(Update.room_id == self.room_id)
                        .order_by(Update.timestamp)
                    )

                updates = session.exec(updates_stmt).all()
                for update in updates:
                    found = True
                    yield update.data, b"", update.timestamp / 1000.0

        # 3. 返回缓冲区中的更新
        for data, timestamp in self._buffer.get_copy():
            found = True
            yield data, b"", timestamp / 1000.0

        if not found:
            raise YDocNotFound

    async def write(self, data: bytes) -> None:
        """写入一个新的更新到缓冲区
        
        更新首先存储在内存缓冲区中，满足以下条件之一时写入数据库：
        1. 缓冲区大小达到 BUFFER_SIZE_THRESHOLD
        2. 距离上次写入超过 BUFFER_FLUSH_INTERVAL 秒
        
        Args:
            data: Yjs 更新的二进制数据
        """
        current_time = int(time.time() * 1000)
        should_flush = self._buffer.add(data, current_time)

        if should_flush:
            self._sync_flush()

    def _compact_sync(self, session: Session) -> int:
        """同步压缩更新：将所有 Update 合并为一个 Snapshot
        
        类似 Git 的 gc，将多个小的增量更新合并成一个完整快照。
        
        Args:
            session: 数据库会话
            
        Returns:
            int: 合并的更新数量
        """
        try:
            # 1. 重建完整文档
            ydoc = Doc()

            # 先应用最新的 Snapshot
            snapshot_stmt = (
                select(Snapshot)
                .where(Snapshot.room_id == self.room_id)
                .order_by(Snapshot.timestamp.desc())
                .limit(1)
            )
            snapshot = session.exec(snapshot_stmt).first()
            snapshot_timestamp = 0

            if snapshot:
                ydoc.apply_update(snapshot.data)
                snapshot_timestamp = snapshot.timestamp

            # 应用所有后续的 Update
            updates_stmt = (
                select(Update)
                .where(
                    Update.room_id == self.room_id,
                    Update.timestamp > snapshot_timestamp
                )
                .order_by(Update.timestamp)
            )
            updates = session.exec(updates_stmt).all()

            if not updates and not snapshot:
                return 0

            for update in updates:
                ydoc.apply_update(update.data)

            # 2. 创建新的 Snapshot
            new_snapshot = Snapshot(
                room_id=self.room_id,
                data=ydoc.get_update(),
                timestamp=int(time.time() * 1000),
            )
            session.add(new_snapshot)

            # 3. 删除旧的 Snapshot 和所有 Update
            if snapshot:
                session.delete(snapshot)

            delete_updates_stmt = delete(Update).where(Update.room_id == self.room_id)
            session.exec(delete_updates_stmt)

            session.commit()
            self.log.info("房间 %s 压缩完成，合并了 %d 个更新", self.room_id, len(updates))
            return len(updates)

        except Exception as e:
            self.log.error("房间 %s 压缩失败: %s", self.room_id, e)
            session.rollback()
            raise

    async def create_snapshot(self) -> None:
        """手动创建快照
        
        可以在适当的时机手动调用，比如用户保存、离开房间等。
        首先刷新缓冲区，然后压缩更新。
        """
        # 先刷新缓冲区
        self._sync_flush()

        async with self.lock:
            with Session(engine) as session:
                self._compact_sync(session)

    async def flush(self) -> None:
        """强制刷新缓冲区
        
        在房间关闭或需要确保数据持久化时调用。
        """
        self._sync_flush()

    def stop(self) -> None:
        """停止 YStore，清理资源"""
        self._buffer.stop()
        self._sync_flush()

    def get_buffer_stats(self) -> dict:
        """获取缓冲区统计信息
        
        Returns:
            包含缓冲区状态的字典
        """
        return {
            "buffer_size": self._buffer.size(),
            "room_id": self.room_id,
        }
