"""模块名称: ystore
主要功能: 基于 SQLModel 的 Yjs 持久化存储

实现自定义 YStore，将 Yjs 文档更新存储到 SQLModel 数据库中。
使用 Commit 表存储版本历史，Update 表作为实时缓冲。

数据流：
1. 用户操作 → Yjs → WebSocket → YStore.write() → Update 表 (缓冲)
2. 提交时 → 合并 Update → 创建 Commit → 清空 Update
3. 恢复时 → 读取最新 Commit + 后续 Update
"""

import threading
import time
from collections.abc import AsyncIterator
from logging import Logger, getLogger
from typing import Callable, Awaitable

from anyio import Lock
from sqlmodel import Session, select

from pycrdt import Doc
from pycrdt.store.base import BaseYStore, YDocNotFound

from src.db.database import engine
from src.db.models import Commit, Update


class WriteBuffer:
    """线程安全的写入缓冲区"""

    def __init__(
            self,
            flush_callback: Callable[[], None],
            flush_interval: float = 5.0,
            max_size: int = 50
    ):
        self._buffer: list[tuple[bytes, int]] = []
        self._lock = threading.Lock()
        self._flush_callback = flush_callback
        self._flush_interval = flush_interval
        self._max_size = max_size
        self._timer: threading.Timer | None = None

    def add(self, data: bytes, timestamp: int) -> bool:
        """添加数据到缓冲区，返回是否需要立即刷新"""
        with self._lock:
            self._buffer.append((data, timestamp))
            should_flush = len(self._buffer) >= self._max_size

            if self._timer:
                self._timer.cancel()

            if should_flush:
                return True

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

    数据恢复流程：
    1. 从最新的 Commit 读取完整状态
    2. 应用 Commit 之后的所有 Update
    3. 应用内存缓冲区中的 Update
    """

    # 写入缓冲配置
    BUFFER_SIZE_THRESHOLD = 50
    BUFFER_FLUSH_INTERVAL = 5.0

    document_ttl: int | None = None

    def __init__(
        self,
        room_id: str,
        metadata_callback: Callable[[], Awaitable[bytes] | bytes] | None = None,
        log: Logger | None = None,
    ) -> None:
        self.room_id = room_id
        self.metadata_callback = metadata_callback
        self.log = log or getLogger(__name__)
        self.lock = Lock()

        self._buffer = WriteBuffer(
            flush_callback=self._sync_flush,
            flush_interval=self.BUFFER_FLUSH_INTERVAL,
            max_size=self.BUFFER_SIZE_THRESHOLD,
        )

    def _sync_flush(self):
        """同步刷新缓冲区到数据库"""
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
                # 使用 DEBUG 级别，避免刷屏
                self.log.debug("房间 %s: 写入 %d 个更新到缓冲", self.room_id, len(buffer_data))
        except Exception as e:
            self.log.error("房间 %s 刷新缓冲区失败: %s", self.room_id, e)

    async def read(self) -> AsyncIterator[tuple[bytes, bytes, float]]:
        """读取房间的所有数据
        
        按顺序返回：最新 Commit → 后续 Update → 内存缓冲
        """
        found = False

        async with self.lock:
            with Session(engine) as session:
                # 1. 获取最新的 Commit
                commit_stmt = (
                    select(Commit)
                    .where(Commit.room_id == self.room_id)
                    .order_by(Commit.timestamp.desc())
                    .limit(1)
                )
                commit = session.exec(commit_stmt).first()

                if commit:
                    found = True
                    yield commit.data, b"", commit.timestamp / 1000.0

                    # 2. 获取 Commit 之后的所有 Update
                    updates_stmt = (
                        select(Update)
                        .where(Update.room_id == self.room_id)
                        .where(Update.timestamp > commit.timestamp)
                        .order_by(Update.timestamp)
                    )
                else:
                    # 没有 Commit，获取所有 Update
                    updates_stmt = (
                        select(Update)
                        .where(Update.room_id == self.room_id)
                        .order_by(Update.timestamp)
                    )

                updates = session.exec(updates_stmt).all()
                for update in updates:
                    found = True
                    yield update.data, b"", update.timestamp / 1000.0

        # 3. 返回内存缓冲区中的更新
        for data, timestamp in self._buffer.get_copy():
            found = True
            yield data, b"", timestamp / 1000.0

        if not found:
            raise YDocNotFound

    async def write(self, data: bytes) -> None:
        """写入一个新的更新到缓冲区"""
        current_time = int(time.time() * 1000)
        should_flush = self._buffer.add(data, current_time)

        if should_flush:
            self._sync_flush()

    def stop(self) -> None:
        """停止 YStore，清理资源"""
        self._buffer.stop()
        self._sync_flush()

    def get_buffer_stats(self) -> dict:
        """获取缓冲区统计信息"""
        return {
            "buffer_size": self._buffer.size(),
            "room_id": self.room_id,
        }

    def get_current_doc(self) -> Doc:
        """获取当前完整文档状态"""
        ydoc = Doc()
        
        with Session(engine) as session:
            # 获取最新 Commit
            commit_stmt = (
                select(Commit)
                .where(Commit.room_id == self.room_id)
                .order_by(Commit.timestamp.desc())
                .limit(1)
            )
            commit = session.exec(commit_stmt).first()

            if commit:
                ydoc.apply_update(commit.data)
                # 获取后续 Update
                updates_stmt = (
                    select(Update)
                    .where(Update.room_id == self.room_id)
                    .where(Update.timestamp > commit.timestamp)
                    .order_by(Update.timestamp)
                )
            else:
                updates_stmt = (
                    select(Update)
                    .where(Update.room_id == self.room_id)
                    .order_by(Update.timestamp)
                )

            updates = session.exec(updates_stmt).all()
            for update in updates:
                ydoc.apply_update(update.data)

        # 应用内存缓冲
        for data, _ in self._buffer.get_copy():
            ydoc.apply_update(data)

        return ydoc
