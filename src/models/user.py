"""模块名称: user
主要功能: 用户数据模型定义
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """用户模型

    存储系统用户的基本信息和认证数据。

    Attributes:
        id (int): 主键，自增
        username (str): 用户名，唯一索引，用于登录
        password_hash (str): 密码哈希 (bcrypt)
        display_name (str): 显示名称，用于 UI 展示
        avatar_url (str): 头像 URL
        created_at (int): 创建时间戳 (秒)
        last_active_at (int): 最后活跃时间戳 (秒)
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=50)
    password_hash: str = Field(max_length=255)
    display_name: Optional[str] = Field(default=None, max_length=100)
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    created_at: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp()))
    last_active_at: Optional[int] = Field(default=None)
