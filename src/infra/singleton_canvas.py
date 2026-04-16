"""Single-instance canvas bootstrap helpers."""

from sqlmodel import Session, select

from src.persistence.db.engine import get_sync_session
from src.persistence.db.models.rooms import Room, RoomMember
from src.persistence.db.models.users import User

SINGLETON_CANVAS_ID = "00000000-0000-0000-0000-000000000001"
SINGLETON_CANVAS_NAME = "Main Canvas"
SINGLETON_USER_USERNAME = "local"
SINGLETON_USER_NICKNAME = "Local Canvas"
SINGLETON_USER_PASSWORD_HASH = "single-instance-mode"


def ensure_singleton_user(session: Session) -> User:
    user = session.exec(
        select(User).where(User.username == SINGLETON_USER_USERNAME)
    ).first()
    if user is None:
        user = User(
            username=SINGLETON_USER_USERNAME,
            password_hash=SINGLETON_USER_PASSWORD_HASH,
            nickname=SINGLETON_USER_NICKNAME,
            is_active=True,
            is_admin=True,
            perm_level=999,
        )
        session.add(user)
        session.flush()
        session.refresh(user)
        return user

    changed = False
    if not user.is_active:
        user.is_active = True
        changed = True
    if not user.is_admin:
        user.is_admin = True
        changed = True
    if user.perm_level < 999:
        user.perm_level = 999
        changed = True
    if user.nickname != SINGLETON_USER_NICKNAME:
        user.nickname = SINGLETON_USER_NICKNAME
        changed = True
    if changed:
        session.add(user)
        session.flush()
        session.refresh(user)
    return user


def ensure_singleton_room(session: Session, owner: User) -> Room:
    room = session.get(Room, SINGLETON_CANVAS_ID)
    if room is None:
        room = Room(
            id=SINGLETON_CANVAS_ID,
            name=SINGLETON_CANVAS_NAME,
            owner_id=owner.id,
            password_hash=None,
            is_public=True,
            max_users=100,
        )
        session.add(room)
        session.flush()
        session.refresh(room)
    else:
        changed = False
        if room.name != SINGLETON_CANVAS_NAME:
            room.name = SINGLETON_CANVAS_NAME
            changed = True
        if room.owner_id != owner.id:
            room.owner_id = owner.id
            changed = True
        if room.password_hash is not None:
            room.password_hash = None
            changed = True
        if not room.is_public:
            room.is_public = True
            changed = True
        if room.max_users < 100:
            room.max_users = 100
            changed = True
        if changed:
            session.add(room)
            session.flush()
            session.refresh(room)

    if owner.id is not None:
        membership = session.exec(
            select(RoomMember).where(
                RoomMember.room_id == SINGLETON_CANVAS_ID,
                RoomMember.user_id == owner.id,
            )
        ).first()
        if membership is None:
            session.add(
                RoomMember(
                    room_id=SINGLETON_CANVAS_ID,
                    user_id=owner.id,
                    role="owner",
                )
            )
            session.flush()

    return room


def bootstrap_singleton_canvas() -> tuple[User, Room]:
    with get_sync_session() as session:
        user = ensure_singleton_user(session)
        room = ensure_singleton_room(session, user)
        return user, room
