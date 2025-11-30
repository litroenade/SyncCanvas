"""模块名称: models
主要功能: SyncCanvas 核心数据模型定义
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, JSON, Column


class Room(SQLModel, table=True):
    """房间模型

    存储协作房间的基本信息和访问控制。

    Attributes:
        id (str): 房间唯一标识 (UUID)
        name (str): 房间名称
        owner_id (int): 创建者用户 ID
        password_hash (str): 房间密码哈希，None 表示无密码
        is_public (bool): 是否公开可见
        max_users (int): 最大用户数
        created_at (int): 创建时间戳 (秒)
    """

    id: str = Field(primary_key=True, max_length=36)
    name: str = Field(max_length=100)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    password_hash: Optional[str] = Field(default=None, max_length=255)
    is_public: bool = Field(default=True)
    max_users: int = Field(default=10)
    created_at: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp()))


class RoomMember(SQLModel, table=True):
    """房间成员模型

    存储用户与房间的关联关系。

    Attributes:
        id (int): 主键 ID
        room_id (str): 房间 ID
        user_id (int): 用户 ID
        role (str): 角色: owner/editor/viewer
        joined_at (int): 加入时间戳 (秒)
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str = Field(foreign_key="room.id", index=True, max_length=36)
    user_id: int = Field(foreign_key="user.id", index=True)
    role: str = Field(default="editor", max_length=20)
    joined_at: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp()))


class Stroke(SQLModel, table=True):
    """笔画/图形模型

    存储每个图形的完整数据，用于历史追溯和统计。

    Attributes:
        id (int): 主键 ID
        room_id (str): 所属房间 ID
        user_id (int): 创建者用户 ID
        shape_id (str): 图形 UUID (对应 Yjs 中的 ID)
        shape_type (str): 图形类型 (rect/circle/text/arrow/line/freedraw/image)
        shape_data (dict): 图形完整数据 (JSON)
        created_at (int): 创建时间戳 (毫秒)
        updated_at (int): 最后更新时间戳 (毫秒)
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str = Field(foreign_key="room.id", index=True, max_length=36)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    shape_id: str = Field(index=True, max_length=36)
    shape_type: str = Field(max_length=20)
    shape_data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp() * 1000))
    updated_at: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp() * 1000))


class Snapshot(SQLModel, table=True):
    """快照模型

    存储文档在某个时刻的完整二进制状态。

    Attributes:
        id (int): 主键 ID
        room_id (str): 所属房间 ID
        data (bytes): 文档状态的二进制数据
        timestamp (int): 快照时间戳 (毫秒)
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str = Field(index=True, max_length=36)
    data: bytes = Field()
    timestamp: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp() * 1000))


class Update(SQLModel, table=True):
    """增量更新模型

    存储自上次快照以来所有的细碎更新。

    Attributes:
        id (int): 主键 ID
        room_id (str): 所属房间 ID
        data (bytes): 更新的二进制数据
        timestamp (int): 更新时间戳 (毫秒)
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str = Field(index=True, max_length=36)
    data: bytes = Field()
    timestamp: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp() * 1000))
