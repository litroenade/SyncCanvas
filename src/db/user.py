"""模块名称: user
主要功能: 用户数据模型

提供用户模型和相关属性方法。
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """用户模型

    存储用户账号信息和权限控制。

    Attributes:
        id (int): 用户 ID (主键)
        username (str): 用户名 (唯一)
        password_hash (str): 密码哈希
        nickname (str): 昵称
        avatar_url (str): 头像 URL
        is_active (bool): 是否激活
        is_admin (bool): 是否管理员
        perm_level (int): 权限等级 (0=普通, 1=高级, 9=管理员)
        ban_until (int): 封禁截止时间戳 (秒)；None 表示未封禁
        ext_data (dict): 扩展数据 (JSON)
        created_at (int): 创建时间戳 (秒)
        updated_at (int): 更新时间戳 (秒)
        last_login_at (int): 最后登录时间戳 (秒)
    """

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=64, unique=True, index=True)
    password_hash: str = Field(max_length=255)
    nickname: str = Field(default="", max_length=64)
    avatar_url: str = Field(default="", max_length=500)

    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    perm_level: int = Field(default=0)

    ban_until: Optional[int] = Field(default=None)
    ext_data: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, default={})
    )

    created_at: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp()))
    updated_at: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp()))
    last_login_at: Optional[int] = Field(default=None)

    @property
    def is_banned(self) -> bool:
        """检查用户是否被封禁

        Returns:
            bool: 是否被封禁
        """
        if self.ban_until is None:
            return False
        now = int(datetime.utcnow().timestamp())
        return now < self.ban_until

    @property
    def is_available(self) -> bool:
        """检查用户是否可用 (激活且未封禁)

        Returns:
            bool: 是否可用
        """
        return self.is_active and not self.is_banned

    @property
    def display_name(self) -> str:
        """获取显示名称

        优先返回昵称；若无昵称则返回用户名。

        Returns:
            str: 显示名称
        """
        return self.nickname if self.nickname else self.username

    def update_login_time(self) -> None:
        """更新最后登录时间"""
        self.last_login_at = int(datetime.utcnow().timestamp())
        self.updated_at = int(datetime.utcnow().timestamp())

    def ban(self, duration_seconds: int) -> None:
        """封禁用户

        Args:
            duration_seconds: 封禁时长 (秒)
        """
        now = int(datetime.utcnow().timestamp())
        self.ban_until = now + duration_seconds
        self.updated_at = now

    def unban(self) -> None:
        """解除封禁"""
        self.ban_until = None
        self.updated_at = int(datetime.utcnow().timestamp())

    def to_public_dict(self) -> dict:
        """转换为公开信息字典 (不含敏感信息)

        Returns:
            dict: 公开用户信息
        """
        return {
            "id": self.id,
            "username": self.username,
            "nickname": self.nickname,
            "avatar_url": self.avatar_url,
            "is_admin": self.is_admin,
            "created_at": self.created_at,
        }
