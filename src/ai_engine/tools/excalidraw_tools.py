"""
模块名称: excalidraw_tools
主要功能: Excalidraw 专用 AI 白板操作工具

通过 WebSocket 服务器直接操作 CRDT 文档中的 elements Y.Array。
使用 Excalidraw 元素 Schema，支持流程图节点创建和绑定箭头。
"""

import uuid
import random
from typing import Optional, List, Literal

from pydantic import BaseModel, Field
from pycrdt import Array, Map

from src.ai_engine.core.agent import AgentContext
from src.ai_engine.core.tools import registry
from src.logger import get_logger
from src.ws.sync import websocket_server

logger = get_logger(__name__)


# --- Excalidraw 元素类型 ---

ExcalidrawShapeType = Literal["rectangle", "diamond", "ellipse", "text"]


# --- 参数 Schema ---

class CreateFlowchartNodeArgs(BaseModel):
    """创建流程图节点的参数"""
    label: str = Field(..., description="节点内部的文字标签")
    node_type: ExcalidrawShapeType = Field(
        "rectangle",
        description="节点类型: rectangle(流程), diamond(判断), ellipse(开始/结束)"
    )
    x: float = Field(..., description="画布上的 X 坐标")
    y: float = Field(..., description="画布上的 Y 坐标")
    width: float = Field(150.0, description="节点宽度")
    height: float = Field(60.0, description="节点高度")
    stroke_color: str = Field("#1e1e1e", description="描边颜色")
    bg_color: str = Field("transparent", description="背景颜色")


class ConnectNodesArgs(BaseModel):
    """连接两个节点的参数"""
    from_id: str = Field(..., description="起始节点的 ID")
    to_id: str = Field(..., description="结束节点的 ID")
    label: Optional[str] = Field(None, description="连线上的文字标签（如 'Yes', 'No'）")
    stroke_color: str = Field("#1e1e1e", description="连线颜色")


class CreateExcalidrawElementArgs(BaseModel):
    """创建 Excalidraw 元素的参数"""
    element_type: str = Field(..., description="元素类型: rectangle, diamond, ellipse, arrow, line, text")
    x: float = Field(..., description="X 坐标")
    y: float = Field(..., description="Y 坐标")
    width: float = Field(100.0, description="宽度")
    height: float = Field(100.0, description="高度")
    text: str = Field("", description="文本内容（仅 text 类型需要）")
    stroke_color: str = Field("#1e1e1e", description="描边颜色")
    bg_color: str = Field("transparent", description="背景颜色")


class ListElementsArgs(BaseModel):
    """列出元素的参数"""
    limit: int = Field(30, description="返回的元素数量上限")


class UpdateElementArgs(BaseModel):
    """更新元素的参数"""
    element_id: str = Field(..., description="元素 ID")
    x: Optional[float] = Field(None, description="新的 X 坐标")
    y: Optional[float] = Field(None, description="新的 Y 坐标")
    width: Optional[float] = Field(None, description="新的宽度")
    height: Optional[float] = Field(None, description="新的高度")
    text: Optional[str] = Field(None, description="新的文本内容")
    stroke_color: Optional[str] = Field(None, description="新的描边颜色")
    bg_color: Optional[str] = Field(None, description="新的背景颜色")


class DeleteElementsArgs(BaseModel):
    """删除元素的参数"""
    element_ids: List[str] = Field(..., description="要删除的元素 ID 列表")


class ClearCanvasArgs(BaseModel):
    """清空画布的参数"""
    confirm: bool = Field(True, description="确认标志")


# --- 辅助函数 ---

def _require_room_id(context: AgentContext) -> str:
    """从 AgentContext 获取房间 ID"""
    if not context or not context.session_id:
        raise ValueError("room_id (session_id) is required in AgentContext for board tools")
    return context.session_id


def _base_excalidraw_element(
    element_type: str,
    x: float,
    y: float,
    width: float,
    height: float,
    stroke_color: str = "#1e1e1e",
    bg_color: str = "transparent",
) -> dict:
    """生成 Excalidraw 元素基础结构"""
    return {
        "id": f"{element_type}_{uuid.uuid4().hex[:8]}",
        "type": element_type,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "strokeColor": stroke_color,
        "backgroundColor": bg_color,
        "fillStyle": "hachure",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "seed": random.randint(1, 100000),
        "version": 1,
        "versionNonce": random.randint(1, 1000000000),
        "isDeleted": False,
        "boundElements": [],
        "updated": 1,
        "link": None,
        "locked": False,
    }


def _get_elements_array(doc) -> Array:
    """获取文档中的 elements Y.Array"""
    return doc.get("elements", type=Array)


def _find_element_by_id(elements_array: Array, element_id: str) -> tuple[int, dict | None]:
    """在 Y.Array 中查找元素，返回 (索引, 元素数据)"""
    for i in range(len(elements_array)):
        el = elements_array[i]
        if isinstance(el, Map):
            if el.get("id") == element_id:
                # 转换为普通字典
                return i, dict(el)
        elif isinstance(el, dict):
            if el.get("id") == element_id:
                return i, el
    return -1, None


