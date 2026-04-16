import threading
import time
from collections.abc import AsyncIterator
from logging import Logger, getLogger
from typing import Awaitable, Callable

from anyio import Lock
from pycrdt import Doc
from pycrdt.store.base import BaseYStore, YDocNotFound
from sqlmodel import Session, select

from src.persistence.db.engine import engine, sqlite_write_transaction
from src.persistence.db.models.rooms import Commit, Room, Update


class WriteBuffer:
    """Thread-safe in-memory buffer for Yjs updates."""

    def __init__(
        self,
        flush_callback: Callable[[], None],
        flush_interval: float = 5.0,
        max_size: int = 50,
    ) -> None:
        self._buffer: list[tuple[bytes, int]] = []
        self._lock = threading.Lock()
        self._flush_callback = flush_callback
        self._flush_interval = flush_interval
        self._max_size = max_size
        self._timer: threading.Timer | None = None

    def _schedule_timer_locked(self) -> None:
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(self._flush_interval, self._flush_callback)
        self._timer.daemon = True
        self._timer.start()

    def add(self, data: bytes, timestamp: int) -> bool:
        """Append an update and report whether the buffer should flush now."""

        with self._lock:
            self._buffer.append((data, timestamp))
            should_flush = len(self._buffer) >= self._max_size

            if self._timer:
                self._timer.cancel()
                self._timer = None

            if should_flush:
                return True

            self._schedule_timer_locked()
            return False

    def prepend(self, data: list[tuple[bytes, int]]) -> None:
        """Put a failed batch back at the front of the buffer and retry later."""

        if not data:
            return

        with self._lock:
            self._buffer = list(data) + self._buffer
            self._schedule_timer_locked()

    def flush(self) -> None:
        """Flush the current buffer immediately."""

        should_flush = False
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            if self._buffer:
                should_flush = True

        if should_flush:
            self._flush_callback()

    def clear(self) -> None:
        """Drop the buffered updates without persisting them."""

        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            self._buffer.clear()

    def get_and_clear(self) -> list[tuple[bytes, int]]:
        """Return buffered updates and clear the buffer."""

        with self._lock:
            data = self._buffer.copy()
            self._buffer.clear()
            return data

    def get_copy(self) -> list[tuple[bytes, int]]:
        """Return a snapshot of buffered updates without clearing them."""

        with self._lock:
            return self._buffer.copy()

    def size(self) -> int:
        """Return the number of buffered updates."""

        with self._lock:
            return len(self._buffer)

    def stop(self) -> None:
        """Cancel the scheduled flush timer."""

        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None


