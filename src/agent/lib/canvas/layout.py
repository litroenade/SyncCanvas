"""模块名称: layout
主要功能: 图表布局引擎
"""

from typing import List, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field

from src.logger import get_logger
from src.config import config

# 从 helpers 导入主题颜色函数
from .helpers import get_theme_colors

logger = get_logger(__name__)


class LayoutDirection(Enum):
    """布局方向"""

    TOP_TO_BOTTOM = "TB"
    LEFT_TO_RIGHT = "LR"
    BOTTOM_TO_TOP = "BT"
    RIGHT_TO_LEFT = "RL"


class NodeType(Enum):
    """节点类型"""

    START = "ellipse"  # 开始/结束
    PROCESS = "rectangle"  # 处理
    DECISION = "diamond"  # 判断
    TEXT = "text"  # 文本


def get_node_size(node_type: str, node_count: int = 1) -> Tuple[float, float]:
    """根据节点类型获取尺寸，使用 CanvasConfig 配置

    Args:
        node_type: 节点类型
        node_count: 节点数量（用于动态调整）

    Returns:
        (width, height) 元组
    """
    c = config.canvas
    if node_type == "ellipse":
        return (c.ellipse_width, c.ellipse_height)
    elif node_type == "diamond":
        return (c.diamond_size, c.diamond_size)
    else:
        return (c.node_width, c.node_height)


def get_layout_gaps(node_count: int = 1) -> Tuple[float, float]:
    """获取布局间距，支持动态调整

    Args:
        node_count: 节点数量

    Returns:
        (horizontal_gap, vertical_gap) 元组
    """
    return config.canvas.calculate_dynamic_gaps(node_count)


@dataclass
class LayoutNode:
    """布局节点"""

    id: str
    type: str
    label: str
    x: float = 0
    y: float = 0
    width: float = 160
    height: float = 70
    level: int = 0  # 层级 (用于分层布局)
    column: int = 0  # 列 (用于分支)


@dataclass
class LayoutEdge:
    """布局边"""

    from_id: str
    to_id: str
    label: str = ""


@dataclass
class LayoutResult:
    """布局结果"""

    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)


def build_adjacency(
    nodes: List[Dict], edges: List[Dict]
) -> tuple[Dict[str, List[str]], Dict[str, int]]:
    """构建邻接表和入度表"""
    adjacency: Dict[str, List[str]] = {n["id"]: [] for n in nodes}
    in_degree: Dict[str, int] = {n["id"]: 0 for n in nodes}

    for edge in edges:
        from_id = edge.get("from") or edge.get("from_id", "")
        to_id = edge.get("to") or edge.get("to_id", "")
        if from_id in adjacency and to_id in in_degree:
            adjacency[from_id].append(to_id)
            in_degree[to_id] += 1

    return adjacency, in_degree


def topological_levels(nodes: List[Dict], edges: List[Dict]) -> Dict[str, int]:
    """拓扑排序并分配层级"""
    adjacency, in_degree = build_adjacency(nodes, edges)

    levels: Dict[str, int] = {}
    queue = [n["id"] for n in nodes if in_degree[n["id"]] == 0]

    # 如果没有入度为 0 的节点，从第一个开始
    if not queue and nodes:
        queue = [nodes[0]["id"]]

    current_level = 0

    while queue:
        next_queue = []
        for node_id in queue:
            if node_id not in levels:
                levels[node_id] = current_level

            for child_id in adjacency.get(node_id, []):
                in_degree[child_id] -= 1
                if in_degree[child_id] <= 0 and child_id not in levels:
                    next_queue.append(child_id)

        queue = next_queue
        current_level += 1

    # 处理未分配的节点
    for node in nodes:
        if node["id"] not in levels:
            levels[node["id"]] = current_level
            current_level += 1

    return levels


