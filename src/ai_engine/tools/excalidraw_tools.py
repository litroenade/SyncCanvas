"""模块名称: excalidraw_tools
主要功能: Excalidraw 专用 AI 白板操作工具

通过 WebSocket 服务器直接操作 CRDT 文档中的 elements Y.Array。
使用 Excalidraw 元素 Schema，支持流程图节点创建和绑定箭头。
"""

import uuid
import random
from typing import Optional, List, Literal, Dict, Any

from pydantic import BaseModel, Field
from pycrdt import Array, Map

from src.ai_engine.core.agent import AgentContext
from src.ai_engine.core.tools import registry
from src.logger import get_logger
from src.ws.sync import websocket_server

logger = get_logger(__name__)


# ==================== 类型定义 ====================

ExcalidrawShapeType = Literal["rectangle", "diamond", "ellipse", "text"]


# ==================== 参数 Schema ====================

class CreateFlowchartNodeArgs(BaseModel):
    """创建流程图节点的参数

    Attributes:
        label: 节点内部的文字标签
        node_type: 节点类型
        x: 画布上的 X 坐标
        y: 画布上的 Y 坐标
        width: 节点宽度
        height: 节点高度
        stroke_color: 描边颜色
        bg_color: 背景颜色
    """
    label: str = Field(..., description="节点内部的文字标签")
    node_type: ExcalidrawShapeType = Field(
        "rectangle",
        description="节点类型: rectangle(流程步骤), diamond(判断), ellipse(开始/结束)"
    )
    x: float = Field(..., description="画布上的 X 坐标")
    y: float = Field(..., description="画布上的 Y 坐标")
    width: float = Field(160.0, description="节点宽度")
    height: float = Field(70.0, description="节点高度")
    stroke_color: str = Field("#1e1e1e", description="描边颜色")
    bg_color: str = Field("#ffffff", description="背景颜色")


class ConnectNodesArgs(BaseModel):
    """连接两个节点的参数

    Attributes:
        from_id: 起始节点的 ID
        to_id: 结束节点的 ID
        label: 连线上的文字标签
        stroke_color: 连线颜色
    """
    from_id: str = Field(..., description="起始节点的 ID (create_flowchart_node 返回的 element_id)")
    to_id: str = Field(..., description="结束节点的 ID (create_flowchart_node 返回的 element_id)")
    label: Optional[str] = Field(None, description="连线上的文字标签 (如 '是', '否')")
    stroke_color: str = Field("#1e1e1e", description="连线颜色")


class CreateExcalidrawElementArgs(BaseModel):
    """创建 Excalidraw 元素的参数

    Attributes:
        element_type: 元素类型
        x: X 坐标
        y: Y 坐标
        width: 宽度
        height: 高度
        text: 文本内容
        stroke_color: 描边颜色
        bg_color: 背景颜色
    """
    element_type: str = Field(..., description="元素类型: rectangle, diamond, ellipse, arrow, line, text")
    x: float = Field(..., description="X 坐标")
    y: float = Field(..., description="Y 坐标")
    width: float = Field(100.0, description="宽度")
    height: float = Field(100.0, description="高度")
    text: str = Field("", description="文本内容 (仅 text 类型需要)")
    stroke_color: str = Field("#1e1e1e", description="描边颜色")
    bg_color: str = Field("transparent", description="背景颜色")


class ListElementsArgs(BaseModel):
    """列出元素的参数

    Attributes:
        limit: 返回的元素数量上限
    """
    limit: int = Field(30, description="返回的元素数量上限")


class UpdateElementArgs(BaseModel):
    """更新元素的参数

    Attributes:
        element_id: 元素 ID
        x: 新的 X 坐标
        y: 新的 Y 坐标
        width: 新的宽度
        height: 新的高度
        text: 新的文本内容
        stroke_color: 新的描边颜色
        bg_color: 新的背景颜色
    """
    element_id: str = Field(..., description="元素 ID")
    x: Optional[float] = Field(None, description="新的 X 坐标")
    y: Optional[float] = Field(None, description="新的 Y 坐标")
    width: Optional[float] = Field(None, description="新的宽度")
    height: Optional[float] = Field(None, description="新的高度")
    text: Optional[str] = Field(None, description="新的文本内容")
    stroke_color: Optional[str] = Field(None, description="新的描边颜色")
    bg_color: Optional[str] = Field(None, description="新的背景颜色")


