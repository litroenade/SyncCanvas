from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Awaitable, Dict, List, Set, Optional, TypeVar
from fastapi import WebSocket
from src.logger import get_logger

logger = get_logger(__name__)

# 类型别名
MessageHandler = Callable[[str, Dict[str, Any], WebSocket], Awaitable[None]]
T = TypeVar("T")


@dataclass
class Subscription:
    """消息订阅"""

    room_id: str
    message_types: Set[str]
    websocket: WebSocket


@dataclass
class MessageEnvelope:
    """消息信封"""

    type: str
    room_id: str
    data: Dict[str, Any]
    sender: Optional[WebSocket] = None
    broadcast: bool = True  # 是否广播给其他连接


class WebSocketMessageRouter:
    """WebSocket 消息路由器

    集中管理所有 WebSocket 消息的路由和分发。

    Example:
        ```python
        router = WebSocketMessageRouter()

        # 注册处理器
        @router.handler("chat")
        async def handle_chat(room_id, data, ws):
            await router.broadcast(room_id, "chat", {"message": data["text"]})

        # 在 WebSocket 端点中使用
        async def ws_endpoint(websocket: WebSocket, room_id: str):
            await router.connect(websocket, room_id)
            try:
                async for message in websocket.iter_json():
                    await router.dispatch(room_id, message, websocket)
            finally:
                router.disconnect(websocket, room_id)
        ```
    """

    def __init__(self):
        # room_id -> list of websockets
        self._connections: Dict[str, List[WebSocket]] = {}
        # message_type -> handler
        self._handlers: Dict[str, MessageHandler] = {}
        # 消息队列（用于异步处理）
        self._queue: asyncio.Queue[MessageEnvelope] = asyncio.Queue()
        # 后台任务
        self._worker_task: Optional[asyncio.Task] = None
        # 订阅存储: room_id -> {websocket -> set of topics}
        self._subscriptions: Dict[str, Dict[WebSocket, Set[str]]] = {}

    async def start(self) -> None:
        """启动消息处理器"""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._process_queue())
            logger.info("WebSocket 消息路由器已启动")

    async def stop(self) -> None:
        """停止消息处理器"""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
            logger.info("WebSocket 消息路由器已停止")

    def handler(self, message_type: str):
        """注册消息处理器装饰器

        Args:
            message_type: 消息类型

        Example:
            @router.handler("ping")
            async def handle_ping(room_id, data, ws):
                await ws.send_json({"type": "pong"})
        """

        def decorator(func: MessageHandler) -> MessageHandler:
            self._handlers[message_type] = func
            logger.debug("注册消息处理器: %s", message_type)
            return func

        return decorator

    def register_handler(self, message_type: str, handler: MessageHandler) -> None:
        """直接注册消息处理器

        Args:
            message_type: 消息类型
            handler: 处理函数
        """
        self._handlers[message_type] = handler
        logger.debug("注册消息处理器: %s", message_type)

    async def connect(self, websocket: WebSocket, room_id: str) -> None:
        """接受 WebSocket 连接

        Args:
            websocket: WebSocket 连接
            room_id: 房间 ID
        """
        await websocket.accept()

        if room_id not in self._connections:
            self._connections[room_id] = []
        self._connections[room_id].append(websocket)

        logger.info(
            "WebSocket 连接: room=%s, 当前连接数=%d",
            room_id,
            len(self._connections[room_id]),
        )

    def disconnect(self, websocket: WebSocket, room_id: str) -> None:
        """断开 WebSocket 连接

        Args:
            websocket: WebSocket 连接
            room_id: 房间 ID
        """
        if room_id in self._connections:
            if websocket in self._connections[room_id]:
                self._connections[room_id].remove(websocket)
            if not self._connections[room_id]:
                del self._connections[room_id]

        # 清理订阅
        if room_id in self._subscriptions:
            if websocket in self._subscriptions[room_id]:
                del self._subscriptions[room_id][websocket]
            if not self._subscriptions[room_id]:
                del self._subscriptions[room_id]

        logger.info("WebSocket 断开: room=%s", room_id)

    def subscribe(
        self, websocket: WebSocket, room_id: str, topics: List[str]
    ) -> Set[str]:
        """订阅指定主题

        Args:
            websocket: WebSocket 连接
            room_id: 房间 ID
            topics: 要订阅的主题列表

        Returns:
            当前订阅的所有主题
        """
        if room_id not in self._subscriptions:
            self._subscriptions[room_id] = {}
        if websocket not in self._subscriptions[room_id]:
            self._subscriptions[room_id][websocket] = set()

        self._subscriptions[room_id][websocket].update(topics)
        logger.debug("订阅主题: room=%s, topics=%s", room_id, topics)
        return self._subscriptions[room_id][websocket]

    def unsubscribe(
        self, websocket: WebSocket, room_id: str, topics: List[str]
    ) -> Set[str]:
        """取消订阅指定主题

        Args:
            websocket: WebSocket 连接
            room_id: 房间 ID
            topics: 要取消的主题列表

        Returns:
            剩余订阅的主题
        """
        if room_id in self._subscriptions and websocket in self._subscriptions[room_id]:
            self._subscriptions[room_id][websocket] -= set(topics)
            logger.debug("取消订阅: room=%s, topics=%s", room_id, topics)
            return self._subscriptions[room_id][websocket]
        return set()

    def get_subscriptions(self, websocket: WebSocket, room_id: str) -> Set[str]:
        """获取连接的订阅主题

        Args:
            websocket: WebSocket 连接
            room_id: 房间 ID

        Returns:
            订阅的主题集合
        """
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
        """向订阅了指定主题的连接广播消息

        Args:
            room_id: 房间 ID
            topic: 主题名称
            message_type: 消息类型
            data: 消息数据
            exclude: 排除的 WebSocket

        Returns:
            成功发送的连接数
        """
        if room_id not in self._subscriptions:
            return 0

        message = {"type": message_type, "topic": topic, "data": data}
        sent_count = 0
        disconnected = []

        for ws, topics in self._subscriptions[room_id].items():
            if ws is exclude:
                continue
            if topic not in topics:
                continue
            try:
                await ws.send_json(message)
                sent_count += 1
            except Exception:  # pylint: disable=broad-except
                disconnected.append(ws)

        # 清理断开的连接
        for ws in disconnected:
            if ws in self._subscriptions[room_id]:
                del self._subscriptions[room_id][ws]

        return sent_count

    def get_connection_count(self, room_id: str) -> int:
        """获取房间连接数

        Args:
            room_id: 房间 ID

        Returns:
            连接数
        """
        return len(self._connections.get(room_id, []))

    async def dispatch(
        self,
        room_id: str,
        message: Dict[str, Any],
        sender: Optional[WebSocket] = None,
    ) -> bool:
        """分发消息到对应处理器

        Args:
            room_id: 房间 ID
            message: 消息内容
            sender: 发送者 WebSocket

        Returns:
            是否成功处理
        """
        message_type = message.get("type")
        if not message_type:
            logger.warning("消息缺少 type 字段: %s", message)
            return False

        handler = self._handlers.get(message_type)
        if not handler:
            logger.debug("未找到消息处理器: %s", message_type)
            return False

        try:
            await handler(room_id, message.get("data", {}), sender)  # type: ignore[arg-type]
            return True
        except Exception as e:  # pylint: disable=broad-except
            logger.error("消息处理失败: type=%s, error=%s", message_type, e)
            return False

    async def broadcast(
        self,
        room_id: str,
        message_type: str,
        data: Dict[str, Any],
        exclude: Optional[WebSocket] = None,
    ) -> int:
        """向房间广播消息

        Args:
            room_id: 房间 ID
            message_type: 消息类型
            data: 消息数据
            exclude: 排除的 WebSocket（通常是发送者）

        Returns:
            成功发送的连接数
        """
        if room_id not in self._connections:
            return 0

        message = {"type": message_type, "data": data}
        sent_count = 0
        disconnected = []

        for ws in self._connections[room_id]:
            if ws is exclude:
                continue
            try:
                await ws.send_json(message)
                sent_count += 1
            except Exception:  # pylint: disable=broad-except
                disconnected.append(ws)

        # 清理断开的连接
        for ws in disconnected:
            self._connections[room_id].remove(ws)

        return sent_count

    async def send_to(
        self,
        websocket: WebSocket,
        message_type: str,
        data: Dict[str, Any],
    ) -> bool:
        """发送消息到指定连接

        Args:
            websocket: 目标 WebSocket
            message_type: 消息类型
            data: 消息数据

        Returns:
            是否成功
        """
        try:
            await websocket.send_json({"type": message_type, "data": data})
            return True
        except Exception as e:  # pylint: disable=broad-except
            logger.warning("发送消息失败: %s", e)
            return False

    async def enqueue(
        self,
        room_id: str,
        message_type: str,
        data: Dict[str, Any],
        sender: Optional[WebSocket] = None,
        broadcast: bool = True,
    ) -> None:
        """将消息加入队列异步处理

        Args:
            room_id: 房间 ID
            message_type: 消息类型
            data: 消息数据
            sender: 发送者
            broadcast: 是否广播
        """
        envelope = MessageEnvelope(
            type=message_type,
            room_id=room_id,
            data=data,
            sender=sender,
            broadcast=broadcast,
        )
        await self._queue.put(envelope)

    async def _process_queue(self) -> None:
        """后台处理消息队列"""
        while True:
            try:
                envelope = await self._queue.get()

                # 先分发给处理器
                await self.dispatch(
                    envelope.room_id,
                    {"type": envelope.type, "data": envelope.data},
                    envelope.sender,
                )

                # 如果需要广播
                if envelope.broadcast:
                    await self.broadcast(
                        envelope.room_id,
                        envelope.type,
                        envelope.data,
                        exclude=envelope.sender,
                    )

                self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:  # pylint: disable=broad-except
                logger.error("消息队列处理错误: %s", e)


# 全局路由器实例
message_router = WebSocketMessageRouter()


# 预置处理器
@message_router.handler("ping")
async def handle_ping(_room_id: str, _data: Dict[str, Any], ws: WebSocket) -> None:
    """处理 ping 消息"""
    await ws.send_json({"type": "pong", "data": {}})


@message_router.handler("subscribe")
async def handle_subscribe(room_id: str, data: Dict[str, Any], ws: WebSocket) -> None:
    """处理订阅消息"""
    topics = data.get("topics", [])
    current_topics = message_router.subscribe(ws, room_id, topics)
    await ws.send_json({"type": "subscribed", "data": {"topics": list(current_topics)}})


@message_router.handler("unsubscribe")
async def handle_unsubscribe(room_id: str, data: Dict[str, Any], ws: WebSocket) -> None:
    """处理取消订阅消息"""
    topics = data.get("topics", [])
    remaining = message_router.unsubscribe(ws, room_id, topics)
    await ws.send_json(
        {
            "type": "unsubscribed",
            "data": {"removed": topics, "remaining": list(remaining)},
        }
    )
