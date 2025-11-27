"""模块名称: models
主要功能: SyncCanvas 核心数据模型定义
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Room(SQLModel, table=True):
    """房间模型

    存储协作房间的基本信息。

    Attributes:
        id (str): 房间唯一标识 (UUID)
        name (str): 房间名称
        created_at (int): 创建时间戳（秒）
    """

    id: str = Field(primary_key=True, max_length=36)  # UUID
    name: str = Field(max_length=100)
    created_at: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp()))


class Snapshot(SQLModel, table=True):
    """快照模型

    存储文档在某个时刻的完整二进制状态。

    Attributes:
        id (int): 主键 ID
        room_id (str): 所属房间 ID
        data (bytes): 文档状态的二进制数据
        timestamp (int): 快照时间戳（毫秒）
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str = Field(index=True, max_length=36)
    data: bytes = Field()  # doc.get_state() 的结果
    timestamp: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp() * 1000))


class Update(SQLModel, table=True):
    """增量更新模型

    存储自上次快照以来所有的细碎更新。

    Attributes:
        id (int): 主键 ID
        room_id (str): 所属房间 ID
        data (bytes): 更新的二进制数据
        timestamp (int): 更新时间戳（毫秒）
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str = Field(index=True, max_length=36)
    data: bytes = Field()  # 单个 Update 二进制流
    timestamp: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp() * 1000))
