"""模块名称: crud
主要功能: 数据库 CRUD 操作，提供房间、提交、更新、成员、笔画等数据的增删改查
"""

from typing import List, Optional

from sqlalchemy import desc
from sqlmodel import Session, select

from .models import Room, Update, RoomMember, Commit


def create_room(session: Session, room: Room) -> Room:
    """创建新房间

    Args:
        session: 数据库会话
        room: 房间对象

    Returns:
        Room: 创建后的房间对象
    """
    session.add(room)
    session.commit()
    session.refresh(room)
    return room


def get_room(session: Session, room_id: str) -> Optional[Room]:
    """获取指定房间

    Args:
        session: 数据库会话
        room_id: 房间 ID

    Returns:
        Optional[Room]: 房间对象，不存在返回 None
    """
    return session.get(Room, room_id)


def get_rooms(
    session: Session,
    user_id: Optional[int] = None,
    is_public: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Room]:
    """获取房间列表

    Args:
        session: 数据库会话
        user_id: 可选，筛选指定用户的房间
        is_public: 可选，筛选公开/私有房间
        limit: 返回数量限制
        offset: 偏移量

    Returns:
        List[Room]: 房间列表
    """
    statement = select(Room)
    if user_id is not None:
        statement = statement.where(Room.owner_id == user_id)
    if is_public is not None:
        statement = statement.where(Room.is_public == is_public)
    statement = statement.order_by(desc(Room.created_at)).offset(offset).limit(limit)
    return list(session.exec(statement))


def delete_room(session: Session, room_id: str) -> bool:
    """删除房间

    Args:
        session: 数据库会话
        room_id: 房间 ID

    Returns:
        bool: 是否删除成功
    """
    room = session.get(Room, room_id)
    if room:
        session.delete(room)
        session.commit()
        return True
    return False


def add_room_member(session: Session, member: RoomMember) -> RoomMember:
    """添加房间成员

    Args:
        session: 数据库会话
        member: 成员对象

    Returns:
        RoomMember: 创建后的成员对象
    """
    session.add(member)
    session.commit()
    session.refresh(member)
    return member


def get_room_members(session: Session, room_id: str) -> List[RoomMember]:
    """获取房间所有成员

    Args:
        session: 数据库会话
        room_id: 房间 ID

    Returns:
        List[RoomMember]: 成员列表
    """
    statement = select(RoomMember).where(RoomMember.room_id == room_id)
    return list(session.exec(statement))


def get_user_rooms(session: Session, user_id: int) -> List[Room]:
    """获取用户加入的所有房间

    Args:
        session: 数据库会话
        user_id: 用户 ID

    Returns:
        List[Room]: 房间列表
    """
    statement = (
        select(Room)
        .join(RoomMember, Room.id == RoomMember.room_id)
        .where(RoomMember.user_id == user_id)
        .order_by(desc(RoomMember.joined_at))
    )
    return list(session.exec(statement))


def is_room_member(session: Session, room_id: str, user_id: int) -> bool:
    """检查用户是否是房间成员

    Args:
        session: 数据库会话
        room_id: 房间 ID
        user_id: 用户 ID

    Returns:
        bool: 是否是成员
    """
    statement = select(RoomMember).where(
        RoomMember.room_id == room_id, RoomMember.user_id == user_id
    )
    return session.exec(statement).first() is not None


def get_room_member(
    session: Session, room_id: str, user_id: int
) -> Optional[RoomMember]:
    """获取房间成员信息

    Args:
        session: 数据库会话
        room_id: 房间 ID
        user_id: 用户 ID

    Returns:
        Optional[RoomMember]: 成员对象，不存在返回 None
    """
    statement = select(RoomMember).where(
        RoomMember.room_id == room_id, RoomMember.user_id == user_id
    )
    return session.exec(statement).first()


def remove_room_member(session: Session, room_id: str, user_id: int) -> bool:
    """移除房间成员

    Args:
        session: 数据库会话
        room_id: 房间 ID
        user_id: 用户 ID

    Returns:
        bool: 是否移除成功
    """
    statement = select(RoomMember).where(
        RoomMember.room_id == room_id, RoomMember.user_id == user_id
    )
    member = session.exec(statement).first()
    if member:
        session.delete(member)
        session.commit()
        return True
    return False


def create_commit(session: Session, commit: Commit) -> Commit:
    """创建提交

    Args:
        session: 数据库会话
        commit: 提交对象

    Returns:
        Commit: 创建后的提交对象
    """
    session.add(commit)
    session.commit()
    session.refresh(commit)
    return commit


def get_latest_commit(session: Session, room_id: str) -> Optional[Commit]:
    """获取房间最新的提交

    Args:
        session: 数据库会话
        room_id: 房间 ID

    Returns:
        Optional[Commit]: 最新的提交对象，若不存在则返回 None
    """
    statement = (
        select(Commit)
        .where(Commit.room_id == room_id)
        .order_by(desc(Commit.timestamp))
        .limit(1)
    )
    return session.exec(statement).first()


def get_commit_by_id(session: Session, commit_id: int) -> Optional[Commit]:
    """根据 ID 获取提交

    Args:
        session: 数据库会话
        commit_id: 提交 ID

    Returns:
        Optional[Commit]: 提交对象，若不存在则返回 None
    """
    return session.get(Commit, commit_id)


def get_commits_by_room(
    session: Session, room_id: str, limit: int = 50
) -> List[Commit]:
    """获取房间的提交历史

    Args:
        session: 数据库会话
        room_id: 房间 ID
        limit: 返回数量限制

    Returns:
        List[Commit]: 提交列表 (从新到旧)
    """
    statement = (
        select(Commit)
        .where(Commit.room_id == room_id)
        .order_by(desc(Commit.timestamp))
        .limit(limit)
    )
    return session.exec(statement).all()


def create_update(session: Session, update: Update) -> Update:
    """创建增量更新

    Args:
        session: 数据库会话
        update: 更新对象

    Returns:
        Update: 创建后的更新对象
    """
    session.add(update)
    session.commit()
    session.refresh(update)
    return update


def get_updates_since(
    session: Session, room_id: str, since_timestamp: int
) -> List[Update]:
    """获取自指定时间以来的所有更新

    Args:
        session: 数据库会话
        room_id: 房间 ID
        since_timestamp: 起始时间戳 (毫秒)

    Returns:
        List[Update]: 更新列表
    """
    statement = (
        select(Update)
        .where(Update.room_id == room_id, Update.timestamp > since_timestamp)
        .order_by(Update.timestamp)
    )
    return list(session.exec(statement))


def get_all_updates(session: Session, room_id: str) -> List[Update]:
    """获取房间所有更新

    Args:
        session: 数据库会话
        room_id: 房间 ID

    Returns:
        List[Update]: 更新列表
    """
    statement = (
        select(Update).where(Update.room_id == room_id).order_by(Update.timestamp)
    )
    return list(session.exec(statement))


def count_updates(session: Session, room_id: str) -> int:
    """统计房间的更新数量

    Args:
        session: 数据库会话
        room_id: 房间 ID

    Returns:
        int: 更新数量
    """
    statement = select(Update).where(Update.room_id == room_id)
    return len(session.exec(statement).all())


def delete_updates_before(session: Session, room_id: str, timestamp: int):
    """删除指定时间之前的更新

    Args:
        session: 数据库会话
        room_id: 房间 ID
        timestamp: 截止时间戳 (毫秒)
    """
    statement = select(Update).where(
        Update.room_id == room_id, Update.timestamp <= timestamp
    )
    results = session.exec(statement)
    for update in results:
        session.delete(update)
    session.commit()
