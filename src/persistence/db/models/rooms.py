"""Room/history persistence models."""

from typing import Optional

from sqlmodel import Field, SQLModel

from src.utils.time import timestamp_ms


class Room(SQLModel, table=True):
    """Collaborative room metadata."""

    id: str = Field(primary_key=True, max_length=36)
    name: str = Field(max_length=100)
    owner_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    password_hash: Optional[str] = Field(default=None, max_length=255)
    is_public: bool = Field(default=True)
    max_users: int = Field(default=10)
    created_at: int = Field(default_factory=timestamp_ms)
    head_commit_id: Optional[int] = Field(default=None)
    elements_count: int = Field(default=0)
    total_contributors: int = Field(default=0)
    last_active_at: Optional[int] = Field(default=None)


class RoomMember(SQLModel, table=True):
    """Room membership metadata."""

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str = Field(foreign_key="room.id", index=True, max_length=36)
    user_id: int = Field(foreign_key="users.id", index=True)
    role: str = Field(default="editor", max_length=20)
    joined_at: int = Field(default_factory=timestamp_ms)


class Commit(SQLModel, table=True):
    """Snapshot commit stored for room history and recovery."""

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str = Field(index=True, max_length=36)
    parent_id: Optional[int] = Field(default=None, index=True)
    author_id: Optional[int] = Field(default=None, foreign_key="users.id")
    author_name: str = Field(default="Anonymous", max_length=100)
    message: str = Field(default="Auto save", max_length=500)
    data: bytes = Field()
    timestamp: int = Field(default_factory=timestamp_ms)
    hash: str = Field(default="", max_length=7, index=True)


class Update(SQLModel, table=True):
    """Incremental realtime updates stored between commits."""

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str = Field(index=True, max_length=36)
    data: bytes = Field()
    timestamp: int = Field(default_factory=timestamp_ms)