def _element_to_ymap(element: dict) -> Map:
    """将元素字典转换为 Y.Map"""
    y_map = Map()
    for key, value in element.items():
        y_map[key] = value
    return y_map


# --- 工具实现 ---

@registry.register("create_flowchart_node", "创建流程图节点（矩形、菱形或椭圆）", CreateFlowchartNodeArgs)
async def create_flowchart_node(
    label: str,
    node_type: str = "rectangle",
    x: float = 0,
    y: float = 0,
    width: float = 150,
    height: float = 60,
    stroke_color: str = "#1e1e1e",
    bg_color: str = "transparent",
    context: AgentContext = None,
):
    """创建流程图节点，包含形状和绑定的文本"""
    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    elements_array = _get_elements_array(doc)

    # 菱形节点调整尺寸
    if node_type == "diamond":
        width = max(width, 120)
        height = max(height, 120)

    # 创建形状元素
    shape_id = f"{node_type}_{uuid.uuid4().hex[:8]}"
    shape = _base_excalidraw_element(node_type, x, y, width, height, stroke_color, bg_color)
    shape["id"] = shape_id
    if node_type == "rectangle":
        shape["roundness"] = {"type": 3}

    # 创建绑定的文本元素
    text_id = f"text_{uuid.uuid4().hex[:8]}"
    text_element = _base_excalidraw_element("text", x + 10, y + height / 2 - 10, width - 20, 20)
    text_element.update({
        "id": text_id,
        "text": label,
        "fontSize": 20,
        "fontFamily": 1,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": shape_id,
        "originalText": label,
        "autoResize": True,
    })

    # 更新形状的 boundElements
    shape["boundElements"] = [{"id": text_id, "type": "text"}]

    with doc.transaction(origin="ai-engine/create_flowchart_node"):
        elements_array.append(_element_to_ymap(shape))
        elements_array.append(_element_to_ymap(text_element))

    logger.info(f"创建流程图节点: {shape_id}", extra={"room": room_id, "type": node_type, "label": label})
    return {"status": "success", "message": f"创建了 {node_type} 节点", "element_id": shape_id, "text_id": text_id}


@registry.register("connect_nodes", "用箭头连接两个流程图节点", ConnectNodesArgs)
async def connect_nodes(
    from_id: str,
    to_id: str,
    label: Optional[str] = None,
    stroke_color: str = "#1e1e1e",
    context: AgentContext = None,
):
    """用绑定箭头连接两个节点"""
    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    elements_array = _get_elements_array(doc)

    # 查找起始和结束节点
    _, start_node = _find_element_by_id(elements_array, from_id)
    _, end_node = _find_element_by_id(elements_array, to_id)

    if not start_node or not end_node:
        return {"status": "error", "message": "找不到指定的节点", "from_id": from_id, "to_id": to_id}

    # 计算节点中心点
    start_cx = start_node.get("x", 0) + start_node.get("width", 0) / 2
    start_cy = start_node.get("y", 0) + start_node.get("height", 0) / 2
    end_cx = end_node.get("x", 0) + end_node.get("width", 0) / 2
    end_cy = end_node.get("y", 0) + end_node.get("height", 0) / 2

    # 创建箭头
    arrow_id = f"arrow_{uuid.uuid4().hex[:8]}"
    arrow = _base_excalidraw_element("arrow", start_cx, start_cy, abs(end_cx - start_cx), abs(end_cy - start_cy), stroke_color)
    arrow.update({
        "id": arrow_id,
        "points": [[0, 0], [end_cx - start_cx, end_cy - start_cy]],
        "startBinding": {"elementId": from_id, "focus": 0.1, "gap": 4},
        "endBinding": {"elementId": to_id, "focus": 0.1, "gap": 4},
        "startArrowhead": None,
        "endArrowhead": "arrow",
    })

    created_elements = [arrow]

    # 如果有标签，创建标签文本
    label_id = None
    if label:
        label_id = f"label_{uuid.uuid4().hex[:8]}"
        mid_x = (start_cx + end_cx) / 2
        mid_y = (start_cy + end_cy) / 2
        label_element = _base_excalidraw_element("text", mid_x - 20, mid_y - 10, 40, 20)
        label_element.update({
            "id": label_id,
            "text": label,
            "fontSize": 14,
            "fontFamily": 1,
            "textAlign": "center",
            "verticalAlign": "middle",
            "originalText": label,
        })
        created_elements.append(label_element)

    with doc.transaction(origin="ai-engine/connect_nodes"):
        for el in created_elements:
            elements_array.append(_element_to_ymap(el))

    logger.info(f"创建连接: {arrow_id}", extra={"room": room_id, "from": from_id, "to": to_id})
    return {"status": "success", "arrow_id": arrow_id, "label_id": label_id}


