"""Room/update/commit repositories."""

from typing import List, Optional

from sqlalchemy import desc
from sqlmodel import Session, select

from src.persistence.db.models.rooms import Commit, Room, RoomMember, Update


def create_room(session: Session, room: Room, auto_commit: bool = True) -> Room:
    session.add(room)
    if auto_commit:
        session.commit()
    else:
        session.flush()
    session.refresh(room)
    return room


def get_room(session: Session, room_id: str) -> Optional[Room]:
    return session.get(Room, room_id)


def get_rooms(
    session: Session,
    user_id: Optional[int] = None,
    is_public: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Room]:
    statement = select(Room)
    if user_id is not None:
        statement = statement.where(Room.owner_id == user_id)
    if is_public is not None:
        statement = statement.where(Room.is_public == is_public)
    statement = statement.order_by(desc(Room.created_at)).offset(offset).limit(limit)  # type: ignore[arg-type]
    return list(session.exec(statement))


def delete_room(session: Session, room_id: str, auto_commit: bool = True) -> bool:
    room = session.get(Room, room_id)
    if room:
        session.delete(room)
        if auto_commit:
            session.commit()
        return True
    return False


def add_room_member(session: Session, member: RoomMember, auto_commit: bool = True) -> RoomMember:
    session.add(member)
    if auto_commit:
        session.commit()
    else:
        session.flush()
    session.refresh(member)
    return member


def get_room_members(session: Session, room_id: str) -> List[RoomMember]:
    statement = select(RoomMember).where(RoomMember.room_id == room_id)
    return list(session.exec(statement))


def get_user_rooms(session: Session, user_id: int) -> List[Room]:
    statement = (
        select(Room)
        .join(RoomMember, Room.id == RoomMember.room_id)  # type: ignore[arg-type]
        .where(RoomMember.user_id == user_id)
        .order_by(desc(RoomMember.joined_at))  # type: ignore[arg-type]
    )
    return list(session.exec(statement))


def is_room_member(session: Session, room_id: str, user_id: int) -> bool:
    statement = select(RoomMember).where(
        RoomMember.room_id == room_id,
        RoomMember.user_id == user_id,
    )
    return session.exec(statement).first() is not None


def get_room_member(session: Session, room_id: str, user_id: int) -> Optional[RoomMember]:
    statement = select(RoomMember).where(
        RoomMember.room_id == room_id,
        RoomMember.user_id == user_id,
    )
    return session.exec(statement).first()


def remove_room_member(
    session: Session,
    room_id: str,
    user_id: int,
    auto_commit: bool = True,
) -> bool:
    statement = select(RoomMember).where(
        RoomMember.room_id == room_id,
        RoomMember.user_id == user_id,
    )
    member = session.exec(statement).first()
    if member:
        session.delete(member)
        if auto_commit:
            session.commit()
        return True
    return False


def create_commit(session: Session, commit: Commit, auto_commit: bool = True) -> Commit:
    session.add(commit)
    if auto_commit:
        session.commit()
    else:
        session.flush()
    session.refresh(commit)
    return commit


def get_latest_commit(session: Session, room_id: str) -> Optional[Commit]:
    statement = (
        select(Commit)
        .where(Commit.room_id == room_id)
        .order_by(desc(Commit.timestamp))  # type: ignore[arg-type]
        .limit(1)
    )
    return session.exec(statement).first()


def get_commit_by_id(session: Session, commit_id: int) -> Optional[Commit]:
    return session.get(Commit, commit_id)


def get_commits_by_room(session: Session, room_id: str, limit: int = 50) -> List[Commit]:
    statement = (
        select(Commit)
        .where(Commit.room_id == room_id)
        .order_by(desc(Commit.timestamp))  # type: ignore[arg-type]
        .limit(limit)
    )
    return list(session.exec(statement).all())


def create_update(session: Session, update: Update, auto_commit: bool = True) -> Update:
    session.add(update)
    if auto_commit:
        session.commit()
    else:
        session.flush()
    session.refresh(update)
    return update


def get_updates_since(session: Session, room_id: str, since_timestamp: int) -> List[Update]:
    statement = (
        select(Update)
        .where(Update.room_id == room_id, Update.timestamp > since_timestamp)
        .order_by(Update.timestamp)  # type: ignore[arg-type]
    )
    return list(session.exec(statement))


def get_all_updates(session: Session, room_id: str) -> List[Update]:
    statement = (
        select(Update)
        .where(Update.room_id == room_id)
        .order_by(Update.timestamp)  # type: ignore[arg-type]
    )
    return list(session.exec(statement))


def count_updates(session: Session, room_id: str) -> int:
    statement = select(Update).where(Update.room_id == room_id)
    return len(session.exec(statement).all())


def delete_updates_before(
    session: Session,
    room_id: str,
    timestamp: int,
    auto_commit: bool = True,
):
    statement = select(Update).where(
        Update.room_id == room_id,
        Update.timestamp <= timestamp,
    )
    results = session.exec(statement)
    deleted = 0
    for update in results:
        session.delete(update)
        deleted += 1
    if auto_commit:
        session.commit()
    return deleted

