"""Shared canvas backend abstraction for realtime room access."""

from typing import Any, Protocol, Tuple

from pycrdt import Array, Doc


class CanvasBackend(Protocol):
    """Minimal interface required by diagram and agent services."""

    async def get_room_doc(self, room_id: str) -> Tuple[Doc, Array]:
        """Return the room Y.Doc and its elements array."""
        ...


class WebSocketCanvasBackend:
    """Canvas backend implementation backed by the Yjs websocket server."""

    def __init__(self, server: Any):
        self._server = server

    async def get_room_doc(self, room_id: str) -> Tuple[Doc, Array]:
        room = await self._server.get_room(f"/ws/{room_id}")
        doc = room.ydoc
        elements = doc.get("elements", type=Array)
        return doc, elements


_backend: CanvasBackend | None = None


def init_canvas_backend(server: Any) -> None:
    """Initialize the global canvas backend."""

    global _backend
    _backend = WebSocketCanvasBackend(server)


def get_canvas_backend() -> CanvasBackend:
    """Return the initialized canvas backend."""

    if _backend is None:
        raise RuntimeError("Canvas backend not initialized. Call init_canvas_backend first.")
    return _backend