@registry.register("create_element", "在画布上创建 Excalidraw 元素", CreateExcalidrawElementArgs)
async def create_element(
    element_type: str,
    x: float,
    y: float,
    width: float = 100,
    height: float = 100,
    text: str = "",
    stroke_color: str = "#1e1e1e",
    bg_color: str = "transparent",
    context: AgentContext = None,
):
    """创建单个 Excalidraw 元素"""
    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    elements_array = _get_elements_array(doc)

    element = _base_excalidraw_element(element_type, x, y, width, height, stroke_color, bg_color)

    if element_type == "text":
        element.update({
            "text": text or "文本",
            "fontSize": 20,
            "fontFamily": 1,
            "textAlign": "left",
            "verticalAlign": "top",
            "originalText": text or "文本",
        })

    with doc.transaction(origin="ai-engine/create_element"):
        elements_array.append(_element_to_ymap(element))

    logger.info(f"创建元素: {element['id']}", extra={"room": room_id, "type": element_type})
    return {"status": "success", "message": f"创建了 {element_type}", "element_id": element["id"]}


@registry.register("list_elements", "列出画布上的元素", ListElementsArgs)
async def list_elements(limit: int = 30, context: AgentContext = None):
    """获取画布上的元素列表摘要"""
    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    elements_array = _get_elements_array(doc)

    elements = []
    for i in range(min(len(elements_array), limit)):
        el = elements_array[i]
        if isinstance(el, Map):
            el = dict(el)
        elements.append({
            "id": el.get("id"),
            "type": el.get("type"),
            "x": el.get("x"),
            "y": el.get("y"),
            "width": el.get("width"),
            "height": el.get("height"),
            "text": el.get("text", ""),
        })

    return {"status": "success", "total": len(elements_array), "elements": elements}


@registry.register("update_element", "更新元素的属性", UpdateElementArgs)
async def update_element(
    element_id: str,
    x: Optional[float] = None,
    y: Optional[float] = None,
    width: Optional[float] = None,
    height: Optional[float] = None,
    text: Optional[str] = None,
    stroke_color: Optional[str] = None,
    bg_color: Optional[str] = None,
    context: AgentContext = None,
):
    """更新已存在元素的属性"""
    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    elements_array = _get_elements_array(doc)

    index, current = _find_element_by_id(elements_array, element_id)
    if index < 0:
        return {"status": "error", "message": "元素不存在", "element_id": element_id}

    updated_fields = []
    y_map = elements_array[index]

    with doc.transaction(origin="ai-engine/update_element"):
        if x is not None:
            y_map["x"] = x
            updated_fields.append("x")
        if y is not None:
            y_map["y"] = y
            updated_fields.append("y")
        if width is not None:
            y_map["width"] = width
            updated_fields.append("width")
        if height is not None:
            y_map["height"] = height
            updated_fields.append("height")
        if text is not None:
            y_map["text"] = text
            y_map["originalText"] = text
            updated_fields.append("text")
        if stroke_color is not None:
            y_map["strokeColor"] = stroke_color
            updated_fields.append("strokeColor")
        if bg_color is not None:
            y_map["backgroundColor"] = bg_color
            updated_fields.append("backgroundColor")
        
        # 更新版本号
        y_map["version"] = current.get("version", 0) + 1
        y_map["versionNonce"] = random.randint(1, 1000000000)

    if not updated_fields:
        return {"status": "noop", "message": "没有需要更新的字段"}

    logger.info(f"更新元素: {element_id}", extra={"room": room_id, "fields": updated_fields})
    return {"status": "success", "element_id": element_id, "updated_fields": updated_fields}


@registry.register("delete_elements", "删除指定的元素", DeleteElementsArgs)
async def delete_elements(element_ids: List[str], context: AgentContext = None):
    """删除指定 ID 的元素"""
    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    elements_array = _get_elements_array(doc)

    removed = []
    id_set = set(element_ids)

    with doc.transaction(origin="ai-engine/delete_elements"):
        # 从后向前删除，避免索引偏移
        for i in range(len(elements_array) - 1, -1, -1):
            el = elements_array[i]
            el_id = el.get("id") if isinstance(el, Map) else el.get("id")
            if el_id in id_set:
                elements_array.delete(i, 1)
                removed.append(el_id)

    logger.info(f"删除元素: {len(removed)} 个", extra={"room": room_id})
    return {"status": "success", "removed": removed}


@registry.register("clear_canvas", "清空画布上的所有元素", ClearCanvasArgs)
async def clear_canvas(confirm: bool = True, context: AgentContext = None):
    """清空画布上的所有元素"""
    if not confirm:
        return {"status": "cancelled", "message": "操作已取消"}

    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    elements_array = _get_elements_array(doc)

    count = len(elements_array)

    with doc.transaction(origin="ai-engine/clear_canvas"):
        elements_array.delete(0, count)

    logger.info(f"清空画布: 删除了 {count} 个元素", extra={"room": room_id})
    return {"status": "success", "message": f"清空了 {count} 个元素"}
