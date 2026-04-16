
import math
from typing import Tuple

from .semantic_ir import GeomNode

Point = Tuple[float, float]
Rect = Tuple[float, float, float, float]


def rect_intersects(a: Rect, b: Rect) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def inflate(r: Rect, pad: float) -> Rect:
    return (r[0] - pad, r[1] - pad, r[2] + pad, r[3] + pad)


def segment_hits_rect(a: Point, b: Point, r: Rect) -> bool:
    x1, y1 = a
    x2, y2 = b
    if abs(x1 - x2) < 1e-6:
        x = x1
        lo, hi = sorted([y1, y2])
        return (r[0] < x < r[2]) and not (hi <= r[1] or lo >= r[3])
    if abs(y1 - y2) < 1e-6:
        y = y1
        lo, hi = sorted([x1, x2])
        return (r[1] < y < r[3]) and not (hi <= r[0] or lo >= r[2])
    return False


def shape_for(node: GeomNode) -> str:
    if node.kind in {"terminator", "goal"}:
        return "ellipse"
    if node.kind == "decision":
        return "diamond"
    if node.kind == "softgoal":
        return "softgoal"
    if node.kind == "network":
        return "ellipse"
    return "rect"


def boundary_point(node: GeomNode, toward: Point) -> Point:
    dx = toward[0] - node.cx
    dy = toward[1] - node.cy
    shape = shape_for(node)
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return (node.cx, node.cy)
    if shape == "ellipse":
        rx = node.w / 2
        ry = node.h / 2
        scale = 1.0 / math.sqrt((dx * dx) / (rx * rx) + (dy * dy) / (ry * ry))
        return (node.cx + dx * scale, node.cy + dy * scale)
    if shape == "diamond":
        if abs(dx) / (node.w / 2) + abs(dy) / (node.h / 2) == 0:
            return (node.cx, node.cy)
        scale = 1.0 / (abs(dx) / (node.w / 2) + abs(dy) / (node.h / 2))
        return (node.cx + dx * scale, node.cy + dy * scale)
    if shape == "softgoal":
        rx = node.w / 2
        ry = node.h / 2
        scale = 1.0 / math.sqrt((dx * dx) / (rx * rx) + (dy * dy) / (ry * ry))
        return (node.cx + dx * scale, node.cy + dy * scale)
    # rectangle-ish shapes
    if abs(dx) * node.h > abs(dy) * node.w:
        sx = node.w / 2 * (1 if dx >= 0 else -1)
        sy = 0 if abs(dx) < 1e-9 else dy / abs(dx) * abs(sx)
    else:
        sy = node.h / 2 * (1 if dy >= 0 else -1)
        sx = 0 if abs(dy) < 1e-9 else dx / abs(dy) * abs(sy)
    return (node.cx + sx, node.cy + sy)


def port_candidates(node: GeomNode, target: GeomNode):
    dx = target.cx - node.cx
    dy = target.cy - node.cy
    if abs(dx) >= abs(dy):
        primary = "right" if dx >= 0 else "left"
        secondary = "bottom" if dy >= 0 else "top"
    else:
        primary = "bottom" if dy >= 0 else "top"
        secondary = "right" if dx >= 0 else "left"
    slots = {
        "left": [0.25, 0.5, 0.75],
        "right": [0.25, 0.5, 0.75],
        "top": [0.25, 0.5, 0.75],
        "bottom": [0.25, 0.5, 0.75],
    }

    def side_point(side: str, t: float):
        if side == "left":
            boundary = (node.x, node.y + node.h * t)
            outside = (node.x - 10, node.y + node.h * t)
        elif side == "right":
            boundary = (node.x + node.w, node.y + node.h * t)
            outside = (node.x + node.w + 10, node.y + node.h * t)
        elif side == "top":
            boundary = (node.x + node.w * t, node.y)
            outside = (node.x + node.w * t, node.y - 10)
        else:
            boundary = (node.x + node.w * t, node.y + node.h)
            outside = (node.x + node.w * t, node.y + node.h + 10)
        return boundary, outside

    candidates = []
    for side in [primary, secondary]:
        for t in slots[side]:
            candidates.append((side, *side_point(side, t)))
    return candidates


def shape_rect(node: GeomNode, pad: float = 0.0) -> Rect:
    return node.bbox(pad)
