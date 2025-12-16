"""模块名称: elements
主要功能: 基础元素操作工具
"""

import random
from typing import Optional, List, Dict, Any

from pycrdt import Map

from src.agent.base import AgentContext
from src.agent.registry import registry, ToolCategory
from src.agent.tools.schemas import (
    CreateExcalidrawElementArgs,
    ListElementsArgs,
    GetElementByIdArgs,
    UpdateElementArgs,
    DeleteElementsArgs,
    ClearCanvasArgs,
    BatchCreateElementsArgs,
)
from src.agent.tools.helpers import (
    require_room_id,
    base_excalidraw_element,
    find_element_by_id,
    element_to_ymap,
    get_room_and_doc,
)
from src.logger import get_logger

logger = get_logger(__name__)


@registry.register(
    "create_element",
    "在画布上创建基础 Excalidraw 元素",
    CreateExcalidrawElementArgs,
    category=ToolCategory.CANVAS,
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
    room_id = require_room_id(context)
    _, doc, elements_array = await get_room_and_doc(room_id)

    element = base_excalidraw_element(
        element_type, x, y, width, height, stroke_color, bg_color
    )

    if element_type == "text":
        element.update(
            {
                "text": text or "文本",
                "fontSize": 20,
                "fontFamily": 1,
                "textAlign": "left",
                "verticalAlign": "top",
                "originalText": text or "文本",
            }
        )

    with doc.transaction(origin="ai-engine/create_element"):
        elements_array.append(element_to_ymap(element))

    logger.info(
        "创建元素: %s", element["id"], extra={"room": room_id, "type": element_type}
    )

    return {
        "status": "success",
        "message": f"已创建 {element_type}",
        "element_id": element["id"],
    }


@registry.register(
    "list_elements",
    "列出画布上的元素摘要信息",
    ListElementsArgs,
    category=ToolCategory.CANVAS,
)
async def list_elements(
    limit: int = 30,
    context: AgentContext = None,
) -> Dict[str, Any]:
    """获取画布上的元素列表摘要

    Args:
        limit: 返回的元素数量上限
        context: Agent 上下文

    Returns:
        dict: 包含 status, total, elements 的结果
    """
    room_id = require_room_id(context)
    _, _, elements_array = await get_room_and_doc(room_id)

    elements = []
    for i in range(min(len(elements_array), limit)):
        el = elements_array[i]
        if isinstance(el, Map):
            el = dict(el)

        if el.get("isDeleted"):
            continue

        elements.append(
            {
                "id": el.get("id"),
                "type": el.get("type"),
                "x": round(el.get("x", 0), 1),
                "y": round(el.get("y", 0), 1),
                "width": round(el.get("width", 0), 1),
                "height": round(el.get("height", 0), 1),
                "text": el.get("text", "")[:50] if el.get("text") else None,
            }
        )

    return {
        "status": "success",
        "total": len(elements_array),
        "shown": len(elements),
        "elements": elements,
    }


@registry.register(
    "get_element",
    "获取指定元素的详细信息",
    GetElementByIdArgs,
    category=ToolCategory.CANVAS,
)
async def get_element(
    element_id: str,
    context: AgentContext = None,
) -> Dict[str, Any]:
    """获取指定元素的详细信息

    Args:
        element_id: 元素 ID
        context: Agent 上下文

    Returns:
        dict: 包含元素详细信息的结果
    """
    room_id = require_room_id(context)
    _, _, elements_array = await get_room_and_doc(room_id)

    _, element = find_element_by_id(elements_array, element_id)

    if not element:
        return {"status": "error", "message": f"元素不存在: {element_id}"}

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
        },
    }


