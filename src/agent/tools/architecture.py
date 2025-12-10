"""模块名称: architecture
主要功能: 架构图工具

提供架构图绘制功能:
- create_container: 创建分组容器
- create_component: 创建组件节点
"""

import random
from typing import Dict, Any

from src.agent.core.agent import AgentContext
from src.agent.core.tools import registry, ToolCategory
from src.agent.tools.schemas import CreateContainerArgs, CreateComponentArgs
from src.agent.tools.helpers import (
    require_room_id,
    generate_element_id,
    base_excalidraw_element,
    element_to_ymap,
    get_room_and_doc,
)
from src.logger import get_logger

logger = get_logger(__name__)


@registry.register(
    "create_container",
    "创建架构图中的分组容器 (如 '前端', '后端' 区域框)，包含标题和可放置组件的区域",
    CreateContainerArgs,
    category=ToolCategory.CANVAS,
)
async def create_container(
    title: str,
    x: float,
    y: float,
    width: float = 300,
    height: float = 400,
    stroke_color: str = "#a1a1aa",
    bg_color: str = "#fafafa",
    title_color: str = "#71717a",
    context: AgentContext = None,
) -> Dict[str, Any]:
    """创建架构图容器

    创建一个带标题的分组容器框，用于组织架构图中的相关组件。
    容器由一个圆角矩形背景和顶部标题组成。

    Args:
        title: 容器标题
        x: 左上角 X 坐标
        y: 左上角 Y 坐标
        width: 容器宽度
        height: 容器高度
        stroke_color: 边框颜色
        bg_color: 背景颜色
        title_color: 标题文字颜色
        context: Agent 上下文

    Returns:
        dict: 包含 status, container_id, title_id 的结果
    """
    room_id = require_room_id(context)
    _, doc, elements_array = await get_room_and_doc(room_id)

    # 创建容器背景矩形
    container_id = generate_element_id("container")
    container = base_excalidraw_element(
        "rectangle", x, y, width, height, stroke_color, bg_color
    )
    container.update(
        {
            "id": container_id,
            "strokeWidth": 1,
            "strokeStyle": "dashed",
            "roundness": {"type": 3},
            "opacity": 60,
        }
    )

    # 创建标题文本
    title_id = generate_element_id("title")
    title_element = {
        "id": title_id,
        "type": "text",
        "x": x + 15,
        "y": y + 10,
        "width": width - 30,
        "height": 24,
        "strokeColor": title_color,
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
        "text": title,
        "fontSize": 16,
        "fontFamily": 1,
        "textAlign": "left",
        "verticalAlign": "top",
        "originalText": title,
    }

    with doc.transaction(origin="ai-engine/create_container"):
        elements_array.append(element_to_ymap(container))
        elements_array.append(element_to_ymap(title_element))

    logger.info(f"创建容器: {container_id}", extra={"room": room_id, "title": title})

    return {
        "status": "success",
        "message": f"已创建容器: {title}",
        "container_id": container_id,
        "title_id": title_id,
        "content_area": {
            "x": x + 15,
            "y": y + 45,
            "width": width - 30,
            "height": height - 60,
        },
    }


@registry.register(
    "create_component",
    "创建架构图中的组件节点 (如 'REST API', 'SQLite' 等服务/数据库组件)",
    CreateComponentArgs,
    category=ToolCategory.CANVAS,
)
async def create_component(
    label: str,
    component_type: str = "service",
    x: float = 0,
    y: float = 0,
    width: float = 150,
    height: float = 50,
    stroke_color: str = "#6b7280",
    bg_color: str = "#f3f4f6",
    context: AgentContext = None,
) -> Dict[str, Any]:
    """创建架构图组件

    根据组件类型创建适当形状的节点:
    - service: 圆角矩形 (服务/API)
    - database: 椭圆形 (数据库)
    - module: 矩形 (模块/功能块)
    - client: 圆角矩形带阴影 (客户端/用户)

    Args:
        label: 组件标签
        component_type: 组件类型
        x: X 坐标
        y: Y 坐标
        width: 宽度
        height: 高度
        stroke_color: 边框颜色
        bg_color: 背景颜色
        context: Agent 上下文

    Returns:
        dict: 包含 status, element_id, text_id 的结果
    """
    room_id = require_room_id(context)
    _, doc, elements_array = await get_room_and_doc(room_id)

    # 根据组件类型选择形状
    if component_type == "database":
        element_type = "ellipse"
        height = max(height, 60)
    else:
        element_type = "rectangle"

    # 创建组件形状
    component_id = generate_element_id("component")
    component = base_excalidraw_element(
        element_type, x, y, width, height, stroke_color, bg_color
    )
    component.update(
        {
            "id": component_id,
            "strokeWidth": 2,
        }
    )

    # 服务和客户端类型使用圆角
    if component_type in ("service", "client", "module"):
        component["roundness"] = {"type": 3}

    # 创建标签文本
    text_id = generate_element_id("label")
    text_x = x + width / 2
    text_y = y + height / 2

    text_element = {
        "id": text_id,
        "type": "text",
        "x": text_x,
        "y": text_y,
        "width": width - 10,
        "height": 18,
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
        "fontSize": 14,
        "fontFamily": 1,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": component_id,
        "originalText": label,
        "autoResize": True,
    }

    # 更新组件的 boundElements
    component["boundElements"] = [{"id": text_id, "type": "text"}]

    with doc.transaction(origin="ai-engine/create_component"):
        elements_array.append(element_to_ymap(component))
        elements_array.append(element_to_ymap(text_element))

    logger.info(
        f"创建组件: {component_id}",
        extra={"room": room_id, "type": component_type, "label": label},
    )

    return {
        "status": "success",
        "message": f"已创建 {component_type} 组件: {label}",
        "element_id": component_id,
        "text_id": text_id,
        "position": {"x": x, "y": y},
        "size": {"width": width, "height": height},
    }
