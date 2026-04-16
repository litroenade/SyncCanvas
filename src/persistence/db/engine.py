"""Database engine and session helpers."""

from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Protocol, cast

from sqlalchemy import event

from sqlmodel import SQLModel, Session, create_engine

from src.infra.config import config
from src.persistence.db.models.ai import (
    AgentAction,
    AgentMessage,
    AgentRequest,
    AgentRun,
    Conversation,
)
from src.persistence.db.models.rooms import Commit, Room, RoomMember, Update
from src.persistence.db.models.users import User

_ = (
    User,
    Room,
    RoomMember,
    Update,
    Commit,
    AgentRun,
    AgentAction,
    AgentRequest,
    Conversation,
    AgentMessage,
)

_db_url = config.database_url
_db_path = _db_url.replace("sqlite:///", "").lstrip("./")
_db_dir = Path(_db_path).parent
_db_dir.mkdir(parents=True, exist_ok=True)
_sqlite_busy_timeout_ms = 30000
_sqlite_write_lock = RLock()


class _SQLiteCursorLike(Protocol):
    def execute(self, statement: str) -> object: ...
    def close(self) -> None: ...


class _SQLiteConnectionLike(Protocol):
    def cursor(self) -> _SQLiteCursorLike: ...


def _is_sqlite_url(db_url: str) -> bool:
    return db_url.startswith("sqlite")


def _get_connect_args(db_url: str) -> dict[str, object]:
    if _is_sqlite_url(db_url):
        return {
            "check_same_thread": False,
            "timeout": _sqlite_busy_timeout_ms / 1000.0,
        }
    return {}


def _configure_sqlite_connection(dbapi_connection: object) -> None:
    connection = cast(_SQLiteConnectionLike, dbapi_connection)
    cursor = connection.cursor()
    try:
        cursor.execute(f"PRAGMA busy_timeout={_sqlite_busy_timeout_ms}")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()

engine = create_engine(
    _db_url,
    connect_args=_get_connect_args(_db_url),
    echo=config.db_echo,
)

if _is_sqlite_url(_db_url):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(
        dbapi_connection: object,
        _connection_record: object,
    ) -> None:
        _configure_sqlite_connection(dbapi_connection)


def init_db():
    from src.persistence.db.models.library_records import Library, LibraryItem  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


def commit_session(session: Session) -> None:
    with sqlite_write_transaction():
        session.commit()


@contextmanager
def get_sync_session():
    session = Session(engine)
    try:
        yield session
        commit_session(session)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def sqlite_write_transaction():
    if _is_sqlite_url(_db_url):
        with _sqlite_write_lock:
            yield
        return
    yield
