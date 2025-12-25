"""路径规划模块

实现 A* 算法用于箭头避障路由
"""

from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass
import heapq

from .geometry import Rect, Point

# 从 canvas 模块导入常量
from ..canvas.constants import (
    PATHFINDING_GRID_SIZE,
    PATHFINDING_OBSTACLE_PADDING,
    PATHFINDING_MAX_ITERATIONS,
    PATHFINDING_TURN_PENALTY,
)


@dataclass
class GridCell:
    """网格单元格"""

    x: int
    y: int

    def __hash__(self):
        return hash((self.x, self.y))

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __lt__(self, other):
        return (self.x, self.y) < (other.x, other.y)


@dataclass
class PathNode:
    """A* 路径节点"""

    cell: GridCell
    g_cost: float  # 从起点到当前节点的实际代价
    h_cost: float  # 从当前节点到终点的启发式代价
    parent: Optional["PathNode"] = None

    @property
    def f_cost(self) -> float:
        """总代价"""
        return self.g_cost + self.h_cost

    def __lt__(self, other):
        if self.f_cost == other.f_cost:
            return self.h_cost < other.h_cost
        return self.f_cost < other.f_cost


class OrthogonalRouter:
    """正交路由器

    使用 A* 算法在网格上寻找避开障碍物的正交路径。
    箭头只能水平或垂直移动，不能斜向。
    """

    # 正交方向（上下左右）
    DIRECTIONS = [(0, -1), (0, 1), (-1, 0), (1, 0)]

    def __init__(
        self,
        grid_size: float = PATHFINDING_GRID_SIZE,
        padding: float = PATHFINDING_OBSTACLE_PADDING,
    ):
        """初始化路由器

        Args:
            grid_size: 网格单元大小（像素）
            padding: 节点边缘额外间距
        """
        self.grid_size = grid_size
        self.padding = padding
        self._obstacles: Set[GridCell] = set()
        self._bounds: Tuple[int, int, int, int] = (0, 0, 100, 100)

    def set_obstacles(
        self,
        nodes: List[Dict[str, Any]],
        exclude_ids: Optional[Set[str]] = None,
    ) -> None:
        """设置障碍物（其他节点）

        Args:
            nodes: 节点列表（Excalidraw 元素）
            exclude_ids: 排除的节点 ID（起点和终点节点）
        """
        exclude_ids = exclude_ids or set()
        self._obstacles.clear()

        min_x, min_y = float("inf"), float("inf")
        max_x, max_y = float("-inf"), float("-inf")

        for node in nodes:
            # 跳过非形状元素（如文本、箭头）
            node_type = node.get("type", "")
            if node_type in ("text", "arrow", "line"):
                continue

            node_id = node.get("id", "")
            if node_id in exclude_ids:
                continue

            rect = Rect.from_element(node)

            # 更新边界
            min_x = min(min_x, rect.left - 100)
            min_y = min(min_y, rect.top - 100)
            max_x = max(max_x, rect.right + 100)
            max_y = max(max_y, rect.bottom + 100)

            # 将节点区域（含 padding）标记为障碍
            cells = self._rect_to_cells(rect, self.padding)
            self._obstacles.update(cells)

        # 设置网格边界
        self._bounds = (
            int(min_x / self.grid_size) - 5,
            int(min_y / self.grid_size) - 5,
            int(max_x / self.grid_size) + 5,
            int(max_y / self.grid_size) + 5,
        )

    def _rect_to_cells(self, rect: Rect, padding: float = 0) -> Set[GridCell]:
        """将矩形区域转换为网格单元集合"""
        cells = set()

        left = int((rect.left - padding) / self.grid_size)
        right = int((rect.right + padding) / self.grid_size) + 1
        top = int((rect.top - padding) / self.grid_size)
        bottom = int((rect.bottom + padding) / self.grid_size) + 1

        for x in range(left, right):
            for y in range(top, bottom):
                cells.add(GridCell(x, y))

        return cells

    def _point_to_cell(self, point: Point) -> GridCell:
        """将坐标转换为网格单元"""
        return GridCell(
            int(point.x / self.grid_size),
            int(point.y / self.grid_size),
        )

    def _cell_to_point(self, cell: GridCell) -> Point:
        """将网格单元转换为坐标（单元中心）"""
        return Point(
            (cell.x + 0.5) * self.grid_size,
            (cell.y + 0.5) * self.grid_size,
        )

    def _heuristic(self, a: GridCell, b: GridCell) -> float:
        """曼哈顿距离启发式"""
        return abs(a.x - b.x) + abs(a.y - b.y)

    def _is_valid(self, cell: GridCell) -> bool:
        """检查单元格是否可通行"""
        if cell in self._obstacles:
            return False

        min_x, min_y, max_x, max_y = self._bounds
        if cell.x < min_x or cell.x > max_x:
            return False
        if cell.y < min_y or cell.y > max_y:
            return False

        return True

    def find_path(
        self,
        start: Point,
        end: Point,
        max_iterations: int = PATHFINDING_MAX_ITERATIONS,
    ) -> List[Point]:
        """A* 寻路

        Args:
            start: 起点坐标
            end: 终点坐标
            max_iterations: 最大迭代次数

        Returns:
            路径点列表，如果找不到路径则返回直线
        """
        start_cell = self._point_to_cell(start)
        end_cell = self._point_to_cell(end)

        # 如果起点或终点不可达，返回直线
        if not self._is_valid(end_cell):
            return [start, end]

        # A* 算法
        open_set: List[PathNode] = []
        closed_set: Set[GridCell] = set()

        start_node = PathNode(
            cell=start_cell,
            g_cost=0,
            h_cost=self._heuristic(start_cell, end_cell),
        )
        heapq.heappush(open_set, start_node)

        # 用于快速查找节点
        cell_to_node: Dict[GridCell, PathNode] = {start_cell: start_node}

        iterations = 0
        while open_set and iterations < max_iterations:
            iterations += 1

            current = heapq.heappop(open_set)

            # 到达终点
            if current.cell == end_cell:
                return self._reconstruct_path(current, start, end)

            closed_set.add(current.cell)

            # 探索邻居
            for dx, dy in self.DIRECTIONS:
                neighbor_cell = GridCell(
                    current.cell.x + dx,
                    current.cell.y + dy,
                )

                if neighbor_cell in closed_set:
                    continue

                if not self._is_valid(neighbor_cell):
                    continue

                # 计算代价（转弯有额外代价）
                move_cost = 1.0
                if current.parent:
                    prev_dx = current.cell.x - current.parent.cell.x
                    prev_dy = current.cell.y - current.parent.cell.y
                    if (dx, dy) != (prev_dx, prev_dy):
                        move_cost += PATHFINDING_TURN_PENALTY

                g_cost = current.g_cost + move_cost

                if neighbor_cell in cell_to_node:
                    neighbor_node = cell_to_node[neighbor_cell]
                    if g_cost < neighbor_node.g_cost:
                        neighbor_node.g_cost = g_cost
                        neighbor_node.parent = current
                        heapq.heapify(open_set)
                else:
                    neighbor_node = PathNode(
                        cell=neighbor_cell,
                        g_cost=g_cost,
                        h_cost=self._heuristic(neighbor_cell, end_cell),
                        parent=current,
                    )
                    cell_to_node[neighbor_cell] = neighbor_node
                    heapq.heappush(open_set, neighbor_node)

        # 找不到路径，返回直线
        return [start, end]

    def _reconstruct_path(
        self,
        end_node: PathNode,
        start: Point,
        end: Point,
    ) -> List[Point]:
        """重建路径并简化"""
        # 收集所有网格点
        cells: List[GridCell] = []
        current: Optional[PathNode] = end_node
        while current:
            cells.append(current.cell)
            current = current.parent
        cells.reverse()

        # 转换为坐标点
        points = [start]  # 使用精确起点

        # 简化路径：只保留转折点
        for i in range(1, len(cells) - 1):
            prev = cells[i - 1]
            curr = cells[i]
            next_cell = cells[i + 1]

            # 计算方向
            dx1, dy1 = curr.x - prev.x, curr.y - prev.y
            dx2, dy2 = next_cell.x - curr.x, next_cell.y - curr.y

            # 如果方向改变，这是一个转折点
            if (dx1, dy1) != (dx2, dy2):
                points.append(self._cell_to_point(curr))

        points.append(end)  # 使用精确终点

        return points


