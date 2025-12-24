"""模块名称: flowchart
主要功能: 流程图工具 - 使用精确数学计算生成 Excalidraw 元素
"""

import random
from typing import Optional, Dict, Any

from src.agent.core.context import AgentContext
from src.agent.core.registry import registry, ToolCategory
from src.agent.lib.canvas.schemas import CreateFlowchartNodeArgs, ConnectNodesArgs
from src.agent.lib.canvas.helpers import (
    require_room_id,
    generate_element_id,
    find_element_by_id,
    append_element_as_ymap,
    get_theme_colors,
    update_element_in_array,
)
from src.agent.lib.math.text import calculate_centered_position
from src.agent.lib.math.geometry import Rect, calculate_arrow_points
from src.logger import get_logger

logger = get_logger(__name__)


def create_complete_flowchart_node(
    node_id: str,
    text_id: str,
    label: str,
    node_type: str,
    x: float,
    y: float,
    width: float,
    height: float,
    stroke_color: str,
    bg_color: str,
    text_color: str,
) -> tuple:
    """创建完整的流程图节点（形状 + 绑定文本）

    使用精确数学计算确保文本居中

    Returns:
        (shape_element, text_element) 元组
    """
    # 计算文本居中位置
    text_x, text_y, text_width, text_height = calculate_centered_position(
        container_x=x,
        container_y=y,
        container_width=width,
        container_height=height,
        text=label,
        font_size=18,
        font_family=1,
        line_height=1.25,
    )

    # 创建形状元素
    shape = {
        "id": node_id,
        "type": node_type,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "frameId": None,
        "angle": 0,
        "strokeColor": stroke_color,
        "backgroundColor": bg_color,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "seed": random.randint(1, 100000),
        "version": 1,
        "versionNonce": random.randint(1, 1000000000),
        "isDeleted": False,
        "boundElements": [{"id": text_id, "type": "text"}],
        "updated": 1,
        "link": None,
        "locked": False,
        "roundness": {"type": 3} if node_type in ("rectangle", "ellipse") else None,
    }

    # 创建文本元素
    text_element = {
        "id": text_id,
        "type": "text",
        "x": text_x,
        "y": text_y,
        "width": text_width,
        "height": text_height,
        "frameId": None,
        "angle": 0,
        "strokeColor": text_color,
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
        "roundness": None,
        "text": label,
        "fontSize": 18,
        "fontFamily": 1,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": node_id,
        "originalText": label,
        "autoResize": True,
        "lineHeight": 1.25,
    }

    return shape, text_element


