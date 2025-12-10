"""包名称: db
功能说明: 数据库模块，提供数据库连接、模型定义、CRUD 操作和 Yjs 持久化存储

包含模块：
- database: 数据库引擎和会话管理
- models: 核心数据模型 (Room, Commit, Update, AgentRun 等)
- user: 用户模型
- base: 模型基类和时间工具
- repository: Repository 层抽象
- crud: 传统 CRUD 函数 (兼容)
- ystore: Yjs 持久化存储
"""

from .database import engine, init_db, get_session
from .models import Room, RoomMember, Update, Commit, AgentRun, AgentAction
from .user import User
from .base import BaseDBMixin, now_timestamp, now_timestamp_ms
from .repository import (
    room_repo,
    room_member_repo,
    commit_repo,
    update_repo,
    agent_run_repo,
    agent_action_repo,
)
from .ystore import SQLModelYStore

__all__ = [
    # 数据库
    "engine",
    "init_db",
    "get_session",
    # 模型
    "Room",
    "RoomMember",
    "Update",
    "Commit",
    "AgentRun",
    "AgentAction",
    "User",
    # 基类
    "BaseDBMixin",
    "now_timestamp",
    "now_timestamp_ms",
    # Repository
    "room_repo",
    "room_member_repo",
    "commit_repo",
    "update_repo",
    "agent_run_repo",
    "agent_action_repo",
    # 存储
    "SQLModelYStore",
]
