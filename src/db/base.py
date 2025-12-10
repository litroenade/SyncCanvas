"""模块名称: base
主要功能: 数据库模型基类

提供通用的模型方法和时间处理工具。

@Time: 2025-12-10
@Author: Yang208115
@File: base.py
"""

from datetime import datetime
from typing import Any, Dict, Optional, Type, TypeVar

from sqlmodel import Session, SQLModel, select

T = TypeVar("T", bound="BaseDBMixin")


class BaseDBMixin:
    """数据库模型通用 Mixin

    提供通用的数据库操作方法，可被模型类继承使用。
    注意：此类需要与 SQLModel 一起使用。

    Example:
        ```python
        class Room(SQLModel, BaseDBMixin, table=True):
            id: str = Field(primary_key=True)
            name: str

        # 使用 Mixin 方法
        room = Room.get_by_id(session, "room-123")
        all_rooms = Room.get_all(session, limit=10)
        room.save(session)
        ```
    """

    @classmethod
    def get_by_id(cls: Type[T], session: Session, id: Any) -> Optional[T]:
        """根据 ID 获取记录

        Args:
            session: 数据库会话
            id: 主键 ID

        Returns:
            模型实例；不存在返回 None
        """
        return session.get(cls, id)

    @classmethod
    def get_all(
        cls: Type[T],
        session: Session,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """获取所有记录

        Args:
            session: 数据库会话
            limit: 最大返回数量
            offset: 偏移量

        Returns:
            模型实例列表
        """
        statement = select(cls).offset(offset).limit(limit)
        return list(session.exec(statement))

    @classmethod
    def get_or_none(cls: Type[T], session: Session, **kwargs) -> Optional[T]:
        """根据条件获取单条记录

        Args:
            session: 数据库会话
            **kwargs: 查询条件

        Returns:
            模型实例；不存在返回 None
        """
        statement = select(cls)
        for key, value in kwargs.items():
            statement = statement.where(getattr(cls, key) == value)
        return session.exec(statement).first()

    def save(self: T, session: Session) -> T:
        """保存记录 (新增或更新)

        Args:
            session: 数据库会话

        Returns:
            保存后的模型实例
        """
        session.add(self)
        session.commit()
        session.refresh(self)
        return self

    def delete(self, session: Session) -> bool:
        """删除记录

        Args:
            session: 数据库会话

        Returns:
            是否删除成功
        """
        session.delete(self)
        session.commit()
        return True

    def to_dict(self, exclude: set = None) -> Dict[str, Any]:
        """转换为字典

        Args:
            exclude: 要排除的字段集合

        Returns:
            字典表示
        """
        exclude = exclude or set()
        data = {}
        for key, value in self.__dict__.items():
            if key.startswith("_") or key in exclude:
                continue
            data[key] = value
        return data


# ==================== 时间工具 ====================


def now_timestamp() -> int:
    """获取当前 UTC 时间戳 (秒)

    Returns:
        int: Unix 时间戳
    """
    return int(datetime.utcnow().timestamp())


def now_timestamp_ms() -> int:
    """获取当前 UTC 时间戳 (毫秒)

    Returns:
        int: Unix 时间戳 (毫秒)
    """
    return int(datetime.utcnow().timestamp() * 1000)


def timestamp_to_datetime(ts: int, is_ms: bool = False) -> datetime:
    """时间戳转 datetime

    Args:
        ts: Unix 时间戳
        is_ms: 是否为毫秒时间戳

    Returns:
        datetime: 日期时间对象
    """
    if is_ms:
        ts = ts // 1000
    return datetime.utcfromtimestamp(ts)


def format_timestamp(
    ts: int, is_ms: bool = False, fmt: str = "%Y-%m-%d %H:%M:%S"
) -> str:
    """格式化时间戳

    Args:
        ts: Unix 时间戳
        is_ms: 是否为毫秒时间戳
        fmt: 格式化字符串

    Returns:
        str: 格式化后的时间字符串
    """
    dt = timestamp_to_datetime(ts, is_ms)
    return dt.strftime(fmt)
