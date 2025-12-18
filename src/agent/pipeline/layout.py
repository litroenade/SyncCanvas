"""模块名称: layout
主要功能: 符号化布局引擎
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from src.agent.pipeline.reasoning import LogicalOp, OpType
from src.agent.pipeline.cognition import CanvasState, CanvasBounds
from src.logger import get_logger

logger = get_logger(__name__)

@dataclass
class LayoutConfig:
    """布局配置"""

    # 节点尺寸
    rectangle_width: int = 160
    rectangle_height: int = 70
    diamond_size: int = 120
    ellipse_width: int = 120
    ellipse_height: int = 50

    # 间距
    vertical_gap: int = 80
    horizontal_gap: int = 200
    branch_offset: int = 180

    # 起始位置
    default_start_x: int = 400
    default_start_y: int = 50
    margin: int = 50  # 边距


@dataclass
class PositionedOp:
    """有坐标的操作

    Phase 4 输出 - 包含几何信息的操作。
    """

    type: OpType
    temp_id: str = ""
    real_id: str = ""  # 生成的真实 UUID
    params: Dict[str, Any] = field(default_factory=dict)

    # 几何信息 (由 LayoutEngine 计算)
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "temp_id": self.temp_id,
            "real_id": self.real_id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            **self.params,
        }

@dataclass
class GraphNode:
    """布局图节点"""

    id: str
    label: str
    node_type: str
    layer: int = 0
    position_in_layer: int = 0

    # 计算后的位置
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0


@dataclass
class GraphEdge:
    """布局图边"""

    from_id: str
    to_id: str
    label: str = ""

class LayoutEngine:
    """符号化布局引擎

    Phase 4 核心 - 几何求解器:
    1. 构建拓扑图
    2. 分层分配 (Layer Assignment)
    3. 计算坐标 (Position Calculation)
    4. 认知地图保持

    使用示例:
        engine = LayoutEngine()
        positioned_ops = await engine.solve(logical_ops, canvas_state)
    """

    def __init__(self, config: Optional[LayoutConfig] = None):
        self.config = config or LayoutConfig()

    async def solve(
        self, logical_ops: List[LogicalOp], canvas_state: CanvasState
    ) -> List[PositionedOp]:
        """求解布局

        将纯逻辑操作转换为有坐标的操作。

        Args:
            logical_ops: 逻辑操作列表
            canvas_state: 画布状态

        Returns:
            List[PositionedOp]: 有坐标的操作列表
        """
        if not logical_ops:
            return []

        # 1. 分离节点和边
        add_ops = [op for op in logical_ops if op.type == OpType.ADD_NODE]
        connect_ops = [op for op in logical_ops if op.type == OpType.CONNECT]
        other_ops = [
            op for op in logical_ops if op.type not in (OpType.ADD_NODE, OpType.CONNECT)
        ]

        # 2. 构建图结构
        nodes, edges = self._build_graph(add_ops, connect_ops)

        # 3. 分层分配
        self._assign_layers(nodes, edges)

        # 4. 计算位置
        self._calculate_positions(nodes, canvas_state.bounds)

        # 5. 生成有坐标的操作
        positioned_ops = self._generate_positioned_ops(nodes, edges, logical_ops)

        # 6. 处理其他操作 (delete, update 等)
        for op in other_ops:
            positioned_ops.append(
                PositionedOp(
                    type=op.type,
                    temp_id=op.temp_id,
                    params=op.params,
                )
            )

        logger.info(
            "[LayoutEngine] 布局完成: %d 节点, %d 连接",
            len(add_ops),
            len(connect_ops),
        )

        return positioned_ops

    def _build_graph(
        self, add_ops: List[LogicalOp], connect_ops: List[LogicalOp]
    ) -> Tuple[Dict[str, GraphNode], List[GraphEdge]]:
        """构建图结构"""
        nodes: Dict[str, GraphNode] = {}
        edges: List[GraphEdge] = []

        # 创建节点
        for op in add_ops:
            node_type = op.params.get("node_type", "rectangle")
            nodes[op.temp_id] = GraphNode(
                id=op.temp_id,
                label=op.params.get("label", ""),
                node_type=node_type,
            )

        # 创建边
        for op in connect_ops:
            from_id = op.params.get("from", "")
            to_id = op.params.get("to", "")
            if from_id and to_id:
                edges.append(
                    GraphEdge(
                        from_id=from_id,
                        to_id=to_id,
                        label=op.params.get("label", ""),
                    )
                )

        return nodes, edges

    def _assign_layers(
        self, nodes: Dict[str, GraphNode], edges: List[GraphEdge]
    ) -> None:
        """分层分配 (拓扑排序)

        使用 BFS 从源节点开始分配层级。
        """
        if not nodes:
            return

        # 构建邻接表和入度
        adjacency: Dict[str, List[str]] = {nid: [] for nid in nodes}
        in_degree: Dict[str, int] = {nid: 0 for nid in nodes}

        for edge in edges:
            if edge.from_id in adjacency and edge.to_id in nodes:
                adjacency[edge.from_id].append(edge.to_id)
                in_degree[edge.to_id] += 1

        # 找到源节点 (入度为 0)
        sources = [nid for nid, deg in in_degree.items() if deg == 0]

        # 如果没有源节点,选择第一个
        if not sources and nodes:
            sources = [list(nodes.keys())[0]]

        # BFS 分层
        layer = 0
        queue = list(sources)
        visited: Set[str] = set()

        while queue:
            next_queue = []
            position = 0

            for nid in queue:
                if nid in visited:
                    continue
                visited.add(nid)

                if nid in nodes:
                    nodes[nid].layer = layer
                    nodes[nid].position_in_layer = position
                    position += 1

                    # 添加后继节点
                    for succ in adjacency.get(nid, []):
                        if succ not in visited:
                            next_queue.append(succ)

            queue = next_queue
            layer += 1

        # 处理未访问的节点 (孤立节点)
        for nid, node in nodes.items():
            if nid not in visited:
                node.layer = layer
                layer += 1

    def _calculate_positions(
        self, nodes: Dict[str, GraphNode], bounds: CanvasBounds
    ) -> None:
        """计算节点位置"""
        if not nodes:
            return

        # 确定起始位置 (避开现有元素)
        start_x = max(bounds.suggested_x, self.config.default_start_x)
        start_y = max(
            bounds.suggested_y + self.config.margin, self.config.default_start_y
        )

        # 如果画布非空,从建议位置开始
        if bounds.max_x > 0:
            start_x = bounds.max_x + self.config.margin * 2

        # 按层分组
        layers: Dict[int, List[GraphNode]] = {}
        for node in nodes.values():
            if node.layer not in layers:
                layers[node.layer] = []
            layers[node.layer].append(node)

        # 计算每层的宽度
        current_y = start_y

        for layer_idx in sorted(layers.keys()):
            layer_nodes = layers[layer_idx]
            layer_width = 0
            max_height = 0

            # 计算节点尺寸
            for node in layer_nodes:
                w, h = self._get_node_size(node.node_type)
                node.width = w
                node.height = h
                layer_width += w
                max_height = max(max_height, h)

            # 添加间距
            layer_width += (len(layer_nodes) - 1) * self.config.horizontal_gap

            # 居中对齐
            current_x = start_x - layer_width / 2 + self.config.rectangle_width / 2

            for node in layer_nodes:
                node.x = current_x
                node.y = current_y
                current_x += node.width + self.config.horizontal_gap

            current_y += max_height + self.config.vertical_gap

    def _get_node_size(self, node_type: str) -> Tuple[float, float]:
        """获取节点尺寸"""
        if node_type == "ellipse":
            return self.config.ellipse_width, self.config.ellipse_height
        elif node_type == "diamond":
            return self.config.diamond_size, self.config.diamond_size
        else:  # rectangle
            return self.config.rectangle_width, self.config.rectangle_height

    def _generate_positioned_ops(
        self,
        nodes: Dict[str, GraphNode],
        edges: List[GraphEdge],
        original_ops: List[LogicalOp],
    ) -> List[PositionedOp]:
        """生成有坐标的操作"""

        positioned: List[PositionedOp] = []
        id_mapping: Dict[str, str] = {}  # temp_id -> real_id

        # 先生成所有节点的 ID 映射
        for temp_id in nodes:
            id_mapping[temp_id] = str(uuid.uuid4())

        # 生成节点操作
        for op in original_ops:
            if op.type == OpType.ADD_NODE and op.temp_id in nodes:
                node = nodes[op.temp_id]
                positioned.append(
                    PositionedOp(
                        type=OpType.ADD_NODE,
                        temp_id=op.temp_id,
                        real_id=id_mapping[op.temp_id],
                        x=node.x,
                        y=node.y,
                        width=node.width,
                        height=node.height,
                        params=op.params,
                    )
                )

        # 生成连接操作
        for op in original_ops:
            if op.type == OpType.CONNECT:
                from_temp = op.params.get("from", "")
                to_temp = op.params.get("to", "")

                # 映射到真实 ID (如果存在)
                from_real = id_mapping.get(from_temp, from_temp)
                to_real = id_mapping.get(to_temp, to_temp)

                positioned.append(
                    PositionedOp(
                        type=OpType.CONNECT,
                        temp_id=f"{from_temp}->{to_temp}",
                        real_id=str(uuid.uuid4()),
                        params={
                            "from": from_real,
                            "to": to_real,
                            "from_temp": from_temp,
                            "to_temp": to_temp,
                            **{
                                k: v
                                for k, v in op.params.items()
                                if k not in ("from", "to")
                            },
                        },
                    )
                )

        return positioned

def get_layout_engine(config: Optional[LayoutConfig] = None) -> LayoutEngine:
    """获取布局引擎"""
    return LayoutEngine(config)
