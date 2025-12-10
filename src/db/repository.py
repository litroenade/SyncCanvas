"""模块名称: repository
主要功能: 数据仓库抽象层

提供类型安全的数据库操作抽象，将 CRUD 操作封装为 Repository 模式。
"""

from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy import desc
from sqlmodel import Session, SQLModel, select

from src.logger import get_logger
from src.db.models import Room, RoomMember, Commit, Update, AgentRun, AgentAction

logger = get_logger(__name__)

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    """数据仓库基类

    提供通用的 CRUD 操作，子类只需指定模型类型即可。

    Example:
        ```python
        class RoomRepository(BaseRepository[Room]):
            model = Room

            def get_public_rooms(self, session: Session) -> List[Room]:
                return self.filter(session, is_public=True)

        room_repo = RoomRepository()
        room = room_repo.get_by_id(session, "room-123")
        ```
    """

    model: Type[T]

    def get_by_id(self, session: Session, id: Any) -> Optional[T]:
        """根据主键获取单条记录

        Args:
            session: 数据库会话
            id: 主键值

        Returns:
            模型实例；不存在返回 None
        """
        return session.get(self.model, id)

    def get_or_none(self, session: Session, **kwargs) -> Optional[T]:
        """根据条件获取单条记录

        Args:
            session: 数据库会话
            **kwargs: 查询条件

        Returns:
            模型实例；不存在返回 None
        """
        statement = select(self.model)
        for key, value in kwargs.items():
            statement = statement.where(getattr(self.model, key) == value)
        return session.exec(statement).first()

    def get_all(
        self,
        session: Session,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
        order_desc: bool = True,
    ) -> List[T]:
        """获取所有记录

        Args:
            session: 数据库会话
            limit: 最大返回数量
            offset: 偏移量
            order_by: 排序字段
            order_desc: 是否降序

        Returns:
            模型实例列表
        """
        statement = select(self.model)
        if order_by:
            order_column = getattr(self.model, order_by)
            statement = statement.order_by(
                desc(order_column) if order_desc else order_column
            )
        statement = statement.offset(offset).limit(limit)
        return list(session.exec(statement))

    def filter(
        self,
        session: Session,
        limit: int = 100,
        offset: int = 0,
        **kwargs,
    ) -> List[T]:
        """根据条件筛选记录

        Args:
            session: 数据库会话
            limit: 最大返回数量
            offset: 偏移量
            **kwargs: 查询条件

        Returns:
            模型实例列表
        """
        statement = select(self.model)
        for key, value in kwargs.items():
            statement = statement.where(getattr(self.model, key) == value)
        statement = statement.offset(offset).limit(limit)
        return list(session.exec(statement))

    def create(self, session: Session, obj: T) -> T:
        """创建记录

        Args:
            session: 数据库会话
            obj: 模型实例

        Returns:
            创建后的模型实例
        """
        session.add(obj)
        session.commit()
        session.refresh(obj)
        logger.debug(f"创建 {self.model.__name__}: {obj}")
        return obj

    def update(self, session: Session, obj: T, **kwargs) -> T:
        """更新记录

        Args:
            session: 数据库会话
            obj: 模型实例
            **kwargs: 要更新的字段

        Returns:
            更新后的模型实例
        """
        for key, value in kwargs.items():
            setattr(obj, key, value)
        session.add(obj)
        session.commit()
        session.refresh(obj)
        logger.debug(f"更新 {self.model.__name__}: {obj}")
        return obj

    def delete(self, session: Session, obj: T) -> bool:
        """删除记录

        Args:
            session: 数据库会话
            obj: 模型实例

        Returns:
            是否删除成功
        """
        session.delete(obj)
        session.commit()
        logger.debug(f"删除 {self.model.__name__}: {obj}")
        return True

    def delete_by_id(self, session: Session, id: Any) -> bool:
        """根据主键删除记录

        Args:
            session: 数据库会话
            id: 主键值

        Returns:
            是否删除成功
        """
        obj = self.get_by_id(session, id)
        if obj:
            return self.delete(session, obj)
        return False

    def count(self, session: Session, **kwargs) -> int:
        """统计记录数量

        Args:
            session: 数据库会话
            **kwargs: 查询条件

        Returns:
            记录数量
        """
        statement = select(self.model)
        for key, value in kwargs.items():
            statement = statement.where(getattr(self.model, key) == value)
        return len(session.exec(statement).all())

    def exists(self, session: Session, **kwargs) -> bool:
        """检查记录是否存在

        Args:
            session: 数据库会话
            **kwargs: 查询条件

        Returns:
            是否存在
        """
        return self.get_or_none(session, **kwargs) is not None


# ==================== 具体仓库实现 ====================




class RoomRepository(BaseRepository[Room]):
    """房间仓库"""

    model = Room

    def get_public_rooms(self, session: Session, limit: int = 50) -> List[Room]:
        """获取公开房间列表"""
        return self.filter(session, is_public=True, limit=limit)

    def get_user_owned_rooms(self, session: Session, user_id: int) -> List[Room]:
        """获取用户拥有的房间"""
        return self.filter(session, owner_id=user_id)


class RoomMemberRepository(BaseRepository[RoomMember]):
    """房间成员仓库"""

    model = RoomMember

    def get_by_room_and_user(
        self, session: Session, room_id: str, user_id: int
    ) -> Optional[RoomMember]:
        """获取指定房间的指定用户成员信息"""
        return self.get_or_none(session, room_id=room_id, user_id=user_id)

    def is_member(self, session: Session, room_id: str, user_id: int) -> bool:
        """检查用户是否是房间成员"""
        return self.exists(session, room_id=room_id, user_id=user_id)


class CommitRepository(BaseRepository[Commit]):
    """提交仓库"""

    model = Commit

    def get_latest(self, session: Session, room_id: str) -> Optional[Commit]:
        """获取房间最新提交"""
        results = self.get_all(session, limit=1, order_by="timestamp", order_desc=True)
        for r in results:
            if r.room_id == room_id:
                return r
        return None

    def get_by_room(
        self, session: Session, room_id: str, limit: int = 50
    ) -> List[Commit]:
        """获取房间的提交历史"""
        return self.filter(session, room_id=room_id, limit=limit)


class UpdateRepository(BaseRepository[Update]):
    """增量更新仓库"""

    model = Update


class AgentRunRepository(BaseRepository[AgentRun]):
    """Agent 运行记录仓库"""

    model = AgentRun


class AgentActionRepository(BaseRepository[AgentAction]):
    """Agent 工具调用记录仓库"""

    model = AgentAction


# ==================== 仓库实例 ====================


room_repo = RoomRepository()
room_member_repo = RoomMemberRepository()
commit_repo = CommitRepository()
update_repo = UpdateRepository()
agent_run_repo = AgentRunRepository()
agent_action_repo = AgentActionRepository()
