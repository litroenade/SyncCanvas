"""模块名称: models
主要功能: SyncCanvas 核心数据模型定义

数据模型设计：
- Room: 房间基本信息，head_commit_id 指向当前版本 (类似 Git HEAD)
- RoomMember: 房间成员关系
- Commit: 版本提交记录，存储完整的文档状态 (类似 Git Commit)
- Update: 实时增量更新缓冲，定期合并到 Commit
- Stroke: 图形统计记录
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


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
        head_commit_id (int): 当前 HEAD 指向的提交 ID (类似 Git HEAD)
    """

    id: str = Field(primary_key=True, max_length=36)
    name: str = Field(max_length=100)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    password_hash: Optional[str] = Field(default=None, max_length=255)
    is_public: bool = Field(default=True)
    max_users: int = Field(default=10)
    created_at: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp()))
    head_commit_id: Optional[int] = Field(default=None)


class RoomMember(SQLModel, table=True):
    """房间成员模型"""

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str = Field(foreign_key="room.id", index=True, max_length=36)
    user_id: int = Field(foreign_key="user.id", index=True)
    role: str = Field(default="editor", max_length=20)
    joined_at: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp()))


class Commit(SQLModel, table=True):
    """提交模型 (类似 Git Commit)

    存储文档在某个时刻的完整状态，以及提交元信息。
    使用链表结构，每个提交指向其父提交，形成版本历史链。
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str = Field(index=True, max_length=36)
    parent_id: Optional[int] = Field(default=None, index=True)
    author_id: Optional[int] = Field(default=None, foreign_key="user.id")
    author_name: str = Field(default="Anonymous", max_length=100)
    message: str = Field(default="Auto save", max_length=500)
    data: bytes = Field()
    timestamp: int = Field(
        default_factory=lambda: int(datetime.utcnow().timestamp() * 1000)
    )
    hash: str = Field(default="", max_length=7, index=True)


class Update(SQLModel, table=True):
    """增量更新模型 (实时缓冲)

    存储用户实时操作的增量更新，作为临时缓冲。
    当用户提交或离开房间时，这些更新会被合并到新的 Commit 中。
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str = Field(index=True, max_length=36)
    data: bytes = Field()
    timestamp: int = Field(
        default_factory=lambda: int(datetime.utcnow().timestamp() * 1000)
    )


class AgentRun(SQLModel, table=True):
    """Agent 运行记录"""

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str = Field(index=True, max_length=36)
    prompt: str = Field(max_length=2000)
    model: str = Field(default="", max_length=100)
    status: str = Field(default="running", max_length=20)
    message: str = Field(default="", max_length=1000)
    created_at: int = Field(
        default_factory=lambda: int(datetime.utcnow().timestamp() * 1000)
    )
    finished_at: Optional[int] = Field(default=None)


class AgentAction(SQLModel, table=True):
    """Agent 工具调用记录"""

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="agentrun.id", index=True)
    tool: str = Field(max_length=64)
    arguments: dict = Field(default_factory=dict, sa_column=Column(JSON))
    result: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: int = Field(
        default_factory=lambda: int(datetime.utcnow().timestamp() * 1000)
    )
