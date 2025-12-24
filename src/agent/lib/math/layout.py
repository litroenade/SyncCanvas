"""布局计算模块

提供流程图等图形的自动布局算法
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class LayoutConfig:
    """布局配置"""

    # 节点间距
    horizontal_gap: float = 60.0  # 水平间距
    vertical_gap: float = 80.0  # 垂直间距

    # 默认节点尺寸
    default_node_width: float = 160.0
    default_node_height: float = 70.0

    # 特殊节点尺寸
    diamond_min_size: float = 100.0  # 菱形最小尺寸
    ellipse_min_width: float = 120.0  # 椭圆最小宽度

    # 起始位置
    start_x: float = 400.0
    start_y: float = 100.0


class FlowLayout:
    """流程图布局计算器

    支持从上到下 (TB) 或从左到右 (LR) 布局
    """

    def __init__(self, config: LayoutConfig = None, direction: str = "TB"):
        """
        Args:
            config: 布局配置
            direction: "TB" (top-to-bottom) 或 "LR" (left-to-right)
        """
        self.config = config or LayoutConfig()
        self.direction = direction
        self._nodes: List[Dict[str, Any]] = []
        self._current_x = self.config.start_x
        self._current_y = self.config.start_y

    def add_node(
        self,
        node_id: str,
        node_type: str = "rectangle",
        width: float = None,
        height: float = None,
    ) -> Dict[str, float]:
        """添加节点并计算其位置

        Args:
            node_id: 节点 ID
            node_type: 节点类型 (rectangle/diamond/ellipse)
            width: 自定义宽度
            height: 自定义高度

        Returns:
            {"x": x, "y": y, "width": width, "height": height}
        """
        # 确定尺寸
        if node_type == "diamond":
            w = max(
                width or self.config.default_node_width, self.config.diamond_min_size
            )
            h = max(
                height or self.config.default_node_height, self.config.diamond_min_size
            )
        elif node_type == "ellipse":
            w = max(
                width or self.config.default_node_width, self.config.ellipse_min_width
            )
            h = height or self.config.default_node_height
        else:
            w = width or self.config.default_node_width
            h = height or self.config.default_node_height

        # 计算位置
        x = self._current_x
        y = self._current_y

        # 记录节点
        node = {
            "id": node_id,
            "type": node_type,
            "x": x,
            "y": y,
            "width": w,
            "height": h,
        }
        self._nodes.append(node)

        # 更新下一个位置
        if self.direction == "TB":
            self._current_y += h + self.config.vertical_gap
        else:
            self._current_x += w + self.config.horizontal_gap

        return {"x": x, "y": y, "width": w, "height": h}

    def add_branch(
        self,
        parent_id: str,
        branches: List[Tuple[str, str]],  # [(node_id, node_type), ...]
    ) -> List[Dict[str, float]]:
        """添加分支节点（用于决策后的并行路径）

        Args:
            parent_id: 父节点 ID
            branches: 分支节点列表

        Returns:
            各分支节点的位置列表
        """
        parent = self._find_node(parent_id)
        if not parent:
            raise ValueError(f"Parent node not found: {parent_id}")

        results = []
        num_branches = len(branches)

        # 计算分支总宽度
        branch_width = self.config.default_node_width
        total_width = (
            num_branches * branch_width
            + (num_branches - 1) * self.config.horizontal_gap
        )

        # 起始 X（居中对齐父节点）
        start_x = parent["x"] + parent["width"] / 2 - total_width / 2
        branch_y = parent["y"] + parent["height"] + self.config.vertical_gap

        for i, (node_id, node_type) in enumerate(branches):
            x = start_x + i * (branch_width + self.config.horizontal_gap)
            h = self.config.default_node_height

            node = {
                "id": node_id,
                "type": node_type,
                "x": x,
                "y": branch_y,
                "width": branch_width,
                "height": h,
            }
            self._nodes.append(node)
            results.append({"x": x, "y": branch_y, "width": branch_width, "height": h})

        # 更新当前位置为分支下方
        self._current_y = (
            branch_y + self.config.default_node_height + self.config.vertical_gap
        )

        return results

    def _find_node(self, node_id: str) -> Dict[str, Any] | None:
        """查找已添加的节点"""
        for node in self._nodes:
            if node["id"] == node_id:
                return node
        return None

    def get_bounds(self) -> Dict[str, float]:
        """获取所有节点的边界"""
        if not self._nodes:
            return {"minX": 0, "minY": 0, "maxX": 0, "maxY": 0}

        min_x = min(n["x"] for n in self._nodes)
        min_y = min(n["y"] for n in self._nodes)
        max_x = max(n["x"] + n["width"] for n in self._nodes)
        max_y = max(n["y"] + n["height"] for n in self._nodes)

        return {"minX": min_x, "minY": min_y, "maxX": max_x, "maxY": max_y}
