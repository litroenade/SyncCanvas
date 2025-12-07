"""
模块名称: board_tools
主要功能: AI 白板操作工具

通过 WebSocket 服务器直接操作 CRDT 文档中的 shapes 记录。
使用与前端 Konva 兼容的扁平化数据格式。
"""

import uuid
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field
from pycrdt import Map

from src.ai_engine.core.agent import AgentContext
from src.ai_engine.core.tools import registry
from src.logger import get_logger
from src.ws.sync import websocket_server

logger = get_logger(__name__)


# --- 参数 Schema ---

class CreateShapeArgs(BaseModel):
    """创建形状的参数"""
    type: str = Field(..., description="形状类型: rect, circle, diamond, text, arrow, line")
    x: float = Field(..., description="画布上的 X 坐标")
    y: float = Field(..., description="画布上的 Y 坐标")
    width: float = Field(100.0, description="形状宽度")
    height: float = Field(100.0, description="形状高度")
    text: str = Field("", description="形状内部的文本（仅 text 类型需要）")
    color: str = Field("#000000", description="描边颜色（十六进制）")
    bg_color: str = Field("transparent", description="填充颜色（十六进制或 transparent）")


class ClearBoardArgs(BaseModel):
    """清空画布的参数"""
    confirm: bool = Field(True, description="确认标志")


class ListShapesArgs(BaseModel):
    """列出形状的参数"""
    limit: int = Field(30, description="返回的形状数量上限")


class UpdateShapeArgs(BaseModel):
    """更新形状的参数"""
    shape_id: str = Field(..., description="形状 ID")
    x: Optional[float] = Field(None, description="新的 X 坐标")
    y: Optional[float] = Field(None, description="新的 Y 坐标")
    width: Optional[float] = Field(None, description="新的宽度")
    height: Optional[float] = Field(None, description="新的高度")
    text: Optional[str] = Field(None, description="新的文本内容")
    color: Optional[str] = Field(None, description="新的描边颜色")
    bg_color: Optional[str] = Field(None, description="新的填充颜色")


class DeleteShapesArgs(BaseModel):
    """删除形状的参数"""
    shape_ids: List[str] = Field(..., description="要删除的形状 ID 列表")


class ConnectShapesArgs(BaseModel):
    """连接两个形状的参数"""
    from_id: str = Field(..., description="起始形状的 ID")
    to_id: str = Field(..., description="结束形状的 ID")
    label: Optional[str] = Field(None, description="连接线上的标签文本")
    color: str = Field("#000000", description="连接线颜色")


def _require_room_id(context: AgentContext) -> str:
    """从 AgentContext 获取房间 ID"""
    if not context or not context.session_id:
        raise ValueError("room_id (session_id) is required in AgentContext for board tools")
    return context.session_id


# --- 工具实现 ---

@registry.register("create_shape", "在白板上创建一个形状或文本", CreateShapeArgs)
async def create_shape(
    type: str,
    x: float,
    y: float,
    width: float = 100,
    height: float = 100,
    text: str = None,
    color: str = "#000000",
    bg_color: str = "transparent",
    context: AgentContext = None,
):
    """在白板上创建一个形状。"""
    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    shapes_map = doc.get("shapes", type=Map)

    shape_id = f"gen_{int(x)}_{int(y)}_{uuid.uuid4().hex[:6]}"
    shape_payload = {
        "id": shape_id,
        "type": type,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "text": text or "",
        "fill": bg_color,
        "strokeColor": color,
    }

    with doc.transaction(origin="ai-engine/create_shape"):
        shapes_map[shape_id] = shape_payload

    logger.info(f"创建形状: {shape_id}", extra={"room": room_id, "type": type})
    return {"status": "success", "message": f"创建了 {type}", "element_id": shape_id}


@registry.register("clear_board", "清空白板上的所有元素", ClearBoardArgs)
async def clear_board(confirm: bool = True, context: AgentContext = None):
    """清空白板上的所有形状。"""
    if not confirm:
        return {"status": "cancelled", "message": "操作已取消"}

    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    shapes_map = doc.get("shapes", type=Map)

    keys_to_delete = list(shapes_map.keys())
    
    with doc.transaction(origin="ai-engine/clear_board"):
        for key in keys_to_delete:
            del shapes_map[key]

    logger.info(f"清空画布: 删除了 {len(keys_to_delete)} 条记录", extra={"room": room_id})
    return {"status": "success", "message": f"清空了 {len(keys_to_delete)} 个元素"}


