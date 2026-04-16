"""Shared math utilities."""

from src.lib.math.geometry import Point, Rect, calculate_arrow_points, get_connection_direction
from src.lib.math.linalg import AxisConstraint, solve_weighted_positions
from src.lib.math.pathfinding import (
    OrthogonalRouter,
    calculate_dynamic_params,
    find_orthogonal_path,
)
from src.lib.math.text import calculate_centered_position, estimate_text_size

__all__ = [
    "AxisConstraint",
    "OrthogonalRouter",
    "Point",
    "Rect",
    "calculate_centered_position",
    "calculate_arrow_points",
    "calculate_dynamic_params",
    "estimate_text_size",
    "find_orthogonal_path",
    "get_connection_direction",
    "solve_weighted_positions",
]
