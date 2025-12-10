"""模块名称: auto_layout
主要功能: 流程图自动布局工具

使用 grandalf 库实现 DAG 层次布局，提供:
- auto_layout_flowchart: 自动排列现有流程图节点
- suggest_next_position: 推荐下一个节点位置
"""

from typing import Dict, Any, List, Tuple

from grandalf.graphs import Graph, Vertex, Edge
from grandalf.layouts import SugiyamaLayout

from src.agent.core.agent import AgentContext
from src.agent.core.tools import registry, ToolCategory
from src.agent.tools.helpers import require_room_id, get_room_and_doc
from src.logger import get_logger

logger = get_logger(__name__)


# 布局配置常量
HORIZONTAL_GAP: int = 200  # 水平间距
VERTICAL_GAP: int = 120    # 垂直间距
DEFAULT_NODE_WIDTH: int = 160
DEFAULT_NODE_HEIGHT: int = 70


class SizeView:
    """grandalf 节点尺寸视图"""

    def __init__(self, w: int, h: int):
        self.w: int = w
        self.h: int = h
        self.xy: Tuple[float, float] = (0, 0)


def _extract_graph_from_elements(
    elements: List[Dict[str, Any]]
) -> Tuple[Dict[str, Dict], List[Tuple[str, str]], Dict[str, Any]]:
    """从画布元素中提取图结构

    Args:
        elements: 画布元素列表

    Returns:
        (nodes_dict, edges_list, arrows_dict)
    """
    nodes: Dict[str, Dict] = {}
    edges: List[Tuple[str, str]] = []
    arrows: Dict[str, Any] = {}

    for el in elements:
        if el.get("isDeleted"):
            continue

        el_type = el.get("type", "")
        el_id = el.get("id", "")

        # 识别节点 (矩形、椭圆、菱形)
        if el_type in ("rectangle", "ellipse", "diamond"):
            nodes[el_id] = {
                "id": el_id,
                "x": el.get("x", 0),
                "y": el.get("y", 0),
                "width": el.get("width", DEFAULT_NODE_WIDTH),
                "height": el.get("height", DEFAULT_NODE_HEIGHT),
                "type": el_type,
            }

        # 识别连接 (箭头)
        elif el_type == "arrow":
            start_binding = el.get("startBinding")
            end_binding = el.get("endBinding")
            if start_binding and end_binding:
                from_id = start_binding.get("elementId")
                to_id = end_binding.get("elementId")
                if from_id and to_id:
                    edges.append((from_id, to_id))
                    arrows[el_id] = {"from": from_id, "to": to_id}

    return nodes, edges, arrows


def _compute_layout(
    nodes: Dict[str, Dict],
    edges: List[Tuple[str, str]],
    start_x: float = 100,
    start_y: float = 100,
) -> Dict[str, Tuple[float, float]]:
    """使用 Sugiyama 算法计算布局

    Args:
        nodes: 节点字典
        edges: 边列表
        start_x: 起始 X 坐标
        start_y: 起始 Y 坐标

    Returns:
        节点 ID -> (x, y) 坐标映射
    """
    if not nodes:
        return {}

    # 创建 grandalf 图结构
    vertices: Dict[str, Vertex] = {}
    for node_id, node in nodes.items():
        v = Vertex(node_id)
        v.view = SizeView(
            int(node.get("width", DEFAULT_NODE_WIDTH)) + HORIZONTAL_GAP,
            int(node.get("height", DEFAULT_NODE_HEIGHT)) + VERTICAL_GAP,
        )
        vertices[node_id] = v

    graph_edges: List[Edge] = []
    for from_id, to_id in edges:
        if from_id in vertices and to_id in vertices:
            graph_edges.append(Edge(vertices[from_id], vertices[to_id]))

    # 构建图
    g = Graph(list(vertices.values()), graph_edges)

    # 计算布局
    positions: Dict[str, Tuple[float, float]] = {}

    for component in g.C:
        sug = SugiyamaLayout(component)
        sug.init_all()
        sug.draw()

        for v in component.sV:
            if v.view and v.view.xy:
                node_data = nodes.get(v.data)
                if node_data:
                    # 转换为左上角坐标
                    cx, cy = v.view.xy
                    w = node_data.get("width", DEFAULT_NODE_WIDTH)
                    h = node_data.get("height", DEFAULT_NODE_HEIGHT)
                    positions[v.data] = (
                        start_x + cx - w / 2,
                        start_y + cy - h / 2,
                    )

    return positions