class SQLModelYStore(BaseYStore):
    """Persist Yjs room updates with SQLModel-backed commits and deltas.

    Recovery order:
    1. Load the latest full commit or the room head commit.
    2. Replay persisted updates newer than that commit.
    3. Replay any in-memory buffered updates that are not flushed yet.
    """

    BUFFER_SIZE_THRESHOLD = 50
    BUFFER_FLUSH_INTERVAL = 5.0

    document_ttl: int | None = None

    def __init__(
        self,
        room_id: str,
        metadata_callback: Callable[[], Awaitable[bytes] | bytes] | None = None,
        log: Logger | None = None,
    ) -> None:
        self.room_id = room_id
        self.metadata_callback = metadata_callback
        self.log = log or getLogger(__name__)
        self.lock = Lock()
        self._flush_lock = threading.Lock()
        self._buffer = WriteBuffer(
            flush_callback=self._sync_flush,
            flush_interval=self.BUFFER_FLUSH_INTERVAL,
            max_size=self.BUFFER_SIZE_THRESHOLD,
        )

    def _sync_flush(self) -> None:
        """Persist buffered updates to the database."""

        buffer_data: list[tuple[bytes, int]] = []
        try:
            with self._flush_lock:
                buffer_data = self._buffer.get_and_clear()
                if not buffer_data:
                    return

                with sqlite_write_transaction():
                    with Session(engine) as session:
                        for data, timestamp in buffer_data:
                            session.add(
                                Update(
                                    room_id=self.room_id,
                                    data=data,
                                    timestamp=timestamp,
                                )
                            )
                        session.commit()
                        self.log.debug(
                            "Room %s: flushed %d buffered update(s)",
                            self.room_id,
                            len(buffer_data),
                        )
        except Exception as exc:  # pylint: disable=broad-except
            self._buffer.prepend(buffer_data)
            self.log.error("Room %s: failed to flush buffered updates: %s", self.room_id, exc)

    async def read(self) -> AsyncIterator[tuple[bytes, bytes, float]]:
        """Read all persisted and buffered updates for a room."""

        found = False
        self.log.info("[YStore.read] loading room %s", self.room_id)

        async with self.lock:
            with Session(engine) as session:
                room = session.get(Room, self.room_id)
                self.log.info(
                    "[YStore.read] room=%s head_commit=%s",
                    room,
                    room.head_commit_id if room else "N/A",
                )

                commit = None
                if room and room.head_commit_id:
                    commit = session.get(Commit, room.head_commit_id)

                if not commit:
                    commit_stmt = (
                        select(Commit)
                        .where(Commit.room_id == self.room_id)
                        .order_by(Commit.timestamp.desc())  # type: ignore[arg-type]
                        .limit(1)
                    )
                    commit = session.exec(commit_stmt).first()

                if commit:
                    found = True
                    self.log.info(
                        "[YStore.read] using commit id=%s size=%d timestamp=%d",
                        commit.id,
                        len(commit.data),
                        commit.timestamp,
                    )
                    yield commit.data, b"", commit.timestamp / 1000.0

                    updates_stmt = (
                        select(Update)
                        .where(Update.room_id == self.room_id)
                        .where(Update.timestamp > commit.timestamp)
                        .order_by(Update.timestamp)  # type: ignore[arg-type]
                    )
                else:
                    self.log.warning(
                        "[YStore.read] no commit found for room %s, replaying updates only",
                        self.room_id,
                    )
                    updates_stmt = (
                        select(Update)
                        .where(Update.room_id == self.room_id)
                        .order_by(Update.timestamp)  # type: ignore[arg-type]
                    )

                updates = session.exec(updates_stmt).all()
                self.log.info("[YStore.read] found %d persisted update(s)", len(updates))
                for update in updates:
                    found = True
                    self.log.info(
                        "[YStore.read] replay update size=%d timestamp=%d",
                        len(update.data),
                        update.timestamp,
                    )
                    yield update.data, b"", update.timestamp / 1000.0

        buffer_data = self._buffer.get_copy()
        self.log.info(
            "[YStore.read] replaying %d in-memory buffered update(s)",
            len(buffer_data),
        )
        for data, timestamp in buffer_data:
            found = True
            yield data, b"", timestamp / 1000.0

        if not found:
            self.log.warning("[YStore.read] no data found for room %s", self.room_id)
            raise YDocNotFound

        self.log.info("[YStore.read] finished loading room %s", self.room_id)

    async def write(self, data: bytes) -> None:
        """Buffer a new Yjs update and flush if the threshold is reached."""

        current_time = int(time.time() * 1000)
        should_flush = self._buffer.add(data, current_time)
        if should_flush:
            self._sync_flush()

    def flush(self) -> None:
        """Force a synchronous flush of buffered updates."""

        self._buffer.flush()

    def discard(self) -> None:
        """Discard buffered updates."""

        self._buffer.clear()

    async def stop(self) -> None:
        """Stop the store and flush pending updates."""

        self._buffer.stop()
        self._sync_flush()

    def get_buffer_stats(self) -> dict:
        """Return a small snapshot of current buffer state."""

        return {
            "buffer_size": self._buffer.size(),
            "room_id": self.room_id,
        }

    def get_buffer_data(self) -> list[tuple[bytes, int]]:
        """Return buffered updates and clear the buffer."""

        return self._buffer.get_and_clear()

    def get_buffer_copy(self) -> list[tuple[bytes, int]]:
        """Return a copy of buffered updates."""

        return self._buffer.get_copy()

    def get_current_doc(self) -> Doc:
        """Assemble the current room document from commits, updates, and buffer."""

        ydoc = Doc()

        with Session(engine) as session:
            room = session.get(Room, self.room_id)

            commit = None
            if room and room.head_commit_id:
                commit = session.get(Commit, room.head_commit_id)

            if not commit:
                commit_stmt = (
                    select(Commit)
                    .where(Commit.room_id == self.room_id)
                    .order_by(Commit.timestamp.desc())  # type: ignore[arg-type]
                    .limit(1)
                )
                commit = session.exec(commit_stmt).first()

            if commit:
                ydoc.apply_update(commit.data)
                updates_stmt = (
                    select(Update)
                    .where(Update.room_id == self.room_id)
                    .where(Update.timestamp > commit.timestamp)
                    .order_by(Update.timestamp)  # type: ignore[arg-type]
                )
            else:
                updates_stmt = (
                    select(Update)
                    .where(Update.room_id == self.room_id)
                    .order_by(Update.timestamp)  # type: ignore[arg-type]
                )

            updates = session.exec(updates_stmt).all()
            for update in updates:
                ydoc.apply_update(update.data)

        for data, _ in self._buffer.get_copy():
            ydoc.apply_update(data)

        return ydoc
