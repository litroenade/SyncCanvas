
import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, TypeVar

from fastapi import WebSocket

from src.infra.logging import get_logger

logger = get_logger(__name__)

MessageHandler = Callable[[str, Dict[str, Any], WebSocket], Awaitable[None]]
T = TypeVar("T")


@dataclass
class Subscription:
    room_id: str
    message_types: Set[str]
    websocket: WebSocket


@dataclass
class MessageEnvelope:
    type: str
    room_id: str
    data: Dict[str, Any]
    sender: Optional[WebSocket] = None
    broadcast: bool = True


class WebSocketMessageRouter:
    """Central websocket message router."""

    def __init__(self):
        self._connections: Dict[str, List[WebSocket]] = {}
        self._handlers: Dict[str, MessageHandler] = {}
        self._queue: asyncio.Queue[MessageEnvelope] = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._subscriptions: Dict[str, Dict[WebSocket, Set[str]]] = {}

    async def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._process_queue())
            logger.info("WebSocket message router started")

    async def stop(self) -> None:
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
            logger.info("WebSocket message router stopped")

    def handler(self, message_type: str):
        def decorator(func: MessageHandler) -> MessageHandler:
            self._handlers[message_type] = func
            logger.debug("Registered websocket handler %s", message_type)
            return func

        return decorator

    def register_handler(self, message_type: str, handler: MessageHandler) -> None:
        self._handlers[message_type] = handler
        logger.debug("Registered websocket handler %s", message_type)

    async def connect(self, websocket: WebSocket, room_id: str) -> None:
        await websocket.accept()
        if room_id not in self._connections:
            self._connections[room_id] = []
        self._connections[room_id].append(websocket)
        logger.info("WebSocket connected: room=%s count=%d", room_id, len(self._connections[room_id]))

    def disconnect(self, websocket: WebSocket, room_id: str) -> None:
        if room_id in self._connections:
            if websocket in self._connections[room_id]:
                self._connections[room_id].remove(websocket)
            if not self._connections[room_id]:
                del self._connections[room_id]
        if room_id in self._subscriptions:
            if websocket in self._subscriptions[room_id]:
                del self._subscriptions[room_id][websocket]
            if not self._subscriptions[room_id]:
                del self._subscriptions[room_id]
        logger.info("WebSocket disconnected: room=%s", room_id)

    def subscribe(self, websocket: WebSocket, room_id: str, topics: List[str]) -> Set[str]:
        if room_id not in self._subscriptions:
            self._subscriptions[room_id] = {}
        if websocket not in self._subscriptions[room_id]:
            self._subscriptions[room_id][websocket] = set()
        self._subscriptions[room_id][websocket].update(topics)
        return self._subscriptions[room_id][websocket]

    def unsubscribe(self, websocket: WebSocket, room_id: str, topics: List[str]) -> Set[str]:
        if room_id in self._subscriptions and websocket in self._subscriptions[room_id]:
            self._subscriptions[room_id][websocket] -= set(topics)
            return self._subscriptions[room_id][websocket]
        return set()

    def get_subscriptions(self, websocket: WebSocket, room_id: str) -> Set[str]:
        if room_id in self._subscriptions and websocket in self._subscriptions[room_id]:
            return self._subscriptions[room_id][websocket]
        return set()

    async def broadcast_to_topic(
        self,
        room_id: str,
        topic: str,
        message_type: str,
        data: Dict[str, Any],
        exclude: Optional[WebSocket] = None,
    ) -> int:
        if room_id not in self._subscriptions:
            return 0
        message = {"type": message_type, "topic": topic, "data": data}
        sent_count = 0
        disconnected = []
        for ws, topics in self._subscriptions[room_id].items():
            if ws is exclude or topic not in topics:
                continue
            try:
                await ws.send_json(message)
                sent_count += 1
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            if ws in self._subscriptions[room_id]:
                del self._subscriptions[room_id][ws]
        return sent_count

    def get_connection_count(self, room_id: str) -> int:
        return len(self._connections.get(room_id, []))

    async def broadcast(
        self,
        room_id: str,
        message_type: str,
        data: Dict[str, Any],
        exclude: Optional[WebSocket] = None,
    ) -> int:
        if room_id not in self._connections:
            return 0
        message = {"type": message_type, "data": data}
        sent_count = 0
        disconnected = []
        for websocket in self._connections[room_id]:
            if websocket is exclude:
                continue
            try:
                await websocket.send_json(message)
                sent_count += 1
            except Exception:
                disconnected.append(websocket)
        for websocket in disconnected:
            self.disconnect(websocket, room_id)
        return sent_count

    async def enqueue(
        self,
        room_id: str,
        message_type: str,
        data: Dict[str, Any],
        *,
        sender: Optional[WebSocket] = None,
        broadcast: bool = True,
    ) -> None:
        await self._queue.put(
            MessageEnvelope(
                type=message_type,
                room_id=room_id,
                data=data,
                sender=sender,
                broadcast=broadcast,
            )
        )

    async def dispatch(self, room_id: str, message: Dict[str, Any], websocket: WebSocket) -> None:
        message_type = message.get("type")
        if not isinstance(message_type, str):
            await websocket.send_json({"type": "error", "message": "invalid_message_type"})
            return
        handler = self._handlers.get(message_type)
        if handler is None:
            await websocket.send_json({"type": "error", "message": f"unknown_message_type:{message_type}"})
            return
        await handler(room_id, message, websocket)

    async def _process_queue(self) -> None:
        while True:
            envelope = await self._queue.get()
            try:
                handler = self._handlers.get(envelope.type)
                if handler:
                    await handler(envelope.room_id, envelope.data, envelope.sender)  # type: ignore[arg-type]
                if envelope.broadcast:
                    await self.broadcast(
                        envelope.room_id,
                        envelope.type,
                        envelope.data,
                        exclude=envelope.sender,
                    )
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("WebSocket queue processing failed: %s", exc)
            finally:
                self._queue.task_done()


message_router = WebSocketMessageRouter()


