"""AI domain models."""

from dataclasses import dataclass
from typing import Literal


ConversationMode = Literal["agent", "planning", "mermaid"]


@dataclass(slots=True)
class AIRequestContext:
    room_id: str
    prompt: str
    mode: ConversationMode = "agent"
    conversation_id: int | None = None
    request_id: str | None = None
    idempotency_key: str | None = None