def calculate_dynamic_params(
    nodes: List[Dict[str, Any]],
    exclude_ids: Optional[Set[str]] = None,
) -> Tuple[float, float]:
    """根据节点大小动态计算路径规划参数

    Args:
        nodes: 节点列表
        exclude_ids: 排除的节点 ID

    Returns:
        (grid_size, padding) 元组
    """
    exclude_ids = exclude_ids or set()

    widths: List[float] = []
    heights: List[float] = []

    for node in nodes:
        node_type = node.get("type", "")
        if node_type in ("text", "arrow", "line"):
            continue

        node_id = node.get("id", "")
        if node_id in exclude_ids:
            continue

        w = float(node.get("width", 100))
        h = float(node.get("height", 70))
        widths.append(w)
        heights.append(h)

    if not widths:
        return (PATHFINDING_GRID_SIZE, PATHFINDING_OBSTACLE_PADDING)

    # 动态计算网格大小：使用最小节点尺寸的 1/10
    min_dimension = min(min(widths), min(heights))
    grid_size = max(5.0, min(20.0, min_dimension / 10))

    # 动态计算 padding：使用平均节点宽度的 1/5
    avg_width = sum(widths) / len(widths)
    padding = max(15.0, min(40.0, avg_width / 5))

    return (grid_size, padding)


def find_orthogonal_path(
    start: Point,
    end: Point,
    obstacles: List[Dict[str, Any]],
    exclude_ids: Optional[Set[str]] = None,
    grid_size: Optional[float] = None,
    padding: Optional[float] = None,
) -> List[Point]:
    """便捷函数：寻找避障正交路径

    Args:
        start: 起点
        end: 终点
        obstacles: 障碍物节点列表
        exclude_ids: 排除的节点 ID
        grid_size: 网格大小（None 表示自动计算）
        padding: 障碍物边缘间距（None 表示自动计算）

    Returns:
        路径点列表
    """
    # 如果未指定参数，动态计算
    if grid_size is None or padding is None:
        auto_grid, auto_padding = calculate_dynamic_params(obstacles, exclude_ids)
        grid_size = grid_size or auto_grid
        padding = padding or auto_padding

    router = OrthogonalRouter(grid_size=grid_size, padding=padding)
    router.set_obstacles(obstacles, exclude_ids)
    return router.find_path(start, end)
