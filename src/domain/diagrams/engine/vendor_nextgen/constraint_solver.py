
from typing import Dict, List, Tuple

import numpy as np

from .semantic_ir import GeomNode, SemanticDiagram


def solve_axis(anchors: np.ndarray, desired_gaps: np.ndarray, anchor_weight: float = 4.0) -> np.ndarray:
    n = len(anchors)
    if n == 1:
        return anchors.copy()
    h = np.zeros((n, n), dtype=float)
    b = np.zeros(n, dtype=float)
    for idx in range(n):
        h[idx, idx] += anchor_weight
        b[idx] += anchor_weight * anchors[idx]
    for idx in range(n - 1):
        h[idx, idx] += 1.0
        h[idx + 1, idx + 1] += 1.0
        h[idx, idx + 1] -= 1.0
        h[idx + 1, idx] -= 1.0
        b[idx] += -desired_gaps[idx]
        b[idx + 1] += desired_gaps[idx]
    h[0, 0] += 10.0
    b[0] += 10.0 * anchors[0]
    return np.linalg.solve(h, b)


def solve_rails(diagram: SemanticDiagram, nodes: List[GeomNode], patch_locked: Dict[str, Tuple[float, float]] | None = None):
    rows = sorted(set(node.row for node in nodes))
    cols = sorted(set(node.col for node in nodes))
    row_to_idx = {row: idx for idx, row in enumerate(rows)}
    col_to_idx = {col: idx for idx, col in enumerate(cols)}

    col_widths = [0.0] * len(cols)
    row_heights = [0.0] * len(rows)
    for node in nodes:
        col_idx = col_to_idx[node.col]
        row_idx = row_to_idx[node.row]
        col_widths[col_idx] = max(col_widths[col_idx], node.w)
        row_heights[row_idx] = max(row_heights[row_idx], node.h)

    base_x = [120.0]
    for idx in range(1, len(cols)):
        gap = col_widths[idx - 1] / 2 + col_widths[idx] / 2 + 110.0
        base_x.append(base_x[-1] + gap)
    base_y = [110.0]
    for idx in range(1, len(rows)):
        gap = row_heights[idx - 1] / 2 + row_heights[idx] / 2 + 95.0
        base_y.append(base_y[-1] + gap)

    x_centers = solve_axis(np.array(base_x), np.array(np.diff(base_x)) if len(base_x) > 1 else np.array([]), anchor_weight=5.0)
    y_centers = solve_axis(np.array(base_y), np.array(np.diff(base_y)) if len(base_y) > 1 else np.array([]), anchor_weight=5.0)

    if patch_locked:
        for node in nodes:
            if node.id in patch_locked:
                ox, oy = patch_locked[node.id]
                node.x = ox
                node.y = oy
                continue
            col_idx = col_to_idx[node.col]
            row_idx = row_to_idx[node.row]
            node.x = float(x_centers[col_idx] - node.w / 2)
            node.y = float(y_centers[row_idx] - node.h / 2)
    else:
        for node in nodes:
            col_idx = col_to_idx[node.col]
            row_idx = row_to_idx[node.row]
            node.x = float(x_centers[col_idx] - node.w / 2)
            node.y = float(y_centers[row_idx] - node.h / 2)

    if diagram.family == "technical_blueprint" and diagram.keepouts:
        _resolve_keepout_overlaps(nodes, diagram.keepouts)

    return {"x_centers": [float(v) for v in x_centers], "y_centers": [float(v) for v in y_centers]}


def group_bounds(nodes: List[GeomNode], pad_x: float = 28.0, pad_y: float = 32.0):
    groups: Dict[str, Tuple[float, float, float, float]] = {}
    for node in nodes:
        if not node.group:
            continue
        x1, y1, x2, y2 = node.bbox()
        if node.group not in groups:
            groups[node.group] = (x1, y1, x2, y2)
        else:
            gx1, gy1, gx2, gy2 = groups[node.group]
            groups[node.group] = (min(gx1, x1), min(gy1, y1), max(gx2, x2), max(gy2, y2))
    out: Dict[str, Tuple[float, float, float, float]] = {}
    for group_id, (x1, y1, x2, y2) in groups.items():
        out[group_id] = (x1 - pad_x, y1 - pad_y, x2 + pad_x, y2 + pad_y)
    return out


def _resolve_keepout_overlaps(nodes: List[GeomNode], keepouts, margin: float = 36.0):
    for node in nodes:
        for x1, y1, x2, y2 in keepouts:
            nx1, ny1, nx2, ny2 = node.bbox()
            if nx2 <= x1 or nx1 >= x2 or ny2 <= y1 or ny1 >= y2:
                continue
            if node.kind == "title_block":
                node.y = float(y2 + margin)
                continue
            candidates = [
                (x1 - node.w - margin, node.y),
                (x2 + margin, node.y),
                (node.x, y1 - node.h - margin),
                (node.x, y2 + margin),
            ]
            def score(pos):
                dx = abs(pos[0] - node.x)
                dy = abs(pos[1] - node.y)
                return dx + 2.8 * dy
            best = min(candidates, key=score)
            node.x, node.y = float(best[0]), float(best[1])