class DeleteElementsArgs(BaseModel):
    """删除元素的参数

    Attributes:
        element_ids: 要删除的元素 ID 列表
    """
    element_ids: List[str] = Field(..., description="要删除的元素 ID 列表")


class ClearCanvasArgs(BaseModel):
    """清空画布的参数

    Attributes:
        confirm: 确认标志
    """
    confirm: bool = Field(True, description="确认标志")


class GetElementByIdArgs(BaseModel):
    """获取元素详情的参数

    Attributes:
        element_id: 元素 ID
    """
    element_id: str = Field(..., description="要查询的元素 ID")


# ==================== 辅助函数 ====================

def _require_room_id(context: AgentContext) -> str:
    """从 AgentContext 获取房间 ID

    Args:
        context: Agent 上下文

    Returns:
        str: 房间 ID

    Raises:
        ValueError: 当 context 为空或没有 session_id 时
    """
    if not context or not context.session_id:
        raise ValueError("room_id (session_id) is required in AgentContext for board tools")
    return context.session_id


def _generate_element_id(prefix: str = "el") -> str:
    """生成唯一的元素 ID

    Args:
        prefix: ID 前缀

    Returns:
        str: 唯一 ID
    """
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _base_excalidraw_element(
    element_type: str,
    x: float,
    y: float,
    width: float,
    height: float,
    stroke_color: str = "#1e1e1e",
    bg_color: str = "transparent",
) -> Dict[str, Any]:
    """生成 Excalidraw 元素基础结构

    Args:
        element_type: 元素类型
        x: X 坐标
        y: Y 坐标
        width: 宽度
        height: 高度
        stroke_color: 描边颜色
        bg_color: 背景颜色

    Returns:
        dict: Excalidraw 元素字典
    """
    return {
        "id": _generate_element_id(element_type),
        "type": element_type,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "strokeColor": stroke_color,
        "backgroundColor": bg_color,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 0,  # 0 = 平滑线条
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
    """获取文档中的 elements Y.Array

    Args:
        doc: Y.Doc 文档对象

    Returns:
        Array: elements Y.Array
    """
    return doc.get("elements", type=Array)


def _find_element_by_id(elements_array: Array, element_id: str) -> tuple:
    """在 Y.Array 中查找元素

    Args:
        elements_array: Y.Array 元素数组
        element_id: 要查找的元素 ID

    Returns:
        tuple: (索引, 元素数据) 或 (-1, None)
    """
    for i in range(len(elements_array)):
        el = elements_array[i]
        if isinstance(el, Map):
            if el.get("id") == element_id:
                return i, dict(el)
        elif isinstance(el, dict):
            if el.get("id") == element_id:
                return i, el
    return -1, None


def _element_to_ymap(element: Dict[str, Any]) -> Map:
    """将元素字典转换为 Y.Map

    Args:
        element: 元素字典

    Returns:
        Map: Y.Map 对象
    """
    y_map = Map()
    for key, value in element.items():
        y_map[key] = value
    return y_map


# ==================== 工具实现 ====================

@registry.register(
    "create_flowchart_node",
    "创建流程图节点 (自动绑定文本标签)，返回 element_id 用于后续连接",
    CreateFlowchartNodeArgs
)
async def create_flowchart_node(
    label: str,
    node_type: str = "rectangle",
    x: float = 400,
    y: float = 50,
    width: float = 160,
    height: float = 70,
    stroke_color: str = "#1e1e1e",
    bg_color: str = "#ffffff",
    context: AgentContext = None,
) -> Dict[str, Any]:
    """创建流程图节点，包含形状和绑定的文本

    Args:
        label: 节点标签文字
        node_type: 节点类型 (rectangle/diamond/ellipse)
        x: X 坐标
        y: Y 坐标
        width: 宽度
        height: 高度
        stroke_color: 描边颜色
        bg_color: 背景颜色
        context: Agent 上下文

    Returns:
        dict: 包含 status, element_id, text_id 的结果
    """
    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    elements_array = _get_elements_array(doc)

    # 根据节点类型调整尺寸
    if node_type == "diamond":
        width = max(width, 120)
        height = max(height, 120)
    elif node_type == "ellipse":
        width = max(width, 120)
        height = max(height, 50)

    # 创建形状元素
    shape_id = _generate_element_id(node_type)
    shape = _base_excalidraw_element(node_type, x, y, width, height, stroke_color, bg_color)
    shape["id"] = shape_id

    # 矩形添加圆角
    if node_type == "rectangle":
        shape["roundness"] = {"type": 3}

    # 创建绑定的文本元素
    text_id = _generate_element_id("text")
    text_x = x + width / 2
    text_y = y + height / 2

    text_element = {
        "id": text_id,
        "type": "text",
        "x": text_x,
        "y": text_y,
        "width": width - 20,
        "height": 20,
        "strokeColor": stroke_color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "seed": random.randint(1, 100000),
        "version": 1,
        "versionNonce": random.randint(1, 1000000000),
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "text": label,
        "fontSize": 18,
        "fontFamily": 1,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": shape_id,
        "originalText": label,
        "autoResize": True,
    }

    # 更新形状的 boundElements
    shape["boundElements"] = [{"id": text_id, "type": "text"}]

    with doc.transaction(origin="ai-engine/create_flowchart_node"):
        elements_array.append(_element_to_ymap(shape))
        elements_array.append(_element_to_ymap(text_element))

    logger.info(
        f"创建流程图节点: {shape_id}",
        extra={"room": room_id, "type": node_type, "label": label}
    )

    return {
        "status": "success",
        "message": f"已创建 {node_type} 节点: {label}",
        "element_id": shape_id,
        "text_id": text_id,
        "position": {"x": x, "y": y},
        "size": {"width": width, "height": height}
    }


@registry.register(
    "connect_nodes",
    "用箭头连接两个流程图节点 (使用 create_flowchart_node 返回的 element_id)",
    ConnectNodesArgs
)
async def connect_nodes(
    from_id: str,
    to_id: str,
    label: Optional[str] = None,
    stroke_color: str = "#1e1e1e",
    context: AgentContext = None,
) -> Dict[str, Any]:
    """用绑定箭头连接两个节点

    Args:
        from_id: 起始节点 ID
        to_id: 目标节点 ID
        label: 连线标签 (可选)
        stroke_color: 连线颜色
        context: Agent 上下文

    Returns:
        dict: 包含 status, arrow_id, label_id 的结果
    """
    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    elements_array = _get_elements_array(doc)

    # 查找起始和结束节点
    _, start_node = _find_element_by_id(elements_array, from_id)
    _, end_node = _find_element_by_id(elements_array, to_id)

    if not start_node:
        return {
            "status": "error",
            "message": f"找不到起始节点: {from_id}",
            "from_id": from_id,
            "to_id": to_id
        }

    if not end_node:
        return {
            "status": "error",
            "message": f"找不到目标节点: {to_id}",
            "from_id": from_id,
            "to_id": to_id
        }

    # 计算节点边缘连接点
    start_x = start_node.get("x", 0)
    start_y = start_node.get("y", 0)
    start_w = start_node.get("width", 100)
    start_h = start_node.get("height", 100)

    end_x = end_node.get("x", 0)
    end_y = end_node.get("y", 0)
    end_w = end_node.get("width", 100)
    end_h = end_node.get("height", 100)

    # 计算中心点
    start_cx = start_x + start_w / 2
    start_cy = start_y + start_h / 2
    end_cx = end_x + end_w / 2
    end_cy = end_y + end_h / 2

    # 确定连接点 (从下边缘到上边缘)
    if end_cy > start_cy:  # 目标在下方
        arrow_start_y = start_y + start_h
        arrow_end_y = end_y
    else:  # 目标在上方
        arrow_start_y = start_y
        arrow_end_y = end_y + end_h

    # 处理水平方向
    if abs(end_cx - start_cx) > 50:  # 有水平偏移
        if end_cx > start_cx:  # 目标在右侧
            arrow_start_x = start_x + start_w
            arrow_end_x = end_x
        else:  # 目标在左侧
            arrow_start_x = start_x
            arrow_end_x = end_x + end_w
    else:
        arrow_start_x = start_cx
        arrow_end_x = end_cx

    # 创建箭头
    arrow_id = _generate_element_id("arrow")
    arrow = _base_excalidraw_element(
        "arrow",
        arrow_start_x,
        arrow_start_y,
        abs(arrow_end_x - arrow_start_x),
        abs(arrow_end_y - arrow_start_y),
        stroke_color,
        "transparent"
    )
    arrow.update({
        "id": arrow_id,
        "points": [[0, 0], [arrow_end_x - arrow_start_x, arrow_end_y - arrow_start_y]],
        "startBinding": {"elementId": from_id, "focus": 0, "gap": 4},
        "endBinding": {"elementId": to_id, "focus": 0, "gap": 4},
        "startArrowhead": None,
        "endArrowhead": "arrow",
        "strokeWidth": 2,
    })

    created_elements = [arrow]
    label_id = None

    # 如果有标签，创建标签文本
    if label:
        label_id = _generate_element_id("label")
        mid_x = (arrow_start_x + arrow_end_x) / 2
        mid_y = (arrow_start_y + arrow_end_y) / 2

        label_element = {
            "id": label_id,
            "type": "text",
            "x": mid_x - 15,
            "y": mid_y - 10,
            "width": 30,
            "height": 20,
            "strokeColor": stroke_color,
            "backgroundColor": "#ffffff",
            "fillStyle": "solid",
            "strokeWidth": 1,
            "strokeStyle": "solid",
            "roughness": 0,
            "opacity": 100,
            "groupIds": [],
            "seed": random.randint(1, 100000),
            "version": 1,
            "versionNonce": random.randint(1, 1000000000),
            "isDeleted": False,
            "boundElements": None,
            "updated": 1,
            "link": None,
            "locked": False,
            "text": label,
            "fontSize": 14,
            "fontFamily": 1,
            "textAlign": "center",
            "verticalAlign": "middle",
            "originalText": label,
        }
        created_elements.append(label_element)

    with doc.transaction(origin="ai-engine/connect_nodes"):
        for el in created_elements:
            elements_array.append(_element_to_ymap(el))

    logger.info(
        f"创建连接: {arrow_id}",
        extra={"room": room_id, "from": from_id, "to": to_id, "label": label}
    )

    return {
        "status": "success",
        "message": f"已连接节点 {from_id} → {to_id}" + (f" (标签: {label})" if label else ""),
        "arrow_id": arrow_id,
        "label_id": label_id
    }


@registry.register(
    "create_element",
    "在画布上创建基础 Excalidraw 元素",
    CreateExcalidrawElementArgs
)
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
) -> Dict[str, Any]:
    """创建单个 Excalidraw 元素

    Args:
        element_type: 元素类型
        x: X 坐标
        y: Y 坐标
        width: 宽度
        height: 高度
        text: 文本内容 (仅 text 类型需要)
        stroke_color: 描边颜色
        bg_color: 背景颜色
        context: Agent 上下文

    Returns:
        dict: 包含 status, element_id 的结果
    """
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

    return {
        "status": "success",
        "message": f"已创建 {element_type}",
        "element_id": element["id"]
    }


