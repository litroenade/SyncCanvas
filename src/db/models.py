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
        elements_count (int): 当前画布元素数量
        total_contributors (int): 历史贡献者总数
        last_active_at (int): 最后活跃时间戳 (秒)
    """

    id: str = Field(primary_key=True, max_length=36)
    name: str = Field(max_length=100)
    owner_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    password_hash: Optional[str] = Field(default=None, max_length=255)
    is_public: bool = Field(default=True)
    max_users: int = Field(default=10)
    created_at: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp()))
    head_commit_id: Optional[int] = Field(default=None)
    # 房间统计信息
    elements_count: int = Field(default=0)
    total_contributors: int = Field(default=0)
    last_active_at: Optional[int] = Field(default=None)


class RoomMember(SQLModel, table=True):
    """房间成员模型"""

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str = Field(foreign_key="room.id", index=True, max_length=36)
    user_id: int = Field(foreign_key="users.id", index=True)
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
    author_id: Optional[int] = Field(default=None, foreign_key="users.id")
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


class Library(SQLModel, table=True):
    """素材库模型

    存储导入的 Excalidraw 素材库元信息。

    Attributes:
        id: 素材库唯一标识
        name: 素材库名称
        description: 素材库描述
        source: 来源 (local/remote URL)
        version: 版本号
        created_at: 导入时间戳
    """

    id: str = Field(primary_key=True, max_length=36)
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=500)
    source: str = Field(default="local", max_length=255)
    version: int = Field(default=1)
    created_at: int = Field(
        default_factory=lambda: int(datetime.utcnow().timestamp() * 1000)
    )


class LibraryItem(SQLModel, table=True):
    """素材库项模型

    存储素材库中的单个素材项及其向量表示。

    Attributes:
        id: 素材项唯一标识
        library_id: 所属素材库 ID
        name: 素材项名称
        description: 素材描述 (用于搜索)
        tags: 标签 JSON 数组
        elements: Excalidraw 元素 JSON 数组
        embedding: 向量表示 (序列化的 numpy 数组)
        created_at: 创建时间戳
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    library_id: str = Field(foreign_key="library.id", index=True, max_length=36)
    item_id: str = Field(max_length=64, index=True)  # 原始素材项 ID
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=1000)
    tags: list = Field(default_factory=list, sa_column=Column(JSON))
    elements: list = Field(default_factory=list, sa_column=Column(JSON))
    embedding: Optional[bytes] = Field(default=None)  # numpy array 序列化
    created_at: int = Field(
        default_factory=lambda: int(datetime.utcnow().timestamp() * 1000)
    )

