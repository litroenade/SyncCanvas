"""Shared geometry primitives used by diagram layout and routing."""

import math
from dataclasses import dataclass
from typing import Any, Dict, Literal, Tuple


@dataclass
class Point:
    """Two-dimensional point."""

    x: float
    y: float

    def __add__(self, other: "Point") -> "Point":
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Point") -> "Point":
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Point":
        return Point(self.x * scalar, self.y * scalar)

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def distance_to(self, other: "Point") -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)


@dataclass
class Rect:
    """Axis-aligned rectangle."""

    x: float
    y: float
    width: float
    height: float

    @property
    def center(self) -> Point:
        return Point(self.x + self.width / 2, self.y + self.height / 2)

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    def edge_center(
        self,
        direction: Literal["top", "bottom", "left", "right"],
    ) -> Point:
        if direction == "top":
            return Point(self.x + self.width / 2, self.y)
        if direction == "bottom":
            return Point(self.x + self.width / 2, self.y + self.height)
        if direction == "left":
            return Point(self.x, self.y + self.height / 2)
        if direction == "right":
            return Point(self.x + self.width, self.y + self.height / 2)
        raise ValueError(f"Invalid direction: {direction}")

    @classmethod
    def from_element(cls, element: Dict[str, Any]) -> "Rect":
        return cls(
            x=element.get("x", 0),
            y=element.get("y", 0),
            width=element.get("width", 100),
            height=element.get("height", 100),
        )


def get_connection_direction(
    from_rect: Rect,
    to_rect: Rect,
) -> Tuple[
    Literal["top", "bottom", "left", "right"],
    Literal["top", "bottom", "left", "right"],
]:
    """Choose the dominant orthogonal connection direction between two boxes."""

    from_center = from_rect.center
    to_center = to_rect.center
    dx = to_center.x - from_center.x
    dy = to_center.y - from_center.y

    if abs(dy) >= abs(dx):
        return ("bottom", "top") if dy > 0 else ("top", "bottom")
    return ("right", "left") if dx > 0 else ("left", "right")


def calculate_arrow_points(
    from_rect: Rect,
    to_rect: Rect,
    gap: float = 8.0,
) -> Tuple[Point, list[list[float]]]:
    """Calculate an orthogonal arrow anchored to two rectangles."""

    from_dir, to_dir = get_connection_direction(from_rect, to_rect)
    start = from_rect.edge_center(from_dir)
    end = to_rect.edge_center(to_dir)

    if from_dir == "bottom":
        start = Point(start.x, start.y + gap)
    elif from_dir == "top":
        start = Point(start.x, start.y - gap)
    elif from_dir == "right":
        start = Point(start.x + gap, start.y)
    else:
        start = Point(start.x - gap, start.y)

    if to_dir == "bottom":
        end = Point(end.x, end.y + gap)
    elif to_dir == "top":
        end = Point(end.x, end.y - gap)
    elif to_dir == "right":
        end = Point(end.x + gap, end.y)
    else:
        end = Point(end.x - gap, end.y)

    relative_end = end - start
    return start, [[0, 0], [relative_end.x, relative_end.y]]

