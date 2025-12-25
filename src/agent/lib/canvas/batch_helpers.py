import random
from typing import Dict, Any, List, Tuple, Optional

from pycrdt import Map

from .helpers import base_excalidraw_element
from .constants import (
    DEFAULT_NODE_WIDTH,
    DEFAULT_NODE_HEIGHT,
    DEFAULT_FONT_SIZE,
    DEFAULT_FONT_FAMILY,
    DEFAULT_LINE_HEIGHT,
    DEFAULT_OPACITY,
    SEED_RANGE,
    VERSION_NONCE_RANGE,
    DEFAULT_STROKE_WIDTH,
)


def create_shape_and_text(
    spec: Dict[str, Any],
    theme_colors: Dict[str, str],
    id_mapping: Dict[str, str],
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """创建形状元素和绑定的文本元素

    Args:
        spec: 元素规格，包含 {id, type, label, x, y, width, height, ...}
        theme_colors: 主题颜色配置
        id_mapping: 临时 ID 到真实 ID 的映射（会被更新）

    Returns:
        Tuple[shape, text_element, created_info]:
            - shape: 形状元素字典
            - text_element: 文本元素字典
            - created_info: 创建信息 {temp_id, element_id, text_id, label}
    """
    temp_id: str = spec.get("id", "")
    elem_type: str = spec.get("type", "rectangle")
    label: str = spec.get("label", "")
    x: float = spec.get("x", 0)
    y: float = spec.get("y", 0)
    width: float = spec.get("width", DEFAULT_NODE_WIDTH)
    height: float = spec.get("height", DEFAULT_NODE_HEIGHT)
    stroke_color: str = spec.get("stroke_color") or theme_colors["stroke"]
    bg_color: str = spec.get("bg_color") or theme_colors["background"]

    # 创建形状元素
    shape = base_excalidraw_element(
        elem_type, x, y, width, height, stroke_color, bg_color
    )
    shape_id: str = shape["id"]
    id_mapping[temp_id] = shape_id

    # 矩形添加圆角
    if elem_type == "rectangle":
        shape["roundness"] = {"type": 3}

    # 创建绑定的文本元素
    text_id: str = f"text_{shape_id}"

    # 安全数值处理
    safe_x: float = float(x) if x is not None else 0.0
    safe_y: float = float(y) if y is not None else 0.0
    safe_width: float = float(width) if width is not None else DEFAULT_NODE_WIDTH
    safe_height: float = float(height) if height is not None else DEFAULT_NODE_HEIGHT

    text_element: Dict[str, Any] = {
        "id": text_id,
        "type": "text",
        "x": safe_x + safe_width / 2,
        "y": safe_y + safe_height / 2,
        "width": max(safe_width - 20, 20),
        "height": 20,
        "frameId": None,
        "angle": 0,
        "strokeColor": stroke_color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": DEFAULT_OPACITY,
        "groupIds": [],
        "seed": random.randint(*SEED_RANGE),
        "version": 1,
        "versionNonce": random.randint(*VERSION_NONCE_RANGE),
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "text": label or "",
        "fontSize": DEFAULT_FONT_SIZE,
        "fontFamily": DEFAULT_FONT_FAMILY,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": shape_id,
        "originalText": label or "",
        "autoResize": True,
        "lineHeight": DEFAULT_LINE_HEIGHT,
    }

    # 更新形状的 boundElements
    shape["boundElements"] = [{"id": text_id, "type": "text"}]

    created_info: Dict[str, Any] = {
        "temp_id": temp_id,
        "element_id": shape_id,
        "text_id": text_id,
        "label": label,
    }

    return shape, text_element, created_info


def create_arrow_between_nodes(
    edge: Dict[str, Any],
    id_mapping: Dict[str, str],
    elements_source: List[Dict[str, Any]],
    theme_colors: Dict[str, str],
) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """创建连接两个节点的箭头

    Args:
        edge: 边规格 {from_id, to_id, label}
        id_mapping: 临时 ID 到真实 ID 的映射
        elements_source: 元素列表（用于查找节点位置）
        theme_colors: 主题颜色配置

    Returns:
        Tuple[arrow, edge_info] 或 None（找不到节点时）
    """
    from_temp_id: str = edge.get("from_id", "")
    to_temp_id: str = edge.get("to_id", "")
    edge_label: Optional[str] = edge.get("label")

    from_id: Optional[str] = id_mapping.get(from_temp_id)
    to_id: Optional[str] = id_mapping.get(to_temp_id)

    if not from_id or not to_id:
        return None

    # 查找节点位置
    from_node: Optional[Dict[str, Any]] = None
    to_node: Optional[Dict[str, Any]] = None

    for el in elements_source:
        # 处理 Y.Map 或普通 dict
        if isinstance(el, Map):
            el = dict(el)
        el_id = el.get("id")
        if el_id == from_id:
            from_node = el
        if el_id == to_id:
            to_node = el

    if not from_node or not to_node:
        return None

    # 计算连接点
    start_x: float = from_node.get("x", 0) + from_node.get("width", 100) / 2
    start_y: float = from_node.get("y", 0) + from_node.get("height", 100)
    end_x: float = to_node.get("x", 0) + to_node.get("width", 100) / 2
    end_y: float = to_node.get("y", 0)

    # 创建箭头
    arrow = base_excalidraw_element(
        "arrow",
        start_x,
        start_y,
        abs(end_x - start_x),
        abs(end_y - start_y),
        theme_colors["arrow"],
        "transparent",
    )
    arrow.update(
        {
            "points": [[0, 0], [end_x - start_x, end_y - start_y]],
            "startBinding": {"elementId": from_id, "focus": 0, "gap": 4},
            "endBinding": {"elementId": to_id, "focus": 0, "gap": 4},
            "startArrowhead": None,
            "endArrowhead": "arrow",
            "strokeWidth": DEFAULT_STROKE_WIDTH,
        }
    )

    edge_info: Dict[str, Any] = {
        "arrow_id": arrow["id"],
        "from_id": from_id,
        "to_id": to_id,
        "label": edge_label,
    }

    return arrow, edge_info
