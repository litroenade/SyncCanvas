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
    text_color: str = spec.get("text_color") or theme_colors["text"]

    # 创建形状元素
    shape = base_excalidraw_element(
        elem_type, x, y, width, height, stroke_color, bg_color
    )
    shape_id: str = shape["id"]
    id_mapping[temp_id] = shape_id

    # 矩形添加圆角
    if elem_type == "rectangle":
        shape["roundness"] = {"type": 3}
    elif elem_type == "ellipse":
        shape["roundness"] = {"type": 2}

    # 创建绑定的文本元素
    text_id: str = f"text_{shape_id}"

    # === 关键修复：完全依赖 Excalidraw 自动居中 ===
    # 当设置 containerId 时，Excalidraw 会根据 textAlign 和 verticalAlign 自动计算位置
    # x, y 使用容器左上角坐标，Excalidraw 会自动调整
    # width, height 设置为 0，启用 autoResize 让 Excalidraw 自动计算

    text_element: Dict[str, Any] = {
        "id": text_id,
        "type": "text",
        "x": float(x) if x is not None else 0.0,  # 容器左上角 x
        "y": float(y) if y is not None else 0.0,  # 容器左上角 y
        "width": 0,  # Excalidraw 自动计算
        "height": 0,  # Excalidraw 自动计算
        "frameId": None,
        "angle": 0,
        "strokeColor": text_color,
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
        "containerId": shape_id,  # 绑定到容器，触发自动居中
        "originalText": label or "",
        "autoResize": True,  # 启用自动调整大小
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
    direction: str = "TB",
    use_pathfinding: bool = True,  # 启用 A* 路径规划
) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """创建连接两个节点的箭头（A* 避障路由）

    使用 A* 算法寻找避开其他节点的正交路径。
    当路径较复杂时自动使用折线，否则使用直线。

    Args:
        edge: 边规格 {from_id, to_id, label}
        id_mapping: 临时 ID 到真实 ID 的映射
        elements_source: 元素列表（用于查找节点位置和障碍物）
        theme_colors: 主题颜色配置
        direction: 布局方向提示 (TB/BT/LR/RL)
        use_pathfinding: 是否启用 A* 路径规划

    Returns:
        Tuple[arrow, edge_info] 或 None（找不到节点时）
    """
    from ..math.geometry import Rect, get_connection_direction
    from ..math.pathfinding import find_orthogonal_path

    from_temp_id: str = edge.get("from_id", "")
    to_temp_id: str = edge.get("to_id", "")
    edge_label: Optional[str] = edge.get("label")

    from_id: Optional[str] = id_mapping.get(from_temp_id)
    to_id: Optional[str] = id_mapping.get(to_temp_id)

    if not from_id or not to_id:
        return None

    # 查找节点
    from_node: Optional[Dict[str, Any]] = None
    to_node: Optional[Dict[str, Any]] = None
    all_nodes: List[Dict[str, Any]] = []

    for el in elements_source:
        if isinstance(el, Map):
            el = dict(el)
        el_id = el.get("id")
        el_type = el.get("type", "")

        # 收集形状节点作为障碍物
        if el_type not in ("text", "arrow", "line"):
            all_nodes.append(el)

        if el_id == from_id:
            from_node = el
        if el_id == to_id:
            to_node = el

    if not from_node or not to_node:
        return None

    # 创建 Rect 对象用于几何计算
    from_rect = Rect.from_element(from_node)
    to_rect = Rect.from_element(to_node)

    # 智能选择连接方向
    from_dir, to_dir = get_connection_direction(from_rect, to_rect)

    # 获取连接点
    gap: float = 4.0
    start_point = from_rect.edge_center(from_dir)
    end_point = to_rect.edge_center(to_dir)

    # 使用 A* 路径规划
    if use_pathfinding and len(all_nodes) > 2:
        # 排除起点和终点节点
        exclude_ids = {from_id, to_id}
        path_points = find_orthogonal_path(
            start=start_point,
            end=end_point,
            obstacles=all_nodes,
            exclude_ids=exclude_ids,
            # 使用默认常量值，可按需覆盖
        )

        # 转换为相对坐标（Excalidraw 箭头使用相对坐标）
        points: List[List[float]] = [[0, 0]]
        for pt in path_points[1:]:
            rel_x = pt.x - start_point.x
            rel_y = pt.y - start_point.y
            points.append([rel_x, rel_y])

        use_orthogonal = len(points) > 2
    else:
        # 简单路由（无障碍或只有两个节点）
        dx = end_point.x - start_point.x
        dy = end_point.y - start_point.y

        use_orthogonal = False
        points = [[0, 0]]

        # 垂直方向连接但水平有偏移 - 使用 Z 型
        if from_dir in ("top", "bottom") and abs(dx) > 20:
            use_orthogonal = True
            mid_y = dy / 2
            points.append([0, mid_y])
            points.append([dx, mid_y])
            points.append([dx, dy])
        # 水平方向连接但垂直有偏移 - 使用 Z 型
        elif from_dir in ("left", "right") and abs(dy) > 20:
            use_orthogonal = True
            mid_x = dx / 2
            points.append([mid_x, 0])
            points.append([mid_x, dy])
            points.append([dx, dy])
        else:
            points.append([dx, dy])

    # 计算箭头边界
    all_x = [p[0] for p in points]
    all_y = [p[1] for p in points]
    width = max(abs(max(all_x) - min(all_x)), 1)
    height = max(abs(max(all_y) - min(all_y)), 1)

    # 创建箭头元素
    arrow = base_excalidraw_element(
        "arrow",
        start_point.x,
        start_point.y,
        width,
        height,
        theme_colors["arrow"],
        "transparent",
    )

    arrow.update(
        {
            "points": points,
            "startBinding": {"elementId": from_id, "focus": 0, "gap": gap},
            "endBinding": {"elementId": to_id, "focus": 0, "gap": gap},
            "startArrowhead": None,
            "endArrowhead": "arrow",
            "strokeWidth": DEFAULT_STROKE_WIDTH,
            "roundness": {"type": 2} if use_orthogonal else None,
        }
    )

    edge_info: Dict[str, Any] = {
        "arrow_id": arrow["id"],
        "from_id": from_id,
        "to_id": to_id,
        "label": edge_label,
    }

    return arrow, edge_info