@registry.register("list_shapes", "列出白板上的形状", ListShapesArgs)
async def list_shapes(limit: int = 30, context: AgentContext = None):
    """获取白板上的形状列表摘要。"""
    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    shapes_map = doc.get("shapes", type=Map)

    shapes = []
    for key, value in shapes_map.items():
        if len(shapes) >= limit:
            break
        shapes.append({
            "id": key,
            "type": value.get("type"),
            "x": value.get("x"),
            "y": value.get("y"),
            "text": value.get("text", ""),
            "width": value.get("width"),
            "height": value.get("height"),
        })

    total = len(shapes_map)
    return {"status": "success", "total": total, "shapes": shapes}


@registry.register("update_shape", "更新形状的属性", UpdateShapeArgs)
async def update_shape(
    shape_id: str,
    x: Optional[float] = None,
    y: Optional[float] = None,
    width: Optional[float] = None,
    height: Optional[float] = None,
    text: Optional[str] = None,
    color: Optional[str] = None,
    bg_color: Optional[str] = None,
    context: AgentContext = None,
):
    """更新已存在形状的属性。"""
    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    shapes_map = doc.get("shapes", type=Map)

    if shape_id not in shapes_map:
        return {"status": "error", "message": "shape_not_found", "shape_id": shape_id}

    current = dict(shapes_map[shape_id])
    updated_fields = []

    if x is not None:
        current["x"] = x
        updated_fields.append("x")
    if y is not None:
        current["y"] = y
        updated_fields.append("y")
    if width is not None:
        current["width"] = width
        updated_fields.append("width")
    if height is not None:
        current["height"] = height
        updated_fields.append("height")
    if text is not None:
        current["text"] = text
        updated_fields.append("text")
    if color is not None:
        current["strokeColor"] = color
        updated_fields.append("color")
    if bg_color is not None:
        current["fill"] = bg_color
        updated_fields.append("bg_color")

    if not updated_fields:
        return {"status": "noop", "message": "没有需要更新的字段"}

    with doc.transaction(origin="ai-engine/update_shape"):
        shapes_map[shape_id] = current

    logger.info(f"更新形状: {shape_id}", extra={"room": room_id, "fields": updated_fields})
    return {"status": "success", "shape_id": shape_id, "updated_fields": updated_fields}


@registry.register("delete_shapes", "删除指定的形状", DeleteShapesArgs)
async def delete_shapes(shape_ids: List[str], context: AgentContext = None):
    """删除指定 ID 的形状。"""
    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    shapes_map = doc.get("shapes", type=Map)

    removed = []
    with doc.transaction(origin="ai-engine/delete_shapes"):
        for sid in shape_ids:
            if sid in shapes_map:
                del shapes_map[sid]
                removed.append(sid)

    logger.info(f"删除形状: {len(removed)} 个", extra={"room": room_id})
    return {"status": "success", "removed": removed}


@registry.register("connect_shapes", "用箭头连接两个形状", ConnectShapesArgs)
async def connect_shapes(
    from_id: str,
    to_id: str,
    label: Optional[str] = None,
    color: str = "#000000",
    context: AgentContext = None,
):
    """用箭头连接两个形状。"""
    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    shapes_map = doc.get("shapes", type=Map)

    if from_id not in shapes_map or to_id not in shapes_map:
        return {"status": "error", "message": "shape_not_found", "from_id": from_id, "to_id": to_id}

    def _center(shape: Dict[str, Any]):
        return (
            float(shape.get("x", 0)) + float(shape.get("width", 0)) / 2.0,
            float(shape.get("y", 0)) + float(shape.get("height", 0)) / 2.0,
        )

    start_shape = shapes_map[from_id]
    end_shape = shapes_map[to_id]
    x1, y1 = _center(start_shape)
    x2, y2 = _center(end_shape)

    connector_id = f"conn_{from_id}_{to_id}"
    connector = {
        "id": connector_id,
        "type": "arrow",
        "x": x1,
        "y": y1,
        "width": max(1.0, abs(x2 - x1)),
        "height": max(1.0, abs(y2 - y1)),
        "points": [[0, 0], [x2 - x1, y2 - y1]],
        "text": label or "",
        "strokeColor": color,
    }

    with doc.transaction(origin="ai-engine/connect_shapes"):
        shapes_map[connector_id] = connector

    logger.info(f"创建连接: {connector_id}", extra={"room": room_id, "from": from_id, "to": to_id})
    return {"status": "success", "connector_id": connector_id}
