import threading
import time
from collections.abc import AsyncIterator
from logging import Logger, getLogger
from typing import Callable, Awaitable
from anyio import Lock
from sqlmodel import Session, select
from pycrdt import Doc
from pycrdt.store.base import BaseYStore, YDocNotFound
from src.db.models import Room
from src.db.database import engine
from src.db.models import Commit, Update


class WriteBuffer:
    """线程安全的写入缓冲区"""

    def __init__(
        self,
        flush_callback: Callable[[], None],
        flush_interval: float = 5.0,
        max_size: int = 50,
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

    def flush(self) -> None:
        """立即刷新缓冲区"""
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            if self._buffer:
                self._flush_callback()

    def clear(self) -> None:
        """清空缓冲区（不保存）"""
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            self._buffer.clear()

    def get_and_clear(self) -> list[tuple[bytes, int]]:
        """获取并清空缓冲区"""
        with self._lock:
            # 注意：这里不取消定时器，由调用者决定是否需要刷新
            # 但通常 get_and_clear 是为了刷新，所以逻辑上没问题
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
        except Exception as e: # pylint: disable=broad-except
            self.log.error("房间 %s 刷新缓冲区失败: %s", self.room_id, e)

    async def read(self) -> AsyncIterator[tuple[bytes, bytes, float]]:
        """读取房间的所有数据

        按顺序返回：最新 Commit → 后续 Update → 内存缓冲
        """
        found = False
        self.log.info("[YStore.read] 开始读取房间 %s 的数据", self.room_id)

        async with self.lock:
            with Session(engine) as session:
                # 0. 获取房间信息，查看 HEAD
                room = session.get(Room, self.room_id)
                self.log.info(
                    "[YStore.read] 房间信息: %s, HEAD: %s",
                    room,
                    room.head_commit_id if room else "N/A",
                )

                commit = None
                if room and room.head_commit_id:
                    # 优先使用 HEAD 指向的提交
                    commit = session.get(Commit, room.head_commit_id)

                if not commit:
                    commit_stmt = (
                        select(Commit)
                        .where(Commit.room_id == self.room_id)
                        .order_by(Commit.timestamp.desc())  # pylint: disable=no-member
                        .limit(1)
                    )
                    commit = session.exec(commit_stmt).first()

                if commit:
                    found = True
                    self.log.info(
                        "[YStore.read] 找到 Commit: id=%s, 数据大小=%d bytes, timestamp=%d",
                        commit.id,
                        len(commit.data),
                        commit.timestamp,
                    )
                    yield commit.data, b"", commit.timestamp / 1000.0

                    updates_stmt = (
                        select(Update)
                        .where(Update.room_id == self.room_id)
                        .where(Update.timestamp > commit.timestamp)
                        .order_by(Update.timestamp)
                    )
                else:
                    self.log.warning("[YStore.read] 未找到 Commit，将读取所有 Update")
                    # 没有 Commit，获取所有 Update
                    updates_stmt = (
                        select(Update)
                        .where(Update.room_id == self.room_id)
                        .order_by(Update.timestamp)
                    )

                updates = session.exec(updates_stmt).all()
                self.log.info("[YStore.read] 找到 %d 个 Update", len(updates))
                for update in updates:
                    found = True
                    self.log.info(
                        "[YStore.read] 返回 Update: 数据大小=%d bytes, timestamp=%d",
                        len(update.data),
                        update.timestamp,
                    )
                    yield update.data, b"", update.timestamp / 1000.0

        buffer_data = self._buffer.get_copy()
        self.log.info("[YStore.read] 内存缓冲区: %d 个更新", len(buffer_data))
        for data, timestamp in buffer_data:
            found = True
            yield data, b"", timestamp / 1000.0

        if not found:
            self.log.warning("[YStore.read] 房间 %s 未找到任何数据", self.room_id)
            raise YDocNotFound

        self.log.info("[YStore.read] 房间 %s 数据读取完成", self.room_id)

    async def write(self, data: bytes) -> None:
        """写入一个新的更新到缓冲区"""
        current_time = int(time.time() * 1000)
        should_flush = self._buffer.add(data, current_time)

        if should_flush:
            self._sync_flush()

    def flush(self) -> None:
        """强制刷新缓冲区到数据库"""
        self._buffer.flush()

    def discard(self) -> None:
        """丢弃缓冲区中的更改"""
        self._buffer.clear()

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

    def get_buffer_data(self) -> list[tuple[bytes, int]]:
        """获取并清空缓冲区数据"""
        return self._buffer.get_and_clear()

    def get_buffer_copy(self) -> list[tuple[bytes, int]]:
        """获取缓冲区数据副本"""
        return self._buffer.get_copy()

    def get_current_doc(self) -> Doc:
        """获取当前完整文档状态"""
        ydoc = Doc()

        with Session(engine) as session:
            # 0. 获取房间信息，查看 HEAD

            room = session.get(Room, self.room_id)

            commit = None
            if room and room.head_commit_id:
                # 优先使用 HEAD 指向的提交
                commit = session.get(Commit, room.head_commit_id)

            if not commit:
                # 获取最新 Commit
                commit_stmt = (
                    select(Commit)
                    .where(Commit.room_id == self.room_id)
                    .order_by(Commit.timestamp.desc())  # pylint: disable=no-member
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
