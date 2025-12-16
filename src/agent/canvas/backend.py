"""模块名称: backend
主要功能: 画布后端抽象层
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Tuple

from pycrdt import Array, Doc

if TYPE_CHECKING:
    pass


class CanvasBackend(Protocol):
    """画布后端抽象接口
    
    定义画布操作的最小接口，隔离基础设施。
    """

    async def get_room_doc(self, room_id: str) -> Tuple[Doc, Array]:
        """获取房间文档和元素数组
        
        Args:
            room_id: 房间 ID
            
        Returns:
            (doc, elements_array) 元组
        """
        ...


class WebSocketCanvasBackend:
    """WebSocket 实现的画布后端"""

    def __init__(self, server: Any):
        """初始化
        
        Args:
            server: WebSocket 服务器实例
        """
        self._server = server

    async def get_room_doc(self, room_id: str) -> Tuple[Doc, Array]:
        """获取房间文档和元素数组"""
        room = await self._server.get_room(room_id)
        doc = room.ydoc
        elements = doc.get("elements", type=Array)
        return doc, elements


# 单例工厂
_backend: CanvasBackend | None = None


def init_canvas_backend(server: Any) -> None:
    """初始化画布后端
    
    应在应用启动时调用一次。
    """
    global _backend
    _backend = WebSocketCanvasBackend(server)


def get_canvas_backend() -> CanvasBackend:
    """获取画布后端实例"""
    if _backend is None:
        raise RuntimeError("Canvas backend not initialized. Call init_canvas_backend first.")
    return _backend
