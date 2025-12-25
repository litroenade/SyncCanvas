"""模块名称: helpers
主要功能: Excalidraw 工具辅助函数
"""

from __future__ import annotations

import uuid
import random
from typing import Dict, Any, Tuple, Optional
from pycrdt import Array, Map
from src.logger import get_logger
from src.agent.core.context import AgentContext

logger = get_logger(__name__)


def require_room_id(context: Optional["AgentContext"]) -> str:
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


# 主题颜色预设
THEME_COLORS = {
    "light": {
        "stroke": "#1e1e1e",
        "background": "#e0f2fe",  # 浅蓝色背景（亮主题）
        "text": "#1e1e1e",
        "arrow": "#374151",
    },
    "dark": {
        "stroke": "#f1f5f9",  # 白色笔画（深色主题可见）
        "background": "#1e3a5f",  # 深蓝色背景（深色主题）
        "text": "#f8fafc",
        "arrow": "#94a3b8",  # 浅灰色箭头
    },
}


def get_theme_colors(theme: str = "light") -> Dict[str, str]:
    """获取主题颜色

    Args:
        theme: 主题名称 ("light" | "dark")

    Returns:
        Dict: 颜色配置
    """
    return THEME_COLORS.get(theme, THEME_COLORS["light"])


def base_excalidraw_element(
    element_type: str,
    x: float,
    y: float,
    width: float,
    height: float,
    stroke_color: Optional[str] = None,
    bg_color: Optional[str] = None,
    theme: str = "light",
) -> Dict[str, Any]:
    """生成 Excalidraw 元素基础结构

    Args:
        element_type: 元素类型
        x: X 坐标
        y: Y 坐标
        width: 宽度
        height: 高度
        stroke_color: 描边颜色 (可选，默认使用主题色)
        bg_color: 背景颜色 (可选，默认使用主题色)
        theme: 颜色主题 ("light" | "dark")

    Returns:
        dict: Excalidraw 元素字典
    """
    colors = get_theme_colors(theme)

    # 使用传入颜色或主题默认色
    final_stroke = stroke_color if stroke_color else colors["stroke"]
    final_bg = bg_color if bg_color else colors["background"]

    # ========== 数值安全处理: 确保坐标和尺寸是有效数字 ==========
    def safe_float(val: Any, default: float = 0.0) -> float:
        """确保值是有效的浮点数"""
        if val is None:
            return default
        try:
            result = float(val)
            # 检查 NaN 和无穷大
            if result != result or result == float("inf") or result == float("-inf"):
                logger.warning("[safe_float] 无效数值 %s，使用默认值 %s", val, default)
                return default
            return result
        except (TypeError, ValueError):
            logger.warning("[safe_float] 无法转换 %s，使用默认值 %s", val, default)
            return default

    safe_x = safe_float(x, 100.0)
    safe_y = safe_float(y, 100.0)
    safe_width = safe_float(width, 100.0)
    safe_height = safe_float(height, 100.0)
    # ========== 数值安全处理结束 ==========

    base = {
        "id": generate_element_id(element_type),
        "type": element_type,
        "x": safe_x,
        "y": safe_y,
        "width": safe_width,
        "height": safe_height,
        "frameId": None,  # Required for Excalidraw (null for non-frame elements)
        "angle": 0,  # Excalidraw 必需字段
        "strokeColor": final_stroke,
        "backgroundColor": final_bg,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,  # Excalidraw 默认值
        "opacity": 100,
        "groupIds": [],
        "seed": random.randint(1, 100000),
        "version": 1,
        "versionNonce": random.randint(1, 1000000000),
        "isDeleted": False,
        "boundElements": None,  # Excalidraw 官方格式使用 null
        "updated": 1,
        "link": None,
        "locked": False,
    }

    # 根据元素类型添加特定属性
    if element_type in ("rectangle", "diamond", "ellipse"):
        # 形状元素支持圆角
        base["roundness"] = {"type": 3}  # 3 = PROPORTIONAL_RADIUS
    elif element_type in ("arrow", "line"):
        # 线性元素需要 points 数组和绑定信息
        base["points"] = [[0, 0], [safe_width, safe_height]]
        base["startBinding"] = None
        base["endBinding"] = None
        base["startArrowhead"] = None
        base["endArrowhead"] = "arrow" if element_type == "arrow" else None
        base["roundness"] = {"type": 2}  # 2 = ADAPTIVE_RADIUS for lines
        base["backgroundColor"] = "transparent"
        # 线性元素不需要 width/height，由 points 决定
        # 但保留用于边界计算
    elif element_type == "freedraw":
        # 自由绘制元素
        base["points"] = []
        base["pressures"] = []
        base["simulatePressure"] = True
        base["roundness"] = None
    elif element_type == "text":
        # 文本元素不需要圆角
        base["roundness"] = None
    elif element_type == "image":
        # 图片元素
        base["fileId"] = None
        base["status"] = "pending"
        base["scale"] = [1, 1]
        base["roundness"] = None
    elif element_type in ("frame", "magicframe"):
        # 框架元素
        base["name"] = None
        base["roundness"] = None
    else:
        # 其他元素默认圆角
        base["roundness"] = {"type": 3}

    return base


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


def append_element_as_ymap(elements_array: Array, element: Dict[str, Any]) -> None:
    """将元素作为 Y.Map 追加到 Y.Array

    重要：pycrdt.Map 必须先关联到文档才能设置属性。
    正确模式：1) 创建空 Map, 2) append 到 Array, 3) 设置属性

    Args:
        elements_array: 已关联文档的 Y.Array
        element: 要追加的元素字典
    """
    el_id = element.get("id", "unknown")
    el_type = element.get("type", "unknown")
    logger.debug(
        "[append_element_as_ymap] 开始添加元素: id=%s, type=%s, keys=%s",
        el_id,
        el_type,
        list(element.keys()),
    )

    ymap = Map()
    logger.debug(
        "[append_element_as_ymap] 创建空 Map, 准备 append 到 Array (len=%d)",
        len(elements_array),
    )

    elements_array.append(ymap)
    logger.debug("[append_element_as_ymap] Map 已 append, 开始设置属性...")

    for key, value in element.items():
        ymap[key] = value

    logger.info(
        "[append_element_as_ymap] 元素已添加: id=%s, type=%s, array_len=%d",
        el_id,
        el_type,
        len(elements_array),
    )


def update_element_in_array(
    elements_array: Array, element_id: str, updates: Dict[str, Any]
) -> bool:
    """更新 Y.Array 中指定元素的属性

    Args:
        elements_array: Y.Array 元素数组
        element_id: 要更新的元素 ID
        updates: 要更新的属性字典

    Returns:
        bool: 是否找到并更新了元素
    """
    for el in elements_array:
        if isinstance(el, Map):
            if el.get("id") == element_id:
                for key, value in updates.items():
                    el[key] = value
                logger.debug(
                    "[update_element_in_array] 已更新元素: id=%s, keys=%s",
                    element_id,
                    list(updates.keys()),
                )
                return True
    return False
