"""模块名称: flowchart
主要功能: 流程图工具
"""

import random
from typing import Optional, Dict, Any

from src.agent.core.context import AgentContext
from src.agent.core.registry import registry, ToolCategory
from src.agent.lib.canvas.schemas import CreateFlowchartNodeArgs, ConnectNodesArgs
from src.agent.lib.canvas.helpers import (
    require_room_id,
    generate_element_id,
    base_excalidraw_element,
    find_element_by_id,
    append_element_as_ymap,
    get_theme_colors,
    update_element_in_array,
)
from src.logger import get_logger

logger = get_logger(__name__)


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
    """创建流程图节点，包含形状和绑定的文本

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

    # 根据节点类型调整尺寸
    if node_type == "diamond":
        width = max(width, 120)
        height = max(height, 120)
    elif node_type == "ellipse":
        width = max(width, 120)
        height = max(height, 50)

    # 创建形状元素
    shape_id = generate_element_id(node_type)
    shape = base_excalidraw_element(
        node_type, x, y, width, height, stroke_color, bg_color, theme=context.theme
    )
    shape["id"] = shape_id

    # 矩形添加圆角
    if node_type == "rectangle":
        shape["roundness"] = {"type": 3}

    # 创建绑定的文本元素
    text_id = generate_element_id("text")
    text_x = x + width / 2
    text_y = y + height / 2

    text_element = {
        "id": text_id,
        "type": "text",
        "x": text_x,
        "y": text_y,
        "width": width - 20,
        "height": 20,
        "frameId": None,  # Required for Excalidraw
        "angle": 0,  # Excalidraw 必需字段
        "strokeColor": theme_colors["text"],  # 使用主题文本颜色
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
        "roundness": None,  # 文本不需要圆角
        "text": label,
        "fontSize": 18,
        "fontFamily": 1,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": shape_id,  # 绑定到形状容器
        "originalText": label,
        "autoResize": True,  # Excalidraw 必需
        "lineHeight": 1.25,  # Excalidraw 必需
    }

    # 更新形状的 boundElements
    shape["boundElements"] = [{"id": text_id, "type": "text"}]

    if context.virtual_mode:
        context.virtual_elements.append(shape)
        context.virtual_elements.append(text_element)
        context.created_element_ids.append(shape_id)
        logger.info(
            "[create_flowchart_node] 虚拟模式: 已添加 shape=%s, text=%s",
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
            "elements": [shape, text_element],  # 虚拟模式返回完整元素
        }

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
    """用绑定箭头连接两个节点

    Args:
        from_id: 起始节点 ID
        to_id: 目标节点 ID
        label: 连线标签 (可选)
        stroke_color: 连线颜色 (空=使用主题默认)
        context: Agent 上下文

    Returns:
        dict: 包含 status, arrow_id, label_id 的结果
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

    # 查找起始和结束节点
    _, start_node = find_element_by_id(elements_array, from_id)
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

    # 确定连接点
    if end_cy > start_cy:
        arrow_start_y = start_y + start_h
        arrow_end_y = end_y
    else:
        arrow_start_y = start_y
        arrow_end_y = end_y + end_h

    # 处理水平方向
    if abs(end_cx - start_cx) > 50:
        if end_cx > start_cx:
            arrow_start_x = start_x + start_w
            arrow_end_x = end_x
        else:
            arrow_start_x = start_x
            arrow_end_x = end_x + end_w
    else:
        arrow_start_x = start_cx
        arrow_end_x = end_cx

    # 创建箭头
    arrow_id = generate_element_id("arrow")
    arrow = base_excalidraw_element(
        "arrow",
        arrow_start_x,
        arrow_start_y,
        abs(arrow_end_x - arrow_start_x),
        abs(arrow_end_y - arrow_start_y),
        stroke_color,
        "transparent",
        theme=context.theme,
    )
    arrow.update(
        {
            "id": arrow_id,
            "points": [
                [0, 0],
                [arrow_end_x - arrow_start_x, arrow_end_y - arrow_start_y],
            ],
            "startBinding": {
                "elementId": from_id,
                "focus": 0,
                "gap": 8,  # 增加间距避免遮挡
                "fixedPoint": None,
            },
            "endBinding": {
                "elementId": to_id,
                "focus": 0,
                "gap": 8,  # 增加间距避免遮挡
                "fixedPoint": None,
            },
            "startArrowhead": None,
            "endArrowhead": "arrow",
            "strokeWidth": 2,
            "elbowed": False,  # 使用曲线箭头，不是折线
            "roundness": {"type": 2},  # 线性元素使用 ADAPTIVE_RADIUS 实现曲线
        }
    )

    created_elements = [arrow]
    label_id = None

    # 如果有标签，创建标签文本
    if label:
        label_id = generate_element_id("label")
        mid_x = (arrow_start_x + arrow_end_x) / 2
        mid_y = (arrow_start_y + arrow_end_y) / 2

        label_element = {
            "id": label_id,
            "type": "text",
            "x": mid_x - 15,
            "y": mid_y - 10,
            "width": 30,
            "height": 20,
            "frameId": None,  # Required for Excalidraw
            "angle": 0,  # Excalidraw 必需字段
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
            "roundness": None,  # 文本不需要圆角
            "text": label,
            "fontSize": 14,
            "fontFamily": 1,
            "textAlign": "center",
            "verticalAlign": "middle",
            "originalText": label,
            "autoResize": True,  # Excalidraw 必需
            "lineHeight": 1.25,  # Excalidraw 必需
            "containerId": None,  # 独立文本，不绑定容器
        }
        created_elements.append(label_element)

    with doc.transaction(origin="ai-engine/connect_nodes"):
        # 添加箭头和标签元素
        for el in created_elements:
            append_element_as_ymap(elements_array, el)

        # 更新起始节点的 boundElements（双向绑定）
        start_bound = start_node.get("boundElements") or []
        if not isinstance(start_bound, list):
            start_bound = []
        # 避免重复添加
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
