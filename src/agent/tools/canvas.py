"""模块名称: canvas
主要功能: 画布状态工具

提供画布状态查询:
- get_canvas_bounds: 获取画布边界和建议绘图位置
"""

from typing import Dict, Any

from pycrdt import Map

from src.agent.core.agent import AgentContext
from src.agent.core.tools import registry, ToolCategory
from src.agent.tools.schemas import GetCanvasBoundsArgs
from src.agent.tools.helpers import require_room_id, get_room_and_doc
from src.logger import get_logger

logger = get_logger(__name__)


@registry.register(
    "get_canvas_bounds",
    "获取画布上现有元素的边界范围，用于确定新元素的放置位置",
    GetCanvasBoundsArgs,
    category=ToolCategory.CANVAS,
)
async def get_canvas_bounds(context: AgentContext = None) -> Dict[str, Any]:
    """获取画布上现有元素的边界范围

    计算所有元素的包围盒，返回最小/最大坐标和建议的绘图起始位置。
    如果画布为空，返回默认的起始位置。

    Args:
        context: Agent 上下文

    Returns:
        dict: 包含边界信息和建议绘图位置
    """
    room_id = require_room_id(context)
    _, _, elements_array = await get_room_and_doc(room_id)

    if len(elements_array) == 0:
        return {
            "status": "success",
            "is_empty": True,
            "bounds": None,
            "suggested_start": {"x": 100, "y": 100},
            "message": "画布为空，建议从 (100, 100) 开始绘制",
        }

    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")
    element_count = 0

    for i in range(len(elements_array)):
        el = elements_array[i]
        if isinstance(el, Map):
            el = dict(el)

        if el.get("isDeleted"):
            continue

        x = el.get("x", 0)
        y = el.get("y", 0)
        w = el.get("width", 0)
        h = el.get("height", 0)

        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x + w)
        max_y = max(max_y, y + h)
        element_count += 1

    if element_count == 0:
        return {
            "status": "success",
            "is_empty": True,
            "bounds": None,
            "suggested_start": {"x": 100, "y": 100},
            "message": "画布为空，建议从 (100, 100) 开始绘制",
        }

    width = max_x - min_x
    height = max_y - min_y

    if width > height * 1.5:
        suggested_x = min_x
        suggested_y = max_y + 100
    else:
        suggested_x = max_x + 100
        suggested_y = min_y

    return {
        "status": "success",
        "is_empty": False,
        "bounds": {
            "min_x": round(min_x, 1),
            "min_y": round(min_y, 1),
            "max_x": round(max_x, 1),
            "max_y": round(max_y, 1),
            "width": round(width, 1),
            "height": round(height, 1),
            "center_x": round((min_x + max_x) / 2, 1),
            "center_y": round((min_y + max_y) / 2, 1),
        },
        "element_count": element_count,
        "suggested_start": {"x": round(suggested_x, 1), "y": round(suggested_y, 1)},
        "message": f"画布有 {element_count} 个元素，建议从 ({suggested_x:.0f}, {suggested_y:.0f}) 开始绘制",
    }