@registry.register(
    "update_element",
    "更新元素的属性 (位置、尺寸、颜色等)",
    UpdateElementArgs,
    category=ToolCategory.CANVAS,
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
    room_id = require_room_id(context)
    _, doc, elements_array = await get_room_and_doc(room_id)

    index, current = find_element_by_id(elements_array, element_id)
    if index < 0:
        return {"status": "error", "message": f"元素不存在: {element_id}"}

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

        y_map["version"] = current.get("version", 0) + 1
        y_map["versionNonce"] = random.randint(1, 1000000000)

    if not updated_fields:
        return {"status": "noop", "message": "没有需要更新的字段"}

    logger.info(
        "更新元素: %s", element_id, extra={"room": room_id, "fields": updated_fields}
    )

    return {
        "status": "success",
        "message": f"已更新元素 {element_id}",
        "element_id": element_id,
        "updated_fields": updated_fields,
    }


@registry.register(
    "delete_elements",
    "删除指定的元素",
    DeleteElementsArgs,
    category=ToolCategory.CANVAS,
)
async def delete_elements(
    element_ids: List[str],
    context: AgentContext = None,
) -> Dict[str, Any]:
    """删除指定 ID 的元素

    Args:
        element_ids: 要删除的元素 ID 列表
        context: Agent 上下文

    Returns:
        dict: 包含 status, removed 的结果
    """
    room_id = require_room_id(context)
    _, doc, elements_array = await get_room_and_doc(room_id)

    removed = []
    id_set = set(element_ids)

    with doc.transaction(origin="ai-engine/delete_elements"):
        for i in range(len(elements_array) - 1, -1, -1):
            el = elements_array[i]
            el_id = el.get("id") if isinstance(el, Map) else el.get("id")
            if el_id in id_set:
                elements_array.delete(i, 1)
                removed.append(el_id)

    logger.info("删除元素: %d 个", len(removed), extra={"room": room_id})

    return {
        "status": "success",
        "message": f"已删除 {len(removed)} 个元素",
        "removed": removed,
    }


@registry.register(
    "clear_canvas",
    "清空画布上的所有元素",
    ClearCanvasArgs,
    category=ToolCategory.CANVAS,
    dangerous=True,
)
async def clear_canvas(
    confirm: bool = True,
    context: AgentContext = None,
) -> Dict[str, Any]:
    """清空画布上的所有元素

    Args:
        confirm: 确认标志
        context: Agent 上下文

    Returns:
        dict: 包含 status, message 的结果
    """
    if not confirm:
        return {"status": "cancelled", "message": "操作已取消"}

    room_id = require_room_id(context)
    _, doc, elements_array = await get_room_and_doc(room_id)

    count = len(elements_array)

    with doc.transaction(origin="ai-engine/clear_canvas"):
        elements_array.delete(0, count)

    logger.info("清空画布: 删除了 %d 个元素", count, extra={"room": room_id})

    return {"status": "success", "message": f"已清空画布 (删除了 {count} 个元素)"}


# ==================== 批量创建工具 (JSON 规划层支持) ====================


@registry.register(
    "batch_create_elements",
    "批量创建流程图元素和连接线 (支持 JSON 规划)",
    BatchCreateElementsArgs,
    category=ToolCategory.CANVAS,
)
async def batch_create_elements(
    elements: list,
    edges: list = None,
    context: AgentContext = None,
) -> Dict[str, Any]:
    """批量创建元素和连接线

    接收 LLM 输出的 JSON 规划，一次性创建所有元素和连接。

    Args:
        elements: 元素规格列表，每项包含 {id, type, label, x, y, width, height, ...}
        edges: 边规格列表，每项包含 {from_id, to_id, label}
        context: Agent 上下文

    Returns:
        dict: 包含 status, created_elements, created_edges 的结果
    """
    room_id = require_room_id(context)
    _, doc, elements_array = await get_room_and_doc(room_id)

    edges = edges or []

    # 临时 ID 到真实 ID 的映射
    id_mapping: Dict[str, str] = {}
    created_elements = []
    created_edges = []

    with doc.transaction(origin="ai-engine/batch_create_elements"):
        # 1. 创建所有元素
        for spec in elements:
            temp_id = spec.get("id", "")
            elem_type = spec.get("type", "rectangle")
            label = spec.get("label", "")
            x = spec.get("x", 0)
            y = spec.get("y", 0)
            width = spec.get("width", 160)
            height = spec.get("height", 70)
            stroke_color = spec.get("stroke_color", "#1e1e1e")
            bg_color = spec.get("bg_color", "#ffffff")

            # 创建形状元素
            shape = base_excalidraw_element(
                elem_type, x, y, width, height, stroke_color, bg_color
            )
            shape_id = shape["id"]
            id_mapping[temp_id] = shape_id

            # 矩形添加圆角
            if elem_type == "rectangle":
                shape["roundness"] = {"type": 3}

            # 创建绑定的文本元素
            text_id = f"text_{shape_id}"
            text_element = {
                "id": text_id,
                "type": "text",
                "x": x + width / 2,
                "y": y + height / 2,
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

            elements_array.append(element_to_ymap(shape))
            elements_array.append(element_to_ymap(text_element))

            created_elements.append(
                {
                    "temp_id": temp_id,
                    "element_id": shape_id,
                    "text_id": text_id,
                    "label": label,
                }
            )

        # 2. 创建所有连接线
        for edge in edges:
            from_temp_id = edge.get("from_id", "")
            to_temp_id = edge.get("to_id", "")
            edge_label = edge.get("label")

            from_id = id_mapping.get(from_temp_id)
            to_id = id_mapping.get(to_temp_id)

            if not from_id or not to_id:
                continue

            # 查找节点位置
            from_node = None
            to_node = None
            for el in elements_array:
                if isinstance(el, Map):
                    el = dict(el)
                if el.get("id") == from_id:
                    from_node = el
                if el.get("id") == to_id:
                    to_node = el

            if not from_node or not to_node:
                continue

            # 计算连接点
            start_x = from_node.get("x", 0) + from_node.get("width", 100) / 2
            start_y = from_node.get("y", 0) + from_node.get("height", 100)
            end_x = to_node.get("x", 0) + to_node.get("width", 100) / 2
            end_y = to_node.get("y", 0)

            # 创建箭头
            arrow = base_excalidraw_element(
                "arrow",
                start_x,
                start_y,
                abs(end_x - start_x),
                abs(end_y - start_y),
                "#1e1e1e",
                "transparent",
            )
            arrow.update(
                {
                    "points": [[0, 0], [end_x - start_x, end_y - start_y]],
                    "startBinding": {"elementId": from_id, "focus": 0, "gap": 4},
                    "endBinding": {"elementId": to_id, "focus": 0, "gap": 4},
                    "startArrowhead": None,
                    "endArrowhead": "arrow",
                    "strokeWidth": 2,
                }
            )

            elements_array.append(element_to_ymap(arrow))

            created_edges.append(
                {
                    "arrow_id": arrow["id"],
                    "from_id": from_id,
                    "to_id": to_id,
                    "label": edge_label,
                }
            )

    logger.info(
        "批量创建: %d 元素, %d 连接",
        len(created_elements),
        len(created_edges),
        extra={"room": room_id},
    )

    return {
        "status": "success",
        "message": f"已创建 {len(created_elements)} 个元素和 {len(created_edges)} 条连接线",
        "created_elements": created_elements,
        "created_edges": created_edges,
        "id_mapping": id_mapping,
    }
