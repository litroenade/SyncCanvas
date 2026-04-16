import asyncio
import hashlib
import time
from functools import partial
from typing import Any

from anyio import get_cancelled_exc_class
from pycrdt import Channel, Doc
from pycrdt.websocket import ASGIServer, WebsocketServer, YRoom
from sqlmodel import Session, delete, select

from src.realtime.canvas_backend import init_canvas_backend
from src.infra.logging import get_logger
from src.persistence.db.engine import engine, sqlite_write_transaction
from src.persistence.db.models.rooms import Commit, Room, Update
from src.persistence.db.ystore import SQLModelYStore

logger = get_logger(__name__)


class PersistentWebsocketServer(WebsocketServer):
    """WebSocket server with SQLModel-backed Yjs persistence."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs["auto_clean_rooms"] = False
        super().__init__(**kwargs)
        self._ystores: dict[str, SQLModelYStore] = {}
        self._room_connections: dict[str, int] = {}
        self._room_last_activity: dict[str, float] = {}

    async def serve(self, websocket: Channel) -> None:
        """Track room connections around the base websocket handler."""

        name = websocket.path
        self._room_connections[name] = self._room_connections.get(name, 0) + 1
        self._room_last_activity[name] = time.time()
        logger.debug(
            "room %s connected, active connections=%s",
            name,
            self._room_connections[name],
        )

        try:
            await super().serve(websocket)
        except get_cancelled_exc_class():
            logger.debug("websocket cancelled: %s", name)
        except Exception as exc:  # pylint: disable=broad-except
            unhandled = [
                item
                for item in self._iter_exceptions(exc)
                if not self._is_disconnect_error(item)
            ]
            if unhandled:
                for item in unhandled:
                    logger.exception("websocket error for room %s: %s", name, item)
            else:
                logger.debug("websocket disconnected: %s", name)
        finally:
            try:
                await self._on_client_disconnect(name)
            except asyncio.CancelledError:
                pass
            except Exception as exc:  # pylint: disable=broad-except
                logger.debug("disconnect cleanup failed for %s: %s", name, exc)

    def _is_disconnect_error(self, exception: BaseException) -> bool:
        """Identify transport-layer disconnect noise."""

        error_text = str(exception).lower()
        disconnect_keywords = [
            "clientdisconnected",
            "connectionclosed",
            "no close frame",
            "websocket.close",
            "websocket.send",
            "response already completed",
            "unexpected asgi message",
        ]
        return any(keyword in error_text for keyword in disconnect_keywords)

    def _iter_exceptions(self, exception: BaseException | Exception) -> list[BaseException]:
        """Flatten ExceptionGroup-like instances into leaf exceptions."""

        if hasattr(exception, "exceptions") and exception.exceptions:  # type: ignore[union-attr]
            exceptions: list[BaseException] = []
            for inner in exception.exceptions:  # type: ignore[union-attr]
                exceptions.extend(self._iter_exceptions(inner))
            return exceptions
        return [exception]

    async def get_room(self, name: str) -> YRoom:
        """Get or create a persistent Yjs room for a websocket path."""

        if name not in self.rooms:
            room_id = name.strip("/").split("/")[-1]
            ystore = SQLModelYStore(room_id=room_id, log=self.log)
            self._ystores[name] = ystore

            provider_factory = (
                partial(self.provider_factory, path=name)
                if self.provider_factory is not None
                else None
            )
            room = YRoom(
                ready=True,
                ystore=ystore,
                log=self.log,
                provider_factory=provider_factory,
            )
            self.rooms[name] = room
            logger.info("created websocket room %s for room_id=%s", name, room_id)
            await self._load_room_data(room, room_id)

        room = self.rooms[name]
        # Keep parity with pycrdt-websocket: get_room() must return a started room.
        await self.start_room(room)
        return room

    async def _load_room_data(self, room: YRoom, room_id: str) -> None:
        """Replay the latest commit and newer updates into a fresh room."""

        try:
            with Session(engine) as session:
                db_room = session.exec(select(Room).where(Room.id == room_id)).first()
                if not db_room:
                    logger.debug("room %s not found in database; skipping preload", room_id)
                    return

                commit = None
                if db_room.head_commit_id:
                    commit = session.get(Commit, db_room.head_commit_id)
                if not commit:
                    commit = session.exec(
                        select(Commit)
                        .where(Commit.room_id == room_id)
                        .order_by(Commit.timestamp.desc())  # type: ignore[arg-type]
                        .limit(1)
                    ).first()

                data_count = 0
                if commit:
                    room.ydoc.apply_update(commit.data)
                    data_count += 1
                    logger.info(
                        "preloaded room %s from commit %s (%s bytes)",
                        room_id,
                        commit.id,
                        len(commit.data),
                    )
                    updates = session.exec(
                        select(Update)
                        .where(Update.room_id == room_id)
                        .where(Update.timestamp > commit.timestamp)
                        .order_by(Update.timestamp)  # type: ignore[arg-type]
                    ).all()
                else:
                    updates = session.exec(
                        select(Update)
                        .where(Update.room_id == room_id)
                        .order_by(Update.timestamp)  # type: ignore[arg-type]
                    ).all()

                for update in updates:
                    room.ydoc.apply_update(update.data)
                    data_count += 1

                if updates:
                    logger.info(
                        "preloaded room %s with %s incremental update(s)",
                        room_id,
                        len(updates),
                    )

                if data_count > 0:
                    logger.info(
                        "room %s preload complete with %s record(s)",
                        room_id,
                        data_count,
                    )
                else:
                    logger.debug("room %s has no persisted history", room_id)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("failed to preload room %s: %s", room_id, exc)

    async def _on_client_disconnect(self, name: str) -> None:
        """Handle connection count updates after a client disconnects."""

        if name not in self._room_connections:
            return

        self._room_connections[name] = max(0, self._room_connections[name] - 1)
        logger.debug(
            "room %s disconnected, remaining connections=%s",
            name,
            self._room_connections[name],
        )

        if self._room_connections[name] != 0:
            return

        await asyncio.sleep(2.0)
        if self._room_connections.get(name, 0) == 0:
            await self._auto_commit_on_last_leave(name)

    async def _auto_commit_on_last_leave(self, name: str) -> None:
        """Create an automatic commit after the last client leaves a room."""

        try:
            room_id = name.strip("/").split("/")[-1]
            logger.info("last client left room %s; creating auto commit", room_id)
            if name in self._ystores:
                await self._ystores[name].stop()
            await asyncio.sleep(0.5)
            await self._create_auto_commit(room_id, "Auto save on disconnect")
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("auto commit on disconnect failed for %s: %s", name, exc)

    async def _create_auto_commit(self, room_id: str, message: str) -> bool:
        """Persist buffered room history as a full commit and clear updates."""

        try:
            with sqlite_write_transaction():
                with Session(engine) as session:
                    room = session.exec(select(Room).where(Room.id == room_id)).first()
                    if not room:
                        return False

                    latest = session.exec(
                        select(Commit)
                        .where(Commit.room_id == room_id)
                        .order_by(Commit.timestamp.desc())  # type: ignore[arg-type]
                        .limit(1)
                    ).first()

                    if latest:
                        updates = session.exec(
                            select(Update)
                            .where(Update.room_id == room_id)
                            .where(Update.timestamp > latest.timestamp)
                            .order_by(Update.timestamp)  # type: ignore[arg-type]
                        ).all()
                    else:
                        updates = session.exec(
                            select(Update)
                            .where(Update.room_id == room_id)
                            .order_by(Update.timestamp)  # type: ignore[arg-type]
                        ).all()

                    if not updates:
                        return False

                    ydoc = Doc()
                    if latest:
                        ydoc.apply_update(latest.data)
                    for update in updates:
                        ydoc.apply_update(update.data)

                    doc_data = ydoc.get_update()
                    current_time = int(time.time() * 1000)
                    hash_input = f"{room_id}:{current_time}:{len(doc_data)}"
                    commit_hash = hashlib.sha1(hash_input.encode()).hexdigest()[:7]

                    commit = Commit(
                        room_id=room_id,
                        parent_id=room.head_commit_id,
                        author_name="System",
                        message=message,
                        data=doc_data,
                        timestamp=current_time,
                        hash=commit_hash,
                    )
                    session.add(commit)
                    session.flush()

                    room.head_commit_id = commit.id
                    session.add(room)
                    session.exec(delete(Update).where(Update.room_id == room_id))  # type: ignore[arg-type]
                    session.commit()

                    logger.info("auto commit created for room %s: %s", room_id, commit_hash)
                    return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug("auto commit skipped for room %s: %s", room_id, exc)
            return False

    def update_room_activity(self, name: str) -> None:
        """Refresh the last-activity timestamp for a room path."""

        self._room_last_activity[name] = time.time()

    def get_room_connections(self, name: str) -> int:
        """Return the active connection count for a room path."""

        return self._room_connections.get(name, 0)

    async def check_idle_rooms(self, idle_threshold: float = 300.0) -> None:
        """Auto-commit rooms that have been idle for at least the threshold."""

        current_time = time.time()
        for name, last_activity in list(self._room_last_activity.items()):
            idle_time = current_time - last_activity
            if idle_time < idle_threshold:
                continue
            room_id = name.strip("/").split("/")[-1]
            logger.info(
                "room %s idle for %s seconds; creating auto commit",
                room_id,
                int(idle_time),
            )
            await self._create_auto_commit(room_id, "Auto save on idle")
            self._room_last_activity[name] = current_time

    async def close_room(self, name: str) -> None:
        """Flush and evict a room, persisting a final auto commit if possible."""

        room_id = name.strip("/").split("/")[-1]
        if name in self._ystores:
            ystore = self._ystores[name]
            try:
                await ystore.stop()
                await self._create_auto_commit(room_id, "Auto save on room close")
                logger.info("room %s closed and persisted", name)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("failed to persist room %s on close: %s", name, exc)
            del self._ystores[name]

        self._room_connections.pop(name, None)
        self._room_last_activity.pop(name, None)
        self.rooms.pop(name, None)

    async def flush_room(self, room_id: str) -> None:
        """Force a pending ystore buffer flush for the given room."""

        target_name = None
        for name in self.rooms:
            if name.endswith(f"/{room_id}") or name == room_id:
                target_name = name
                break

        if target_name and target_name in self._ystores:
            self._ystores[target_name].flush()
            logger.debug("flushed room buffer for %s", room_id)

    async def evict_room(self, room_id: str, discard_changes: bool = False) -> None:
        """Remove a room from memory, optionally discarding buffered changes."""

        target_name = None
        for name in self.rooms:
            if name.endswith(f"/{room_id}") or name == room_id:
                target_name = name
                break

        if not target_name:
            return

        if target_name in self._ystores:
            ystore = self._ystores[target_name]
            if discard_changes:
                ystore.discard()
            await ystore.stop()
            del self._ystores[target_name]

        self.rooms.pop(target_name, None)
        self._room_connections.pop(target_name, None)
        self._room_last_activity.pop(target_name, None)
        logger.info("evicted room %s from memory (discard=%s)", room_id, discard_changes)

    def get_ystore(self, room_id: str) -> SQLModelYStore | None:
        """Return the loaded ystore instance for a room, if any."""

        for name in self.rooms:
            if name.endswith(f"/{room_id}") or name == room_id:
                return self._ystores.get(name)
        return None


websocket_server = PersistentWebsocketServer()
init_canvas_backend(websocket_server)
asgi_server = ASGIServer(websocket_server)


async def background_compaction_task() -> None:
    """Periodic background task for idle-room auto commits."""

    idle_check_interval = 300
    idle_threshold = 300.0
    last_idle_check = time.time()

    while True:
        await asyncio.sleep(60)
        current_time = time.time()
        try:
            if current_time - last_idle_check >= idle_check_interval:
                last_idle_check = current_time
                logger.debug("checking idle rooms")
                await websocket_server.check_idle_rooms(idle_threshold)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("background compaction task failed: %s", exc)