@registry.register(
    "list_elements",
    "列出画布上的元素摘要信息",
    ListElementsArgs
)
async def list_elements(
    limit: int = 30,
    context: AgentContext = None
) -> Dict[str, Any]:
    """获取画布上的元素列表摘要

    Args:
        limit: 返回的元素数量上限
        context: Agent 上下文

    Returns:
        dict: 包含 status, total, elements 的结果
    """
    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    elements_array = _get_elements_array(doc)

    elements = []
    for i in range(min(len(elements_array), limit)):
        el = elements_array[i]
        if isinstance(el, Map):
            el = dict(el)

        # 只返回非删除的元素
        if el.get("isDeleted"):
            continue

        elements.append({
            "id": el.get("id"),
            "type": el.get("type"),
            "x": round(el.get("x", 0), 1),
            "y": round(el.get("y", 0), 1),
            "width": round(el.get("width", 0), 1),
            "height": round(el.get("height", 0), 1),
            "text": el.get("text", "")[:50] if el.get("text") else None,
        })

    return {
        "status": "success",
        "total": len(elements_array),
        "shown": len(elements),
        "elements": elements
    }


@registry.register(
    "get_element",
    "获取指定元素的详细信息",
    GetElementByIdArgs
)
async def get_element(
    element_id: str,
    context: AgentContext = None
) -> Dict[str, Any]:
    """获取指定元素的详细信息

    Args:
        element_id: 元素 ID
        context: Agent 上下文

    Returns:
        dict: 包含元素详细信息的结果
    """
    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    elements_array = _get_elements_array(doc)

    _, element = _find_element_by_id(elements_array, element_id)

    if not element:
        return {
            "status": "error",
            "message": f"元素不存在: {element_id}"
        }

    return {
        "status": "success",
        "element": {
            "id": element.get("id"),
            "type": element.get("type"),
            "x": element.get("x"),
            "y": element.get("y"),
            "width": element.get("width"),
            "height": element.get("height"),
            "text": element.get("text"),
            "strokeColor": element.get("strokeColor"),
            "backgroundColor": element.get("backgroundColor"),
            "boundElements": element.get("boundElements"),
        }
    }


