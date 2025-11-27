"""模块名称: crud
主要功能: 数据库 CRUD 操作，提供房间、快照、增量更新的增删改查功能

@Time: 2025-11-26
@Author: Yang208115
@File: crud.py
@Desc: 数据库 CRUD 操作
"""

from typing import List, Optional

from sqlalchemy import desc
from sqlmodel import Session, select

from .models import Room, Snapshot, Update


def create_room(session: Session, room: Room) -> Room:
    """创建新房间"""
    session.add(room)
    session.commit()
    session.refresh(room)
    return room


def get_room(session: Session, room_id: str) -> Optional[Room]:
    """获取指定房间"""
    return session.get(Room, room_id)


def create_snapshot(session: Session, snapshot: Snapshot) -> Snapshot:
    """创建快照"""
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def get_latest_snapshot(session: Session, room_id: str) -> Optional[Snapshot]:
    """获取房间最新的快照

    Args:
        session: 数据库会话
        room_id: 房间 ID

    Returns:
        Optional[Snapshot]: 最新的快照对象，若不存在则返回 None
    """
    statement = (
        select(Snapshot)
        .where(Snapshot.room_id == room_id)
        .order_by(desc(Snapshot.timestamp))
        .limit(1)
    )
    return session.exec(statement).first()


def create_update(session: Session, update: Update) -> Update:
    """创建增量更新"""
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
        since_timestamp: 起始时间戳（毫秒）

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
    """统计房间的更新数量"""
    statement = select(Update).where(Update.room_id == room_id)
    return len(session.exec(statement).all())


def delete_updates_before(session: Session, room_id: str, timestamp: int):
    """删除指定时间之前的更新

    Args:
        session: 数据库会话
        room_id: 房间 ID
        timestamp: 截止时间戳（毫秒）
    """
    statement = select(Update).where(
        Update.room_id == room_id, Update.timestamp <= timestamp
    )
    results = session.exec(statement)
    for update in results:
        session.delete(update)
    session.commit()
