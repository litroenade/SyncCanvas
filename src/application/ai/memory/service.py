"""Conversation history storage for the AI sidebar."""

from typing import Any, Dict, List, Optional

from sqlmodel import Session, desc, select

from src.infra.logging import get_logger
from src.persistence.db.engine import commit_session, engine
from src.persistence.db.models.ai import AgentMessage, Conversation
from src.utils.time import timestamp_ms

logger = get_logger(__name__)


class MemoryService:
    """Manage conversations and persisted AI messages."""

    _instance: Optional["MemoryService"] = None
    MAX_CHUNK_SIZE: int = 4000

    @classmethod
    def get_instance(cls) -> "MemoryService":
        if cls._instance is None:
            cls._instance = MemoryService()
        return cls._instance

    async def create_conversation(
        self,
        room_id: str,
        title: str = "New conversation",
        user_id: Optional[int] = None,
        mode: str = "planning",
    ) -> Conversation:
        with Session(engine) as session:
            statement = select(Conversation).where(
                Conversation.room_id == room_id,
                Conversation.is_active == True,
            )
            for conversation in session.exec(statement).all():
                conversation.is_active = False

            conversation = Conversation(
                room_id=room_id,
                user_id=user_id,
                title=title,
                mode=mode,
                is_active=True,
            )
            session.add(conversation)
            commit_session(session)
            session.refresh(conversation)

        logger.info(
            "Created conversation: room=%s id=%s title=%s",
            room_id,
            conversation.id,
            title,
        )
        return conversation

    async def get_conversations(
        self,
        room_id: str,
        limit: int = 50,
    ) -> List[Conversation]:
        with Session(engine) as session:
            statement = (
                select(Conversation)
                .where(Conversation.room_id == room_id)
                .order_by(desc(Conversation.updated_at))
                .limit(limit)
            )
            return list(session.exec(statement).all())

    async def get_active_conversation(self, room_id: str) -> Optional[Conversation]:
        with Session(engine) as session:
            statement = select(Conversation).where(
                Conversation.room_id == room_id,
                Conversation.is_active == True,
            )
            return session.exec(statement).first()

    async def get_or_create_conversation(
        self,
        room_id: str,
        user_id: Optional[int] = None,
        mode: str = "planning",
    ) -> Conversation:
        conversation = await self.get_active_conversation(room_id)
        if conversation:
            return conversation
        return await self.create_conversation(room_id, "New conversation", user_id, mode)

    async def update_conversation_title(self, conversation_id: int, title: str) -> None:
        with Session(engine) as session:
            conversation = session.get(Conversation, conversation_id)
            if conversation:
                conversation.title = title
                conversation.updated_at = timestamp_ms()
                commit_session(session)

    async def activate_conversation(
        self,
        room_id: str,
        conversation_id: int,
    ) -> Optional[Conversation]:
        with Session(engine) as session:
            statement = select(Conversation).where(Conversation.room_id == room_id)
            conversations = session.exec(statement).all()
            activated: Optional[Conversation] = None
            updated_at = timestamp_ms()

            for conversation in conversations:
                is_target = conversation.id == conversation_id
                conversation.is_active = is_target
                if is_target:
                    conversation.updated_at = updated_at
                    activated = conversation

            commit_session(session)
            if activated:
                session.refresh(activated)
            return activated

    async def delete_conversation(self, conversation_id: int) -> int:
        with Session(engine) as session:
            msg_statement = select(AgentMessage).where(
                AgentMessage.conversation_id == conversation_id
            )
            messages = session.exec(msg_statement).all()
            message_count = len(messages)
            for message in messages:
                session.delete(message)

            conversation = session.get(Conversation, conversation_id)
            if conversation:
                session.delete(conversation)

            commit_session(session)

        logger.info(
            "Deleted conversation %s with %s message(s)",
            conversation_id,
            message_count,
        )
        return message_count

    async def save_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        run_id: Optional[int] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not content:
            return

        chunks = self._split_content(content)
        total_chunks = len(chunks)

        with Session(engine) as session:
            base_time = timestamp_ms()
            with session.no_autoflush:
                conversation = session.get(Conversation, conversation_id)
            for index, chunk in enumerate(chunks):
                chunk_content = (
                    f"[{index + 1}/{total_chunks}] {chunk}"
                    if total_chunks > 1
                    else chunk
                )
                message = AgentMessage(
                    conversation_id=conversation_id,
                    run_id=run_id,
                    role=role,
                    content=chunk_content,
                    extra_data=extra_data or {},
                    created_at=base_time + index,
                )
                session.add(message)

            if conversation:
                conversation.message_count += total_chunks
                conversation.updated_at = base_time

            commit_session(session)

        logger.debug(
            "Saved message: conversation=%s role=%s length=%s",
            conversation_id,
            role,
            len(content),
        )

    async def get_messages(
        self,
        conversation_id: int,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        with Session(engine) as session:
            statement = (
                select(AgentMessage)
                .where(AgentMessage.conversation_id == conversation_id)
                .order_by(desc(AgentMessage.created_at))
                .limit(limit)
            )
            messages = session.exec(statement).all()

        return [
            {
                "role": message.role,
                "content": message.content,
                "extra_data": message.extra_data,
                "created_at": message.created_at,
            }
            for message in reversed(messages)
        ]

    def _split_content(self, content: str) -> List[str]:
        if len(content) <= self.MAX_CHUNK_SIZE:
            return [content]

        chunks: List[str] = []
        remaining = content
        while remaining:
            if len(remaining) <= self.MAX_CHUNK_SIZE:
                chunks.append(remaining)
                break

            split_pos = self.MAX_CHUNK_SIZE
            for separator in ["\n\n", "\n", ". ", "! ", "? ", ".", "!", "?", " "]:
                position = remaining.rfind(separator, 0, self.MAX_CHUNK_SIZE)
                if position > self.MAX_CHUNK_SIZE // 2:
                    split_pos = position + len(separator)
                    break

            chunks.append(remaining[:split_pos])
            remaining = remaining[split_pos:]

        return chunks


memory_service: MemoryService = MemoryService.get_instance()
