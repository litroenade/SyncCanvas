"""模块名称: helpers
主要功能: Excalidraw 工具辅助函数
"""

import uuid
import random
from typing import Dict, Any, Tuple

from pycrdt import Array, Map

from src.agent.base import AgentContext
from src.logger import get_logger

logger = get_logger(__name__)


def require_room_id(context: AgentContext) -> str:
    """从 AgentContext 获取房间 ID

    Args:
        context: Agent 上下文

    Returns:
        str: 房间 ID

    Raises:
        ValueError: 当 context 为空或没有 session_id 时
    """
    if not context or not context.session_id:
        raise ValueError(
            "room_id (session_id) is required in AgentContext for board tools"
        )
    return context.session_id


def generate_element_id(prefix: str = "el") -> str:
    """生成唯一的元素 ID

    Args:
        prefix: ID 前缀

    Returns:
        str: 唯一 ID
    """
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def base_excalidraw_element(
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
        "id": generate_element_id(element_type),
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
        "roughness": 0,
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


def get_elements_array(doc) -> Array:
    """获取文档中的 elements Y.Array

    Args:
        doc: Y.Doc 文档对象

    Returns:
        Array: elements Y.Array
    """
    return doc.get("elements", type=Array)


def find_element_by_id(elements_array: Array, element_id: str) -> Tuple[int, Any]:
    """在 Y.Array 中查找元素

    Args:
        elements_array: Y.Array 元素数组
        element_id: 要查找的元素 ID

    Returns:
        tuple: (索引, 元素数据) 或 (-1, None)
    """
    for i, el in enumerate(elements_array):
        if isinstance(el, Map):
            if el.get("id") == element_id:
                return i, dict(el)
        elif isinstance(el, dict):
            if el.get("id") == element_id:
                return i, el
    return -1, None


def element_to_ymap(element: Dict[str, Any]) -> Dict[str, Any]:
    """将元素字典转换为可 append 的格式

    注意: pycrdt Array 可以直接 append dict，会自动转换为 Y.Map。
    不需要手动创建 Map() 对象。

    Args:
        element: 元素字典

    Returns:
        Dict: 元素字典（直接返回）
    """
    return element

