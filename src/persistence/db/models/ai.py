"""AI persistence models."""

from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from src.utils.time import timestamp_ms


class AgentRun(SQLModel, table=True):
    """Agent execution record."""

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str = Field(index=True, max_length=36)
    prompt: str = Field(max_length=2000)
    model: str = Field(default="", max_length=100)
    status: str = Field(default="running", max_length=20)
    message: str = Field(default="", max_length=1000)
    created_at: int = Field(default_factory=timestamp_ms)
    finished_at: Optional[int] = Field(default=None)


class AgentAction(SQLModel, table=True):
    """Tool call record captured during one agent run."""

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="agentrun.id", index=True)
    tool: str = Field(max_length=64)
    arguments: dict = Field(default_factory=dict, sa_column=Column(JSON))
    result: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: int = Field(default_factory=timestamp_ms)


class AgentRequest(SQLModel, table=True):
    """Idempotent AI request ledger for replay/rollback tracing."""

    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: str = Field(index=True, max_length=64)
    room_id: str = Field(index=True, max_length=36)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    idempotency_key: str = Field(index=True, unique=True, max_length=128)
    status: str = Field(default="processing", max_length=20)
    source: str = Field(default="api", max_length=16)
    response: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    error: Optional[str] = Field(default=None, max_length=1000)
    run_id: Optional[int] = Field(default=None, foreign_key="agentrun.id")
    explain_requested: bool = Field(default=False)
    timeout_ms: Optional[int] = Field(default=None)
    created_at: int = Field(default_factory=timestamp_ms)
    updated_at: int = Field(default_factory=timestamp_ms)


class Conversation(SQLModel, table=True):
    """Conversation thread for the AI sidebar."""

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: str = Field(index=True, max_length=36)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    title: str = Field(default="New conversation", max_length=100)
    mode: str = Field(default="planning", max_length=20)
    is_active: bool = Field(default=True)
    message_count: int = Field(default=0)
    created_at: int = Field(default_factory=timestamp_ms)
    updated_at: int = Field(default_factory=timestamp_ms)


class AgentMessage(SQLModel, table=True):
    """Persisted chat message inside one conversation."""

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversation.id", index=True)
    run_id: Optional[int] = Field(default=None, foreign_key="agentrun.id", index=True)
    role: str = Field(max_length=20)
    content: str = Field(max_length=10000)
    extra_data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: int = Field(default_factory=timestamp_ms)

