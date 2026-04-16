import asyncio
import importlib
import sys
from pathlib import Path

import pytest
from sqlmodel import SQLModel, Session, create_engine, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.application.ai.memory.service import MemoryService
from src.infra.singleton_canvas import (
    SINGLETON_CANVAS_ID,
    SINGLETON_USER_USERNAME,
    bootstrap_singleton_canvas,
)
from src.persistence.db.models.ai import AgentMessage, Conversation
from src.persistence.db.models.rooms import Room, RoomMember, Update
from src.persistence.db.models.users import User
from src.persistence.db.repositories import rooms as room_repo

db_engine_module = importlib.import_module("src.persistence.db.engine")
memory_service_module = importlib.import_module("src.application.ai.memory.service")


@pytest.fixture()
def isolated_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    db_path = tmp_path / "db.sqlite"
    test_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(test_engine)
    monkeypatch.setattr(db_engine_module, "engine", test_engine)
    monkeypatch.setattr(memory_service_module, "engine", test_engine)
    return test_engine


def test_bootstrap_singleton_canvas_is_idempotent(isolated_db) -> None:
    bootstrap_singleton_canvas()
    bootstrap_singleton_canvas()

    with Session(isolated_db) as session:
        users = session.exec(select(User)).all()
        rooms = session.exec(select(Room)).all()
        members = session.exec(select(RoomMember)).all()
        assert len(users) == 1
        assert users[0].username == SINGLETON_USER_USERNAME
        assert len(rooms) == 1
        assert len(members) == 1
        assert members[0].room_id == SINGLETON_CANVAS_ID
        assert members[0].user_id == users[0].id


def test_memory_service_conversation_lifecycle_round_trip(isolated_db) -> None:
    service = MemoryService()

    first = asyncio.run(service.create_conversation("room-1", title="First"))
    second = asyncio.run(service.create_conversation("room-1", title="Second"))
    assert first.id is not None
    assert second.id is not None

    activated = asyncio.run(service.activate_conversation("room-1", first.id))
    assert activated is not None
    assert activated.id == first.id

    asyncio.run(service.update_conversation_title(first.id, "Renamed"))
    asyncio.run(
        service.save_message(
            first.id,
            "assistant",
            "hello database",
            extra_data={"status": "ok"},
        )
    )
    messages = asyncio.run(service.get_messages(first.id))
    deleted = asyncio.run(service.delete_conversation(first.id))

    assert len(messages) == 1
    assert messages[0]["content"] == "hello database"
    assert deleted == 1

    with Session(isolated_db) as session:
        remaining = session.get(Conversation, second.id)
        deleted_conversation = session.get(Conversation, first.id)
        deleted_messages = session.exec(
            select(AgentMessage).where(AgentMessage.conversation_id == first.id)
        ).all()
        assert remaining is not None
        assert remaining.is_active is False
        assert deleted_conversation is None
        assert deleted_messages == []


def test_room_repository_round_trip(isolated_db) -> None:
    with Session(isolated_db) as session:
        room = room_repo.create_room(
            session,
            Room(id="room-repo", name="Room Repo"),
        )
        assert room.id == "room-repo"

        update = room_repo.create_update(
            session,
            Update(room_id=room.id, data=b"abc", timestamp=123),
        )
        assert update.id is not None
        assert room_repo.count_updates(session, room.id) == 1

        deleted = room_repo.delete_updates_before(session, room.id, 123)
        assert deleted == 1
        assert room_repo.count_updates(session, room.id) == 0