def calculate_layout(
    structure: Dict[str, Any],
    theme: str = "light",
) -> LayoutResult:
    """
    计算图表布局

    Args:
        structure: 图表结构 {
            "type": "flowchart",
            "direction": "TB",
            "nodes": [{"id": "n1", "type": "ellipse", "label": "开始"}, ...],
            "edges": [{"from": "n1", "to": "n2", "label": ""}, ...]
        }
        theme: 颜色主题 ("light" | "dark")

    Returns:
        LayoutResult: 带坐标的节点和边
    """
    nodes = structure.get("nodes", [])
    edges = structure.get("edges", [])
    direction = structure.get("direction", "TB")

    if not nodes:
        return LayoutResult()

    # 从全局配置获取基础参数
    canvas_config = config.canvas
    node_count = len(nodes)

    colors = get_theme_colors(theme)

    # 1. 拓扑排序分层
    levels = topological_levels(nodes, edges)

    # 2. 统计每层节点数
    level_nodes: Dict[int, List[Dict]] = {}
    for node in nodes:
        level = levels.get(node["id"], 0)
        if level not in level_nodes:
            level_nodes[level] = []
        level_nodes[level].append(node)

    # === 动态间距计算 ===
    # 根据每层最大节点数计算间距，确保不重叠
    max_nodes_per_level = max(len(nodes_list) for nodes_list in level_nodes.values())

    # 获取最大节点尺寸
    max_width, max_height = 0.0, 0.0
    for node in nodes:
        node_type = node.get("type", "rectangle")
        w, h = get_node_size(node_type, node_count)
        max_width = max(max_width, w)
        max_height = max(max_height, h)

    # 动态计算间距：基础间距 + 根据节点数调整
    # 节点越多，间距适当增大
    scale_factor = 1.0 + max(0, (max_nodes_per_level - 2)) * 0.15
    scale_factor = min(scale_factor, 2.0)  # 最大 2 倍

    horizontal_gap = max(50.0, canvas_config.base_horizontal_gap * scale_factor)
    vertical_gap = max(80.0, canvas_config.base_vertical_gap * scale_factor)

    # 3. 计算坐标
    positioned_nodes = []
    node_positions: Dict[str, Tuple[float, float, float, float]] = {}

    for level in sorted(level_nodes.keys()):
        layer_nodes = level_nodes[level]
        layer_width = len(layer_nodes)

        for col, node in enumerate(layer_nodes):
            node_type = node.get("type", "rectangle")
            width, height = get_node_size(node_type, node_count)

            if direction in ("TB", "BT"):
                # 垂直布局：动态计算水平位置
                # 使用最大节点宽度确保间距一致
                cell_width = max_width + horizontal_gap
                total_layer_width = layer_width * cell_width
                start_x = canvas_config.start_x - total_layer_width / 2 + cell_width / 2

                x = start_x + col * cell_width
                y = canvas_config.start_y + level * (max_height + vertical_gap)
            else:
                # 水平布局
                cell_height = max_height + vertical_gap
                total_layer_height = layer_width * cell_height
                start_y = (
                    canvas_config.start_y - total_layer_height / 2 + cell_height / 2
                )

                x = canvas_config.start_x + level * (max_width + horizontal_gap)
                y = start_y + col * cell_height

            positioned_nodes.append(
                {
                    "id": node["id"],
                    "type": node_type,
                    "label": node.get("label", ""),
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "stroke_color": colors["stroke"],
                    "bg_color": colors["background"],
                    "text_color": colors["text"],
                }
            )

            node_positions[node["id"]] = (x, y, width, height)

    # 4. 计算边
    positioned_edges = []
    for edge in edges:
        from_id = edge.get("from") or edge.get("from_id", "")
        to_id = edge.get("to") or edge.get("to_id", "")
        label = edge.get("label", "")

        if from_id in node_positions and to_id in node_positions:
            positioned_edges.append(
                {
                    "from_id": from_id,
                    "to_id": to_id,
                    "label": label,
                }
            )

    logger.info(
        "布局计算完成: %d 节点, %d 连接, 方向=%s, 间距=(%d, %d)",
        len(positioned_nodes),
        len(positioned_edges),
        direction,
        horizontal_gap,
        vertical_gap,
    )

    return LayoutResult(nodes=positioned_nodes, edges=positioned_edges)
