"""User persistence models."""

from typing import Any, Dict, Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from src.utils.time import timestamp_seconds


class User(SQLModel, table=True):
    """Persisted user account and permission metadata."""

    __tablename__ = "users"  # type: ignore[assignment]

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
        default_factory=dict,
        sa_column=Column(JSON, default={}),
    )

    created_at: int = Field(default_factory=timestamp_seconds)
    updated_at: int = Field(default_factory=timestamp_seconds)
    last_login_at: Optional[int] = Field(default=None)

    @property
    def is_banned(self) -> bool:
        if self.ban_until is None:
            return False
        return timestamp_seconds() < self.ban_until

    @property
    def is_available(self) -> bool:
        return self.is_active and not self.is_banned

    @property
    def display_name(self) -> str:
        return self.nickname if self.nickname else self.username

    def update_login_time(self) -> None:
        now = timestamp_seconds()
        self.last_login_at = now
        self.updated_at = now

    def ban(self, duration_seconds: int) -> None:
        now = timestamp_seconds()
        self.ban_until = now + duration_seconds
        self.updated_at = now

    def unban(self) -> None:
        self.ban_until = None
        self.updated_at = timestamp_seconds()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "nickname": self.nickname,
            "avatar_url": self.avatar_url,
            "is_admin": self.is_admin,
            "created_at": self.created_at,
        }

