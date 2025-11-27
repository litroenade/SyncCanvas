"""模块名称: user
主要功能: 用户数据模型定义
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """用户模型"""

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=50)
    password_hash: str = Field(max_length=255)
    created_at: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp()))
