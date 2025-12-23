"""
Memory Service - 房间对话历史管理
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlmodel import Session, select, desc

from src.db.database import engine
from src.logger import get_logger

logger = get_logger(__name__)


class MemoryService:
    """
    Usage:
        memory = MemoryService()
        await memory.save_message("room_123", "user", "画一个流程图")
        history = await memory.get_history("room_123", limit=10)
    """

    _instance: Optional["MemoryService"] = None

    @classmethod
    def get_instance(cls) -> "MemoryService":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = MemoryService()
        return cls._instance

    MAX_CHUNK_SIZE: int = 4000

    async def save_message(
        self,
        room_id: str,
        role: str,
        content: str,
    ) -> None:
        """保存对话消息到房间记忆

        长内容会自动分多条消息保存。

        Args:
            room_id: 房间 ID
            role: 消息角色 (user | assistant)
            content: 消息内容
        """
        if not content:
            return

        # 延迟导入避免循环依赖
        from src.db.models import AgentMessage

        # 分块处理长内容
        chunks = self._split_content(content)
        total_chunks = len(chunks)

        with Session(engine) as session:
            base_time = int(datetime.utcnow().timestamp() * 1000)

            for i, chunk in enumerate(chunks):
                # 多条消息时添加标记
                if total_chunks > 1:
                    chunk_content = f"[{i + 1}/{total_chunks}] {chunk}"
                else:
                    chunk_content = chunk

                memory = AgentMessage(
                    room_id=room_id,
                    role=role,
                    content=chunk_content,
                    created_at=base_time + i,  # 确保顺序
                )
                session.add(memory)

            session.commit()

        logger.debug(
            "保存消息到房间 %s: role=%s, len=%d, chunks=%d",
            room_id,
            role,
            len(content),
            total_chunks,
        )

    def _split_content(self, content: str) -> List[str]:
        """将长内容分割为多个块

        尽量在句子边界分割。
        """
        if len(content) <= self.MAX_CHUNK_SIZE:
            return [content]

        chunks: List[str] = []
        remaining = content

        while remaining:
            if len(remaining) <= self.MAX_CHUNK_SIZE:
                chunks.append(remaining)
                break

            # 尝试在句子边界分割
            split_pos = self.MAX_CHUNK_SIZE

            # 查找最近的句子结束符
            for sep in ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " "]:
                pos = remaining.rfind(sep, 0, self.MAX_CHUNK_SIZE)
                if pos > self.MAX_CHUNK_SIZE // 2:  # 至少保留一半
                    split_pos = pos + len(sep)
                    break

            chunks.append(remaining[:split_pos])
            remaining = remaining[split_pos:]

        return chunks

    async def get_history(
        self,
        room_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """获取房间最近对话历史

        Args:
            room_id: 房间 ID
            limit: 返回消息数量上限

        Returns:
            消息列表，格式: [{"role": "user", "content": "..."}]
        """
        from src.db.models import AgentMessage

        with Session(engine) as session:
            statement = (
                select(AgentMessage)
                .where(AgentMessage.room_id == room_id)
                .order_by(desc(AgentMessage.created_at))
                .limit(limit)
            )
            memories = session.exec(statement).all()

        # 反转为时间正序
        messages = [{"role": m.role, "content": m.content} for m in reversed(memories)]

        logger.debug("加载房间 %s 历史: %d 条消息", room_id, len(messages))
        return messages

    async def clear(self, room_id: str) -> int:
        """清空房间对话记忆

        Args:
            room_id: 房间 ID

        Returns:
            删除的消息数量
        """
        from src.db.models import AgentMessage

        with Session(engine) as session:
            statement = select(AgentMessage).where(AgentMessage.room_id == room_id)
            memories = session.exec(statement).all()
            count = len(memories)

            for m in memories:
                session.delete(m)
            session.commit()

        logger.info("清空房间 %s 记忆: %d 条", room_id, count)
        return count

    async def get_message_count(self, room_id: str) -> int:
        """获取房间消息总数"""
        from src.db.models import AgentMessage

        with Session(engine) as session:
            statement = select(AgentMessage).where(AgentMessage.room_id == room_id)
            return len(session.exec(statement).all())


# 全局实例
memory_service: MemoryService = MemoryService.get_instance()
