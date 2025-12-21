"""模块名称: layout
主要功能: 图表布局引擎
"""

from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field

from src.logger import get_logger

logger = get_logger(__name__)


class LayoutDirection(Enum):
    """布局方向"""
    TOP_TO_BOTTOM = "TB"
    LEFT_TO_RIGHT = "LR"
    BOTTOM_TO_TOP = "BT"
    RIGHT_TO_LEFT = "RL"


class NodeType(Enum):
    """节点类型"""
    START = "ellipse"      # 开始/结束
    PROCESS = "rectangle"  # 处理
    DECISION = "diamond"   # 判断
    TEXT = "text"          # 文本


@dataclass
class LayoutConfig:
    """布局配置"""
    # 节点尺寸
    node_width: float = 160
    node_height: float = 70
    ellipse_width: float = 120
    ellipse_height: float = 50
    decision_size: float = 120
    
    # 间距
    vertical_gap: float = 100
    horizontal_gap: float = 200
    
    # 起始位置
    start_x: float = 400
    start_y: float = 100


# 主题颜色预设
THEME_COLORS = {
    "light": {
        "stroke": "#1e1e1e",
        "background": "#a5d8ff",
        "text": "#1e1e1e",
        "arrow": "#1e1e1e",
    },
    "dark": {
        "stroke": "#e2e8f0",
        "background": "#3b82f6",
        "text": "#f8fafc",
        "arrow": "#e2e8f0",
    },
}


def get_theme_colors(theme: str = "light") -> Dict[str, str]:
    """获取主题颜色"""
    return THEME_COLORS.get(theme, THEME_COLORS["light"])


def get_node_size(node_type: str, config: LayoutConfig) -> tuple[float, float]:
    """获取节点尺寸"""
    if node_type == "ellipse":
        return (config.ellipse_width, config.ellipse_height)
    elif node_type == "diamond":
        return (config.decision_size, config.decision_size)
    else:
        return (config.node_width, config.node_height)


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


def topological_levels(
    nodes: List[Dict], edges: List[Dict]
) -> Dict[str, int]:
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
    config: Optional[LayoutConfig] = None,
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
        config: 布局配置
        theme: 颜色主题 ("light" | "dark")
    
    Returns:
        LayoutResult: 带坐标的节点和边
    """
    if config is None:
        config = LayoutConfig()
    
    nodes = structure.get("nodes", [])
    edges = structure.get("edges", [])
    direction = structure.get("direction", "TB")
    
    if not nodes:
        return LayoutResult()
    
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
    
    # 3. 计算坐标
    positioned_nodes = []
    node_positions: Dict[str, tuple[float, float, float, float]] = {}
    
    for level in sorted(level_nodes.keys()):
        layer_nodes = level_nodes[level]
        layer_width = len(layer_nodes)
        
        for col, node in enumerate(layer_nodes):
            node_type = node.get("type", "rectangle")
            width, height = get_node_size(node_type, config)
            
            if direction in ("TB", "BT"):
                # 垂直布局
                x = config.start_x + (col - layer_width / 2 + 0.5) * config.horizontal_gap
                y = config.start_y + level * (height + config.vertical_gap)
            else:
                # 水平布局
                x = config.start_x + level * (width + config.horizontal_gap)
                y = config.start_y + (col - layer_width / 2 + 0.5) * config.vertical_gap
            
            positioned_nodes.append({
                "id": node["id"],
                "type": node_type,
                "label": node.get("label", ""),
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "stroke_color": colors["stroke"],
                "bg_color": colors["background"],
            })
            
            node_positions[node["id"]] = (x, y, width, height)
    
    # 4. 计算边
    positioned_edges = []
    for edge in edges:
        from_id = edge.get("from") or edge.get("from_id", "")
        to_id = edge.get("to") or edge.get("to_id", "")
        label = edge.get("label", "")
        
        if from_id in node_positions and to_id in node_positions:
            positioned_edges.append({
                "from_id": from_id,
                "to_id": to_id,
                "label": label,
            })
    
    logger.info(
        "布局计算完成: %d 节点, %d 连接, 方向=%s",
        len(positioned_nodes), len(positioned_edges), direction
    )
    
    return LayoutResult(nodes=positioned_nodes, edges=positioned_edges)


# 默认配置实例
default_layout_config = LayoutConfig()
