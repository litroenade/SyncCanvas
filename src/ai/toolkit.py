"""模块名称: toolkit
主要功能: 提供白板操作工具，供 LLM 通过函数调用安全操控画布。
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from pycrdt import Map
from pydantic import BaseModel, ConfigDict, Field

from src.logger import get_logger
from src.ws.sync import websocket_server

logger = get_logger(__name__)


class ShapePayload(BaseModel):
    """单个形状的规范化载体。"""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    type: str = Field(..., description="图形类型: rect/circle/text/arrow/line")
    x: float = Field(..., description="X 坐标")
    y: float = Field(..., description="Y 坐标")
    width: float = Field(100.0, description="宽度")
    height: float = Field(100.0, description="高度")
    text: str = Field("", description="文本内容")
    fill: str = Field("#E0E0E0", description="填充颜色")
    stroke_color: str = Field("#000000", alias="strokeColor", description="描边颜色")
    id: str | None = Field(default=None, description="形状唯一标识，可选")

    def to_canvas_dict(self) -> Dict[str, Any]:
        """转换为前端使用的字段形式。"""

        payload = self.model_dump(by_alias=True)
        if not payload.get("id"):
            payload["id"] = str(uuid.uuid4())
        return payload


class BoardToolKit:
    """封装白板常用操作，确保原子性与日志可追踪。"""

    async def add_shapes(self, room_id: str, shapes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量添加图形到房间。"""

        validated = [ShapePayload.model_validate(item) for item in shapes]
        room = await websocket_server.get_room(room_id)
        doc = room.ydoc
        shapes_map = doc.get("shapes", type=Map)

        created_ids: list[str] = []
        with doc.transaction(origin="ai-tool/add_shapes"):
            for shape in validated:
                shape_dict = shape.to_canvas_dict()
                shape_id = shape_dict["id"]
                shapes_map[shape_id] = shape_dict
                created_ids.append(shape_id)

        logger.info("已添加形状", extra={"room": room_id, "count": len(created_ids)})
        return {"created": created_ids, "count": len(created_ids)}

    async def remove_shapes(self, room_id: str, shape_ids: List[str]) -> Dict[str, Any]:
        """按 ID 删除指定图形。"""

        room = await websocket_server.get_room(room_id)
        doc = room.ydoc
        shapes_map = doc.get("shapes", type=Map)

        removed: list[str] = []
        with doc.transaction(origin="ai-tool/remove_shapes"):
            for sid in shape_ids:
                if sid in shapes_map:
                    shapes_map.pop(sid)
                    removed.append(sid)

        if removed:
            logger.info("已删除形状", extra={"room": room_id, "count": len(removed)})
        return {"removed": removed, "count": len(removed)}

    async def clear_board(self, room_id: str) -> Dict[str, Any]:
        """清空白板上的全部图形。"""

        room = await websocket_server.get_room(room_id)
        doc = room.ydoc
        shapes_map = doc.get("shapes", type=Map)

        with doc.transaction(origin="ai-tool/clear_board"):
            shapes_map.clear()

        logger.info("已清空白板", extra={"room": room_id})
        return {"cleared": True}

    async def update_shape(
        self, room_id: str, shape_id: str, patch: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新单个形状的部分属性。"""

        room = await websocket_server.get_room(room_id)
        doc = room.ydoc
        shapes_map = doc.get("shapes", type=Map)

        try:
            current_shape = dict(shapes_map[shape_id])
        except KeyError:
            logger.warning("形状不存在，跳过更新", extra={"shape": shape_id})
            return {"updated": False, "reason": "shape_not_found"}

        allowed_keys = {
            "type",
            "x",
            "y",
            "width",
            "height",
            "text",
            "fill",
            "strokeColor",
        }
        sanitized_patch = {k: v for k, v in patch.items() if k in allowed_keys}

        if not sanitized_patch:
            return {"updated": False, "reason": "empty_patch"}

        current_shape.update(sanitized_patch)

        with doc.transaction(origin="ai-tool/update_shape"):
            shapes_map[shape_id] = current_shape

        logger.info("形状已更新", extra={"shape": shape_id, "fields": list(sanitized_patch)})
        return {"updated": True, "shape": shape_id, "fields": list(sanitized_patch)}

    async def list_shapes(self, room_id: str, limit: int = 30) -> Dict[str, Any]:
        """列出房间内部分形状以供模型参考。"""

        room = await websocket_server.get_room(room_id)
        doc = room.ydoc
        shapes_map = doc.get("shapes", type=Map)
        items = list(shapes_map.items())[:limit]

        summary = [
            {
                "id": key,
                "type": value.get("type"),
                "text": value.get("text", ""),
                "x": value.get("x"),
                "y": value.get("y"),
            }
            for key, value in items
        ]
        return {"count": len(shapes_map), "sample": summary}


class BoardToolRegistry:
    """工具注册表，提供给 LLM 的工具描述与执行入口。"""

    def __init__(self, toolkit: BoardToolKit):
        self._toolkit = toolkit
        self._tools_schema = self._build_schema()
        self._handlers = {
            "add_shapes": self._toolkit.add_shapes,
            "update_shape": self._toolkit.update_shape,
            "remove_shapes": self._toolkit.remove_shapes,
            "list_shapes": self._toolkit.list_shapes,
            "clear_board": self._toolkit.clear_board,
        }

    @property
    def tools_schema(self) -> List[Dict[str, Any]]:
        """返回 OpenAI 兼容的工具定义列表。"""

        return self._tools_schema

    async def run(self, name: str, arguments: Dict[str, Any], room_id: str) -> Dict[str, Any]:
        """执行指定工具。"""

        if name not in self._handlers:
            raise ValueError(f"未知的工具: {name}")

        handler = self._handlers[name]
        safe_args = {k: v for k, v in arguments.items() if v is not None}

        if name == "add_shapes":
            shapes = safe_args.get("shapes", [])
            return await handler(room_id=room_id, shapes=shapes)

        if name == "update_shape":
            return await handler(
                room_id=room_id,
                shape_id=str(safe_args.get("shape_id", "")),
                patch=safe_args.get("patch", {}),
            )

        if name == "remove_shapes":
            shape_ids = [str(item) for item in safe_args.get("shape_ids", [])]
            return await handler(room_id=room_id, shape_ids=shape_ids)

        if name == "clear_board":
            return await handler(room_id=room_id)

        limit = int(safe_args.get("limit", 30))
        return await handler(room_id=room_id, limit=limit)

    def _build_schema(self) -> List[Dict[str, Any]]:
        """定义工具的 JSON Schema，供模型调用。"""

        return [
            {
                "type": "function",
                "function": {
                    "name": "add_shapes",
                    "description": "批量创建图形并放入白板，需包含坐标与尺寸。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "shapes": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "type": {"type": "string"},
                                        "x": {"type": "number"},
                                        "y": {"type": "number"},
                                        "width": {"type": "number"},
                                        "height": {"type": "number"},
                                        "text": {"type": "string"},
                                        "fill": {"type": "string"},
                                        "strokeColor": {"type": "string"},
                                    },
                                    "required": ["type", "x", "y"],
                                },
                            }
                        },
                        "required": ["shapes"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_shape",
                    "description": "根据 shape_id 更新已有图形的局部属性。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "shape_id": {"type": "string"},
                            "patch": {
                                "type": "object",
                                "description": "仅包含需要修改的字段",
                            },
                        },
                        "required": ["shape_id", "patch"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "remove_shapes",
                    "description": "根据 shape_id 列表删除图形。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "shape_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "需要删除的 shape_id 列表",
                            }
                        },
                        "required": ["shape_ids"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "clear_board",
                    "description": "清空当前白板上的所有图形。",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_shapes",
                    "description": "获取当前白板上的部分图形摘要，便于规划布局。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "返回的最大记录数，默认 30",
                            }
                        },
                    },
                },
            },
        ]
