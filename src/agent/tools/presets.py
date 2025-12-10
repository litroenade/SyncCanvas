"""模块名称: presets
主要功能: 元素预设和批量操作

提供:
- ELEMENT_PRESETS: 常用流程图元素预设
- create_preset_element: 使用预设创建元素
- batch_update_elements: 批量更新多个元素
"""

from typing import List, Dict, Any

from src.agent.core.agent import AgentContext
from src.agent.core.tools import registry, ToolCategory
from src.agent.tools.schemas import CreatePresetElementArgs, BatchUpdateArgs
from src.agent.tools.flowchart import create_flowchart_node
from src.agent.tools.helpers import (
    require_room_id,
    find_element_by_id,
    get_room_and_doc,
)
from src.logger import get_logger

logger = get_logger(__name__)


# ==================== 元素预设 ====================

ELEMENT_PRESETS = {
    "flowchart_start": {
        "node_type": "ellipse",
        "width": 120,
        "height": 50,
        "stroke_color": "#1e1e1e",
        "bg_color": "#e6f7ff",
    },
    "flowchart_end": {
        "node_type": "ellipse",
        "width": 120,
        "height": 50,
        "stroke_color": "#1e1e1e",
        "bg_color": "#fff1f0",
    },
    "flowchart_process": {
        "node_type": "rectangle",
        "width": 160,
        "height": 70,
        "stroke_color": "#1e1e1e",
        "bg_color": "#ffffff",
    },
    "flowchart_decision": {
        "node_type": "diamond",
        "width": 120,
        "height": 120,
        "stroke_color": "#1e1e1e",
        "bg_color": "#fff7e6",
    },
    "flowchart_io": {
        "node_type": "rectangle",
        "width": 160,
        "height": 60,
        "stroke_color": "#1e1e1e",
        "bg_color": "#f6ffed",
    },
}


@registry.register(
    "create_preset_element",
    f"使用预设创建流程图元素。可用预设: {', '.join(ELEMENT_PRESETS.keys())}",
    CreatePresetElementArgs,
    category=ToolCategory.CANVAS,
)
async def create_preset_element(
    preset: str,
    label: str,
    x: float,
    y: float,
    context: AgentContext = None,
) -> Dict[str, Any]:
    """使用预设创建元素

    Args:
        preset: 预设名称
        label: 元素标签
        x: X 坐标
        y: Y 坐标
        context: Agent 上下文

    Returns:
        dict: 创建结果
    """
    if preset not in ELEMENT_PRESETS:
        return {
            "status": "error",
            "message": f"未知预设: {preset}，可用: {', '.join(ELEMENT_PRESETS.keys())}",
        }

    config = ELEMENT_PRESETS[preset]

    return await create_flowchart_node(
        label=label,
        node_type=config["node_type"],
        x=x,
        y=y,
        width=config["width"],
        height=config["height"],
        stroke_color=config["stroke_color"],
        bg_color=config["bg_color"],
        context=context,
    )


@registry.register(
    "batch_update_elements",
    "批量更新多个元素的属性，减少请求次数",
    BatchUpdateArgs,
    category=ToolCategory.CANVAS,
)
async def batch_update_elements(
    updates: List[Dict[str, Any]],
    context: AgentContext = None,
) -> Dict[str, Any]:
    """批量更新多个元素

    Args:
        updates: 更新列表，每项包含:
            - id: 元素 ID
            - x, y: 新位置 (可选)
            - width, height: 新尺寸 (可选)
            - text: 新文本 (可选)
            - strokeColor, backgroundColor: 新颜色 (可选)
        context: Agent 上下文

    Returns:
        dict: 批量更新结果
    """
    room_id = require_room_id(context)
    _, doc, elements_array = await get_room_and_doc(room_id)

    results = []
    updated_count = 0
    error_count = 0

    with doc.transaction(origin="ai-engine/batch_update"):
        for update in updates:
            element_id = update.get("id")
            if not element_id:
                results.append({"id": None, "status": "error", "message": "缺少 id"})
                error_count += 1
                continue

            index, _ = find_element_by_id(elements_array, element_id)
            if index < 0:
                results.append(
                    {
                        "id": element_id,
                        "status": "error",
                        "message": "元素不存在",
                    }
                )
                error_count += 1
                continue

            y_map = elements_array[index]
            updated_fields = []

            # 更新各个字段
            for key in [
                "x",
                "y",
                "width",
                "height",
                "text",
                "strokeColor",
                "backgroundColor",
            ]:
                if key in update and update[key] is not None:
                    y_map[key] = update[key]
                    updated_fields.append(key)
                    if key == "text":
                        y_map["originalText"] = update[key]

            if updated_fields:
                updated_count += 1
                results.append(
                    {
                        "id": element_id,
                        "status": "success",
                        "updated": updated_fields,
                    }
                )
            else:
                results.append(
                    {
                        "id": element_id,
                        "status": "skipped",
                        "message": "无更新字段",
                    }
                )

    logger.info(
        f"批量更新元素: {updated_count} 成功, {error_count} 失败",
        extra={"room": room_id},
    )

    return {
        "status": "success" if error_count == 0 else "partial",
        "updated": updated_count,
        "errors": error_count,
        "results": results[:10],
    }