@registry.register(
    "auto_layout_flowchart",
    "自动排列画布上的流程图节点，使用层次布局算法优化节点位置",
    None,  # 无参数
    category=ToolCategory.CANVAS,
)
async def auto_layout_flowchart(
    start_x: float = 100,
    start_y: float = 100,
    context: AgentContext = None,
) -> Dict[str, Any]:
    """自动排列流程图节点

    Args:
        start_x: 布局起始 X 坐标
        start_y: 布局起始 Y 坐标
        context: Agent 上下文

    Returns:
        dict: 包含 status, moved_count, positions 的结果
    """
    room_id = require_room_id(context)
    _, doc, elements_array = await get_room_and_doc(room_id)

    # 提取元素数据
    elements = []
    for i in range(len(elements_array)):
        ymap = elements_array[i]
        el = dict(ymap)
        elements.append(el)

    # 提取图结构
    nodes, edges, _ = _extract_graph_from_elements(elements)

    if not nodes:
        return {
            "status": "warning",
            "message": "画布上没有可布局的节点",
            "moved_count": 0,
        }

    if not edges:
        return {
            "status": "warning",
            "message": "没有节点之间的连接，无法确定布局关系",
            "moved_count": 0,
            "node_count": len(nodes),
        }

    # 计算新布局
    positions = _compute_layout(nodes, edges, start_x, start_y)

    # 应用新位置
    moved_count = 0
    with doc.transaction(origin="ai-engine/auto_layout"):
        for i in range(len(elements_array)):
            ymap = elements_array[i]
            el_id = ymap.get("id")
            if el_id in positions:
                new_x, new_y = positions[el_id]
                ymap["x"] = new_x
                ymap["y"] = new_y
                moved_count += 1

    logger.info(
        f"自动布局完成: 移动 {moved_count} 个节点",
        extra={"room": room_id},
    )

    return {
        "status": "success",
        "message": f"已自动排列 {moved_count} 个节点",
        "moved_count": moved_count,
        "positions": {k: {"x": v[0], "y": v[1]} for k, v in positions.items()},
    }


@registry.register(
    "suggest_next_position",
    "根据画布现有内容，推荐下一个节点的最佳位置",
    None,
    category=ToolCategory.CANVAS,
)
async def suggest_next_position(
    context: AgentContext = None,
) -> Dict[str, Any]:
    """推荐下一个节点位置

    Args:
        context: Agent 上下文

    Returns:
        dict: 包含 status, suggested_x, suggested_y 的结果
    """
    room_id = require_room_id(context)
    _, _, elements_array = await get_room_and_doc(room_id)

    if len(elements_array) == 0:
        return {
            "status": "success",
            "message": "画布为空，建议从左上角开始",
            "suggested_x": 100,
            "suggested_y": 100,
            "is_empty": True,
        }

    # 找到最右下角的元素
    max_x: float = 0
    max_bottom: float = 0

    for i in range(len(elements_array)):
        ymap = elements_array[i]
        if ymap.get("isDeleted"):
            continue

        el_type = ymap.get("type", "")
        if el_type not in ("rectangle", "ellipse", "diamond", "text"):
            continue

        x = ymap.get("x", 0)
        y = ymap.get("y", 0)
        w = ymap.get("width", 100)
        h = ymap.get("height", 50)

        right = x + w
        bottom = y + h

        if right > max_x:
            max_x = right

        if bottom > max_bottom:
            max_bottom = bottom

    # 建议在最底部元素下方
    suggested_x = 100  # 左对齐
    suggested_y = max_bottom + VERTICAL_GAP

    return {
        "status": "success",
        "message": f"建议在 ({suggested_x}, {suggested_y}) 创建下一个节点",
        "suggested_x": suggested_x,
        "suggested_y": suggested_y,
        "is_empty": False,
    }
