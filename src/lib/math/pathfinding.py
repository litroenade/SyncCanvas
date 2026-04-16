"""Orthogonal pathfinding helpers for routed connectors."""

import heapq
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from src.infra.config import config
from src.lib.math.geometry import Point, Rect


def _get_pathfinding_params() -> tuple[float, float, int, float]:
    canvas = config.canvas
    return (
        canvas.pathfinding_grid_size,
        canvas.pathfinding_obstacle_padding,
        canvas.pathfinding_max_iterations,
        canvas.pathfinding_turn_penalty,
    )


@dataclass
class GridCell:
    """Grid coordinate used by the A* router."""

    x: int
    y: int

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def __lt__(self, other: "GridCell") -> bool:
        return (self.x, self.y) < (other.x, other.y)


@dataclass
class PathNode:
    """One A* frontier node."""

    cell: GridCell
    g_cost: float
    h_cost: float
    parent: Optional["PathNode"] = None

    @property
    def f_cost(self) -> float:
        return self.g_cost + self.h_cost

    def __lt__(self, other: "PathNode") -> bool:
        if self.f_cost == other.f_cost:
            return self.h_cost < other.h_cost
        return self.f_cost < other.f_cost


class OrthogonalRouter:
    """A* router constrained to orthogonal movement."""

    DIRECTIONS = [(0, -1), (0, 1), (-1, 0), (1, 0)]

    def __init__(self, grid_size: float = 0.0, padding: float = 0.0):
        params = _get_pathfinding_params()
        self.grid_size = grid_size if grid_size > 0 else params[0]
        self.padding = padding if padding > 0 else params[1]
        self._obstacles: Set[GridCell] = set()
        self._bounds: Tuple[int, int, int, int] = (0, 0, 100, 100)

    def set_obstacles(
        self,
        nodes: List[Dict[str, Any]],
        exclude_ids: Optional[Set[str]] = None,
    ) -> None:
        exclude_ids = exclude_ids or set()
        self._obstacles.clear()

        min_x, min_y = float("inf"), float("inf")
        max_x, max_y = float("-inf"), float("-inf")

        for node in nodes:
            node_type = node.get("type", "")
            if node_type in ("text", "arrow", "line"):
                continue

            node_id = node.get("id", "")
            if node_id in exclude_ids:
                continue

            rect = Rect.from_element(node)
            min_x = min(min_x, rect.left - 100)
            min_y = min(min_y, rect.top - 100)
            max_x = max(max_x, rect.right + 100)
            max_y = max(max_y, rect.bottom + 100)
            self._obstacles.update(self._rect_to_cells(rect, self.padding))

        self._bounds = (
            int(min_x / self.grid_size) - 5,
            int(min_y / self.grid_size) - 5,
            int(max_x / self.grid_size) + 5,
            int(max_y / self.grid_size) + 5,
        )

    def _rect_to_cells(self, rect: Rect, padding: float = 0) -> Set[GridCell]:
        cells: Set[GridCell] = set()
        left = int((rect.left - padding) / self.grid_size)
        right = int((rect.right + padding) / self.grid_size) + 1
        top = int((rect.top - padding) / self.grid_size)
        bottom = int((rect.bottom + padding) / self.grid_size) + 1
        for x in range(left, right):
            for y in range(top, bottom):
                cells.add(GridCell(x, y))
        return cells

    def _point_to_cell(self, point: Point) -> GridCell:
        return GridCell(int(point.x / self.grid_size), int(point.y / self.grid_size))

    def _cell_to_point(self, cell: GridCell) -> Point:
        return Point((cell.x + 0.5) * self.grid_size, (cell.y + 0.5) * self.grid_size)

    def _heuristic(self, a: GridCell, b: GridCell) -> float:
        return abs(a.x - b.x) + abs(a.y - b.y)

    def _is_valid(self, cell: GridCell) -> bool:
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
        max_iterations: int = 0,
    ) -> List[Point]:
        if max_iterations <= 0:
            max_iterations = _get_pathfinding_params()[2]

        start_cell = self._point_to_cell(start)
        end_cell = self._point_to_cell(end)
        if not self._is_valid(end_cell):
            return [start, end]

        open_set: List[PathNode] = []
        closed_set: Set[GridCell] = set()
        start_node = PathNode(
            cell=start_cell,
            g_cost=0,
            h_cost=self._heuristic(start_cell, end_cell),
        )
        heapq.heappush(open_set, start_node)
        cell_to_node: Dict[GridCell, PathNode] = {start_cell: start_node}

        iterations = 0
        while open_set and iterations < max_iterations:
            iterations += 1
            current = heapq.heappop(open_set)
            if current.cell == end_cell:
                return self._reconstruct_path(current, start, end)

            closed_set.add(current.cell)
            for dx, dy in self.DIRECTIONS:
                neighbor_cell = GridCell(current.cell.x + dx, current.cell.y + dy)
                if neighbor_cell in closed_set or not self._is_valid(neighbor_cell):
                    continue

                move_cost = 1.0
                if current.parent:
                    prev_dx = current.cell.x - current.parent.cell.x
                    prev_dy = current.cell.y - current.parent.cell.y
                    if (dx, dy) != (prev_dx, prev_dy):
                        move_cost += _get_pathfinding_params()[3]

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

        return [start, end]

    def _reconstruct_path(
        self,
        end_node: PathNode,
        start: Point,
        end: Point,
    ) -> List[Point]:
        cells: List[GridCell] = []
        current: Optional[PathNode] = end_node
        while current:
            cells.append(current.cell)
            current = current.parent
        cells.reverse()

        points = [start]
        for index in range(1, len(cells) - 1):
            prev_cell = cells[index - 1]
            cell = cells[index]
            next_cell = cells[index + 1]
            dx1, dy1 = cell.x - prev_cell.x, cell.y - prev_cell.y
            dx2, dy2 = next_cell.x - cell.x, next_cell.y - cell.y
            if (dx1, dy1) != (dx2, dy2):
                points.append(self._cell_to_point(cell))
        points.append(end)
        return points


def calculate_dynamic_params(
    nodes: List[Dict[str, Any]],
    exclude_ids: Optional[Set[str]] = None,
) -> Tuple[float, float]:
    """Compute routing params from the local obstacle set."""

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
        widths.append(float(node.get("width", 100)))
        heights.append(float(node.get("height", 70)))

    if not widths:
        grid_size, padding, _, _ = _get_pathfinding_params()
        return (grid_size, padding)

    min_dimension = min(min(widths), min(heights))
    grid_size = max(5.0, min(20.0, min_dimension / 10))
    avg_width = sum(widths) / len(widths)
    padding = max(25.0, min(60.0, avg_width / 3))
    return (grid_size, padding)


def find_orthogonal_path(
    start: Point,
    end: Point,
    obstacles: List[Dict[str, Any]],
    exclude_ids: Optional[Set[str]] = None,
    grid_size: Optional[float] = None,
    padding: Optional[float] = None,
) -> List[Point]:
    """Convenience wrapper around the orthogonal router."""

    if grid_size is None or padding is None:
        auto_grid, auto_padding = calculate_dynamic_params(obstacles, exclude_ids)
        grid_size = grid_size or auto_grid
        padding = padding or auto_padding

    router = OrthogonalRouter(grid_size=grid_size, padding=padding)
    router.set_obstacles(obstacles, exclude_ids)
    return router.find_path(start, end)