@registry.register(
    "create_flowchart_node",
    "创建流程图节点 (自动绑定文本标签)，返回 element_id 用于后续连接",
    CreateFlowchartNodeArgs,
    category=ToolCategory.CANVAS,
)
async def create_flowchart_node(
    label: str,
    node_type: str = "rectangle",
    x: float = 400,
    y: float = 50,
    width: float = 160,
    height: float = 70,
    stroke_color: str = "",
    bg_color: str = "",
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """创建流程图节点，使用精确数学计算确保正确布局

    Args:
        label: 节点标签文字
        node_type: 节点类型 (rectangle/diamond/ellipse)
        x: X 坐标
        y: Y 坐标
        width: 宽度
        height: 高度
        stroke_color: 描边颜色 (空=使用主题默认)
        bg_color: 背景颜色 (空=使用主题默认)
        context: Agent 上下文

    Returns:
        dict: 包含 status, element_id, text_id 的结果
    """
    if context is None:
        return {"status": "error", "message": "Context is required"}
    room_id = require_room_id(context)
    doc, elements_array = await context.get_room_and_doc()
    if doc is None or elements_array is None:
        return {"status": "error", "message": "Failed to get room doc"}

    # 获取主题颜色
    theme_colors = get_theme_colors(context.theme)
    stroke_color = stroke_color or theme_colors["stroke"]
    bg_color = bg_color or theme_colors["background"]
    text_color = theme_colors["text"]

    # 根据节点类型调整尺寸
    if node_type == "diamond":
        width = max(width, 100)
        height = max(height, 100)
    elif node_type == "ellipse":
        width = max(width, 120)
        height = max(height, 60)

    # 生成 ID
    shape_id = generate_element_id(node_type)
    text_id = generate_element_id("text")

    # 创建完整元素
    shape, text_element = create_complete_flowchart_node(
        node_id=shape_id,
        text_id=text_id,
        label=label,
        node_type=node_type,
        x=x,
        y=y,
        width=width,
        height=height,
        stroke_color=stroke_color,
        bg_color=bg_color,
        text_color=text_color,
    )

    if context.virtual_mode:
        # 虚拟模式：存入 virtual_elements
        context.virtual_elements.append(shape)
        context.virtual_elements.append(text_element)
        context.created_element_ids.append(shape_id)
        logger.info(
            "[create_flowchart_node] 虚拟模式: 创建 shape=%s, text=%s",
            shape_id,
            text_id,
        )
        return {
            "status": "success",
            "message": f"已创建 {node_type} 节点: {label} (虚拟模式)",
            "element_id": shape_id,
            "text_id": text_id,
            "position": {"x": x, "y": y},
            "size": {"width": width, "height": height},
        }

    # 非虚拟模式：写入画布
    with doc.transaction(origin="ai-engine/create_flowchart_node"):
        append_element_as_ymap(elements_array, shape)
        append_element_as_ymap(elements_array, text_element)

    logger.info(
        "创建流程图节点: %s",
        shape_id,
        extra={"room": room_id, "type": node_type, "label": label},
    )

    return {
        "status": "success",
        "message": f"已创建 {node_type} 节点: {label}",
        "element_id": shape_id,
        "text_id": text_id,
        "position": {"x": x, "y": y},
        "size": {"width": width, "height": height},
    }


@registry.register(
    "connect_nodes",
    "用箭头连接两个流程图节点 (使用 create_flowchart_node 返回的 element_id)",
    ConnectNodesArgs,
    category=ToolCategory.CANVAS,
)
async def connect_nodes(
    from_id: str,
    to_id: str,
    label: Optional[str] = None,
    stroke_color: str = "",
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """用箭头连接两个节点，使用智能路径计算

    Args:
        from_id: 起始节点 ID
        to_id: 目标节点 ID
        label: 连线标签 (可选)
        stroke_color: 连线颜色 (空=使用主题默认)
        context: Agent 上下文

    Returns:
        dict: 包含 status, arrow_id 的结果
    """
    if context is None:
        return {"status": "error", "message": "Context is required"}

    # 获取主题颜色
    theme_colors = get_theme_colors(context.theme)
    stroke_color = stroke_color or theme_colors["arrow"]
    room_id = require_room_id(context)
    doc, elements_array = await context.get_room_and_doc()
    if doc is None or elements_array is None:
        return {"status": "error", "message": "Failed to get room doc"}

    # 查找节点（从画布或虚拟元素中）
    start_node = None
    end_node = None

    # 先从虚拟元素中查找
    if context.virtual_mode and context.virtual_elements:
        for el in context.virtual_elements:
            if el.get("id") == from_id:
                start_node = el
            if el.get("id") == to_id:
                end_node = el

    # 如果虚拟元素中没有，从画布查找
    if not start_node:
        _, start_node = find_element_by_id(elements_array, from_id)
    if not end_node:
        _, end_node = find_element_by_id(elements_array, to_id)

    if not start_node:
        return {
            "status": "error",
            "message": f"找不到起始节点: {from_id}",
            "from_id": from_id,
            "to_id": to_id,
        }

    if not end_node:
        return {
            "status": "error",
            "message": f"找不到目标节点: {to_id}",
            "from_id": from_id,
            "to_id": to_id,
        }

    # 使用数学计算获取最佳箭头路径
    from_rect = Rect.from_element(start_node)
    to_rect = Rect.from_element(end_node)
    start_point, points = calculate_arrow_points(from_rect, to_rect, gap=8.0)

    # 创建箭头元素
    arrow_id = generate_element_id("arrow")
    arrow = {
        "id": arrow_id,
        "type": "arrow",
        "x": start_point.x,
        "y": start_point.y,
        "width": abs(points[1][0]) if len(points) > 1 else 0,
        "height": abs(points[1][1]) if len(points) > 1 else 0,
        "frameId": None,
        "angle": 0,
        "strokeColor": stroke_color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
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
        "points": points,
        "startBinding": {
            "elementId": from_id,
            "focus": 0,
            "gap": 8,
            "fixedPoint": None,
        },
        "endBinding": {
            "elementId": to_id,
            "focus": 0,
            "gap": 8,
            "fixedPoint": None,
        },
        "startArrowhead": None,
        "endArrowhead": "arrow",
        "elbowed": False,
        "roundness": {"type": 2},
    }

    created_elements = [arrow]
    label_id = None

    # 如果有标签，创建标签文本
    if label:
        label_id = generate_element_id("label")
        # 标签位于箭头中点
        mid_x = start_point.x + points[1][0] / 2
        mid_y = start_point.y + points[1][1] / 2

        label_element = {
            "id": label_id,
            "type": "text",
            "x": mid_x - len(label) * 4,
            "y": mid_y - 10,
            "width": len(label) * 8,
            "height": 20,
            "frameId": None,
            "angle": 0,
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
            "roundness": None,
            "text": label,
            "fontSize": 14,
            "fontFamily": 1,
            "textAlign": "center",
            "verticalAlign": "middle",
            "originalText": label,
            "autoResize": True,
            "lineHeight": 1.25,
            "containerId": None,
        }
        created_elements.append(label_element)

    if context.virtual_mode:
        # 虚拟模式
        for el in created_elements:
            context.virtual_elements.append(el)
        logger.info(
            "[connect_nodes] 虚拟模式: 创建箭头 %s -> %s",
            from_id,
            to_id,
        )
        return {
            "status": "success",
            "message": f"已连接节点 {from_id} -> {to_id}"
            + (f" (标签: {label})" if label else ""),
            "arrow_id": arrow_id,
            "label_id": label_id,
        }

    # 非虚拟模式：写入画布
    with doc.transaction(origin="ai-engine/connect_nodes"):
        for el in created_elements:
            append_element_as_ymap(elements_array, el)

        # 更新起始节点的 boundElements（双向绑定）
        start_bound = start_node.get("boundElements") or []
        if not isinstance(start_bound, list):
            start_bound = []
        if not any(b.get("id") == arrow_id for b in start_bound if isinstance(b, dict)):
            start_bound.append({"id": arrow_id, "type": "arrow"})
            update_element_in_array(
                elements_array, from_id, {"boundElements": start_bound}
            )

        # 更新结束节点的 boundElements
        end_bound = end_node.get("boundElements") or []
        if not isinstance(end_bound, list):
            end_bound = []
        if not any(b.get("id") == arrow_id for b in end_bound if isinstance(b, dict)):
            end_bound.append({"id": arrow_id, "type": "arrow"})
            update_element_in_array(elements_array, to_id, {"boundElements": end_bound})

    logger.info(
        "创建连接: %s",
        arrow_id,
        extra={"room": room_id, "from": from_id, "to": to_id, "label": label},
    )

    return {
        "status": "success",
        "message": f"已连接节点 {from_id} -> {to_id}"
        + (f" (标签: {label})" if label else ""),
        "arrow_id": arrow_id,
        "label_id": label_id,
    }
