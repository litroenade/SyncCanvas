"""Conversation/message repositories."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import desc
from sqlmodel import Session, select

from src.persistence.db.models.ai import AgentMessage, Conversation


def list_conversations(session: Session, room_id: str, limit: int = 50) -> List[Conversation]:
    statement = (
        select(Conversation)
        .where(Conversation.room_id == room_id)
        .order_by(desc("updated_at"))
        .limit(limit)
    )
    return list(session.exec(statement).all())


def get_active_conversation(session: Session, room_id: str) -> Optional[Conversation]:
    statement = select(Conversation).where(
        Conversation.room_id == room_id,
        Conversation.is_active == True,
    )
    return session.exec(statement).first()


def list_messages(session: Session, conversation_id: int, limit: int = 50) -> List[AgentMessage]:
    statement = (
        select(AgentMessage)
        .where(AgentMessage.conversation_id == conversation_id)
        .order_by(desc("created_at"))
        .limit(limit)
    )
    return list(session.exec(statement).all())

