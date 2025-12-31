"""
Memory Service - 对话历史管理

支持多会话，每个会话独立存储消息。
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlmodel import Session, select, desc

from src.db.database import engine
from src.db.models import Conversation, AgentMessage
from src.logger import get_logger

logger = get_logger(__name__)


class MemoryService:
    """
    对话历史管理服务

    Usage:
        memory = MemoryService()
        conv = await memory.create_conversation("room_123", "用户问题标题")
        await memory.save_message(conv.id, "user", "画一个流程图")
        history = await memory.get_messages(conv.id)
    """

    _instance: Optional["MemoryService"] = None

    @classmethod
    def get_instance(cls) -> "MemoryService":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = MemoryService()
        return cls._instance

    MAX_CHUNK_SIZE: int = 4000

    # ========== 对话管理 ==========

    async def create_conversation(
        self,
        room_id: str,
        title: str = "新对话",
        user_id: Optional[int] = None,
        mode: str = "planning",
    ) -> Conversation:
        """创建新对话"""
        with Session(engine) as session:
            # 将其他对话设为非活跃
            statement = select(Conversation).where(
                Conversation.room_id == room_id,
                Conversation.is_active == True,
            )
            for conv in session.exec(statement).all():
                conv.is_active = False

            # 创建新对话
            conversation = Conversation(
                room_id=room_id,
                user_id=user_id,
                title=title,
                mode=mode,
                is_active=True,
            )
            session.add(conversation)
            session.commit()
            session.refresh(conversation)

        logger.info(
            "创建对话: room=%s, id=%d, title=%s", room_id, conversation.id, title
        )
        return conversation

    async def get_conversations(
        self,
        room_id: str,
        limit: int = 50,
    ) -> List[Conversation]:
        """获取房间的所有对话"""
        with Session(engine) as session:
            statement = (
                select(Conversation)
                .where(Conversation.room_id == room_id)
                .order_by(desc(Conversation.updated_at))
                .limit(limit)
            )
            return list(session.exec(statement).all())

    async def get_active_conversation(
        self,
        room_id: str,
    ) -> Optional[Conversation]:
        """获取当前活跃的对话"""
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
        """获取或创建活跃对话"""
        conv = await self.get_active_conversation(room_id)
        if conv:
            return conv
        return await self.create_conversation(room_id, "新对话", user_id, mode)

    async def update_conversation_title(
        self,
        conversation_id: int,
        title: str,
    ) -> None:
        """更新对话标题"""
        with Session(engine) as session:
            conv = session.get(Conversation, conversation_id)
            if conv:
                conv.title = title
                conv.updated_at = int(datetime.utcnow().timestamp() * 1000)
                session.commit()

    async def delete_conversation(
        self,
        conversation_id: int,
    ) -> int:
        """删除对话及其所有消息"""
        with Session(engine) as session:
            # 删除消息
            msg_statement = select(AgentMessage).where(
                AgentMessage.conversation_id == conversation_id
            )
            messages = session.exec(msg_statement).all()
            msg_count = len(messages)
            for m in messages:
                session.delete(m)

            # 删除对话
            conv = session.get(Conversation, conversation_id)
            if conv:
                session.delete(conv)

            session.commit()

        logger.info("删除对话 %d, 消息 %d 条", conversation_id, msg_count)
        return msg_count

    # ========== 消息管理 ==========

    async def save_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        run_id: Optional[int] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """保存消息到对话"""
        if not content:
            return

        chunks = self._split_content(content)
        total_chunks = len(chunks)

        with Session(engine) as session:
            base_time = int(datetime.utcnow().timestamp() * 1000)

            for i, chunk in enumerate(chunks):
                if total_chunks > 1:
                    chunk_content = f"[{i + 1}/{total_chunks}] {chunk}"
                else:
                    chunk_content = chunk

                message = AgentMessage(
                    conversation_id=conversation_id,
                    run_id=run_id,
                    role=role,
                    content=chunk_content,
                    extra_data=extra_data or {},
                    created_at=base_time + i,
                )
                session.add(message)

            # 更新对话
            conv = session.get(Conversation, conversation_id)
            if conv:
                conv.message_count += total_chunks
                conv.updated_at = base_time

            session.commit()

        logger.debug(
            "保存消息: conv=%d, role=%s, len=%d",
            conversation_id,
            role,
            len(content),
        )

    async def get_messages(
        self,
        conversation_id: int,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """获取对话消息"""
        with Session(engine) as session:
            statement = (
                select(AgentMessage)
                .where(AgentMessage.conversation_id == conversation_id)
                .order_by(desc(AgentMessage.created_at))
                .limit(limit)
            )
            messages = session.exec(statement).all()

        return [
            {"role": m.role, "content": m.content, "extra_data": m.extra_data}
            for m in reversed(messages)
        ]

    # ========== 辅助方法 ==========

    def _split_content(self, content: str) -> List[str]:
        """将长内容分割为多个块"""
        if len(content) <= self.MAX_CHUNK_SIZE:
            return [content]

        chunks: List[str] = []
        remaining = content

        while remaining:
            if len(remaining) <= self.MAX_CHUNK_SIZE:
                chunks.append(remaining)
                break

            split_pos = self.MAX_CHUNK_SIZE
            for sep in ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " "]:
                pos = remaining.rfind(sep, 0, self.MAX_CHUNK_SIZE)
                if pos > self.MAX_CHUNK_SIZE // 2:
                    split_pos = pos + len(sep)
                    break

            chunks.append(remaining[:split_pos])
            remaining = remaining[split_pos:]

        return chunks


# 全局实例
memory_service: MemoryService = MemoryService.get_instance()
