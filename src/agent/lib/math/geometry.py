"""几何计算模块

提供点、向量、矩形等几何计算
"""

from typing import Tuple, Dict, Any, Literal
from dataclasses import dataclass
import math


@dataclass
class Point:
    """二维点"""

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
        """计算到另一点的距离"""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)


@dataclass
class Rect:
    """矩形区域"""

    x: float
    y: float
    width: float
    height: float

    @property
    def center(self) -> Point:
        """矩形中心点"""
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
        self, direction: Literal["top", "bottom", "left", "right"]
    ) -> Point:
        """获取边缘中点"""
        if direction == "top":
            return Point(self.x + self.width / 2, self.y)
        elif direction == "bottom":
            return Point(self.x + self.width / 2, self.y + self.height)
        elif direction == "left":
            return Point(self.x, self.y + self.height / 2)
        elif direction == "right":
            return Point(self.x + self.width, self.y + self.height / 2)
        else:
            raise ValueError(f"Invalid direction: {direction}")

    @classmethod
    def from_element(cls, element: Dict[str, Any]) -> "Rect":
        """从 Excalidraw 元素创建矩形"""
        return cls(
            x=element.get("x", 0),
            y=element.get("y", 0),
            width=element.get("width", 100),
            height=element.get("height", 100),
        )


def get_connection_direction(
    from_rect: Rect, to_rect: Rect
) -> Tuple[
    Literal["top", "bottom", "left", "right"], Literal["top", "bottom", "left", "right"]
]:
    """智能选择两个矩形之间的最佳连接方向

    基于中心点相对位置判断：
    - 如果垂直距离更大，使用 top/bottom 连接
    - 如果水平距离更大，使用 left/right 连接

    Returns:
        (from_direction, to_direction) 元组
    """
    from_center = from_rect.center
    to_center = to_rect.center

    dx = to_center.x - from_center.x
    dy = to_center.y - from_center.y

    # 判断主要方向
    if abs(dy) >= abs(dx):
        # 垂直方向为主
        if dy > 0:
            return ("bottom", "top")
        else:
            return ("top", "bottom")
    else:
        # 水平方向为主
        if dx > 0:
            return ("right", "left")
        else:
            return ("left", "right")


def calculate_arrow_points(
    from_rect: Rect,
    to_rect: Rect,
    gap: float = 8.0,
) -> Tuple[Point, list]:
    """计算箭头的起点和路径点

    Args:
        from_rect: 起始矩形
        to_rect: 目标矩形
        gap: 箭头与矩形边缘的间距

    Returns:
        (start_point, points_list) - 起点坐标和相对路径点列表
    """
    from_dir, to_dir = get_connection_direction(from_rect, to_rect)

    # 获取边缘中点
    start = from_rect.edge_center(from_dir)
    end = to_rect.edge_center(to_dir)

    # 应用间距偏移
    if from_dir == "bottom":
        start = Point(start.x, start.y + gap)
    elif from_dir == "top":
        start = Point(start.x, start.y - gap)
    elif from_dir == "right":
        start = Point(start.x + gap, start.y)
    elif from_dir == "left":
        start = Point(start.x - gap, start.y)

    if to_dir == "bottom":
        end = Point(end.x, end.y + gap)
    elif to_dir == "top":
        end = Point(end.x, end.y - gap)
    elif to_dir == "right":
        end = Point(end.x + gap, end.y)
    elif to_dir == "left":
        end = Point(end.x - gap, end.y)

    # 计算相对路径点
    relative_end = end - start
    points = [[0, 0], [relative_end.x, relative_end.y]]

    return start, points
