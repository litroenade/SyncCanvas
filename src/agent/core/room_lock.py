from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Set

from src.logger import get_logger

logger = get_logger(__name__)


class RoomLockManager:
    """房间级别的并发锁管理器

    防止同一房间同时有多个 Agent 操作，避免元素冲突。

    Attributes:
        _locks: 房间 ID 到锁对象的映射
        _active_rooms: 当前活跃的房间 ID 集合
    """

    _locks: Dict[str, asyncio.Lock] = {}
    _active_rooms: Set[str] = set()

    @classmethod
    def get_lock(cls, room_id: str) -> asyncio.Lock:
        """获取房间锁

        Args:
            room_id: 房间 ID

        Returns:
            asyncio.Lock: 对应房间的锁对象
        """
        if room_id not in cls._locks:
            cls._locks[room_id] = asyncio.Lock()
        return cls._locks[room_id]

    @classmethod
    @asynccontextmanager
    async def acquire(cls, room_id: str, timeout: float = 30.0):
        """获取房间锁的上下文管理器

        Args:
            room_id: 房间 ID
            timeout: 获取锁的超时时间

        Raises:
            TimeoutError: 获取锁超时
            RuntimeError: 房间正忙
        """
        lock = cls.get_lock(room_id)

        try:
            acquired = await asyncio.wait_for(lock.acquire(), timeout=timeout)
            if not acquired:
                raise RuntimeError(f"房间 {room_id} 正忙，请稍后再试")

            cls._active_rooms.add(room_id)
            logger.debug("获取房间锁: %s", room_id)

            yield

        except asyncio.TimeoutError as exc:
            raise TimeoutError(f"获取房间 {room_id} 的锁超时") from exc
        finally:
            if room_id in cls._active_rooms:
                cls._active_rooms.discard(room_id)
            if lock.locked():
                lock.release()
                logger.debug("释放房间锁: %s", room_id)

    @classmethod
    def is_room_busy(cls, room_id: str) -> bool:
        """检查房间是否正忙

        Args:
            room_id: 房间 ID

        Returns:
            bool: 房间是否正忙
        """
        return room_id in cls._active_rooms

    @classmethod
    def get_active_rooms(cls) -> list:
        """获取所有活跃房间列表

        Returns:
            list: 活跃房间 ID 列表
        """
        return list(cls._active_rooms)