@registry.register(
    "update_element",
    "更新元素的属性 (位置、尺寸、颜色等)",
    UpdateElementArgs
)
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
) -> Dict[str, Any]:
    """更新已存在元素的属性

    Args:
        element_id: 元素 ID
        x: 新的 X 坐标
        y: 新的 Y 坐标
        width: 新的宽度
        height: 新的高度
        text: 新的文本内容
        stroke_color: 新的描边颜色
        bg_color: 新的背景颜色
        context: Agent 上下文

    Returns:
        dict: 包含 status, updated_fields 的结果
    """
    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    elements_array = _get_elements_array(doc)

    index, current = _find_element_by_id(elements_array, element_id)
    if index < 0:
        return {
            "status": "error",
            "message": f"元素不存在: {element_id}"
        }

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
        return {
            "status": "noop",
            "message": "没有需要更新的字段"
        }

    logger.info(f"更新元素: {element_id}", extra={"room": room_id, "fields": updated_fields})

    return {
        "status": "success",
        "message": f"已更新元素 {element_id}",
        "element_id": element_id,
        "updated_fields": updated_fields
    }


@registry.register(
    "delete_elements",
    "删除指定的元素",
    DeleteElementsArgs
)
async def delete_elements(
    element_ids: List[str],
    context: AgentContext = None
) -> Dict[str, Any]:
    """删除指定 ID 的元素

    Args:
        element_ids: 要删除的元素 ID 列表
        context: Agent 上下文

    Returns:
        dict: 包含 status, removed 的结果
    """
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

    return {
        "status": "success",
        "message": f"已删除 {len(removed)} 个元素",
        "removed": removed
    }


@registry.register(
    "clear_canvas",
    "清空画布上的所有元素",
    ClearCanvasArgs
)
async def clear_canvas(
    confirm: bool = True,
    context: AgentContext = None
) -> Dict[str, Any]:
    """清空画布上的所有元素

    Args:
        confirm: 确认标志
        context: Agent 上下文

    Returns:
        dict: 包含 status, message 的结果
    """
    if not confirm:
        return {
            "status": "cancelled",
            "message": "操作已取消"
        }

    room_id = _require_room_id(context)
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    elements_array = _get_elements_array(doc)

    count = len(elements_array)

    with doc.transaction(origin="ai-engine/clear_canvas"):
        elements_array.delete(0, count)

    logger.info(f"清空画布: 删除了 {count} 个元素", extra={"room": room_id})

    return {
        "status": "success",
        "message": f"已清空画布 (删除了 {count} 个元素)"
    }
