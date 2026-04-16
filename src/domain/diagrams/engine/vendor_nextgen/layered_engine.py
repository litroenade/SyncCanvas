
from collections import defaultdict
from typing import Dict, Iterable, Tuple

from .geometry import boundary_point, segment_hits_rect
from .semantic_ir import GeomNode, LabelBox, Route, SemanticDiagram
from .text_fit import text_size

Point = Tuple[float, float]


def _set_center(node: GeomNode, cx: float, cy: float) -> None:
    node.x = cx - node.w / 2
    node.y = cy - node.h / 2


def _label(text: str, x: float, y: float, edge_id: str) -> LabelBox:
    tw, th = text_size(text)
    return LabelBox(text, x, y, tw + 14, th + 10, edge_id)


def _row_positions(nodes: Dict[str, GeomNode]):
    by_row = defaultdict(list)
    for node in nodes.values():
        by_row[node.row].append(node)
    row_keys = sorted(by_row.keys())
    for ridx, row in enumerate(row_keys):
        row_nodes = sorted(by_row[row], key=lambda n: n.col)
        y = 130.0 + ridx * 150.0
        total_w = sum(n.w for n in row_nodes) + max(0, len(row_nodes) - 1) * 130.0
        start_x = 660.0 - total_w / 2
        x = start_x
        for n in row_nodes:
            _set_center(n, x + n.w / 2, y)
            x += n.w + 130.0


def _group_bounds(nodes: Dict[str, GeomNode]):
    groups = {}
    for n in nodes.values():
        if not n.group:
            continue
        x1, y1, x2, y2 = n.bbox()
        if n.group not in groups:
            groups[n.group] = [x1, y1, x2, y2]
        else:
            g = groups[n.group]
            g[0] = min(g[0], x1)
            g[1] = min(g[1], y1)
            g[2] = max(g[2], x2)
            g[3] = max(g[3], y2)
    return {k: (v[0] - 34.0, v[1] - 38.0, v[2] + 34.0, v[3] + 38.0) for k, v in groups.items()}


def _hits_other_nodes(path: Iterable[Point], nodes: Dict[str, GeomNode], ignored: set[str]) -> bool:
    pts = list(path)
    for a, b in zip(pts, pts[1:]):
        for nid, node in nodes.items():
            if nid in ignored:
                continue
            if segment_hits_rect(a, b, node.bbox()):
                return True
    return False


def _route_and_label(edge_id: str, label: str, a: GeomNode, b: GeomNode, nodes: Dict[str, GeomNode]):
    min_x = min(n.x for n in nodes.values())
    max_x = max(n.x + n.w for n in nodes.values())
    s = boundary_point(a, (b.cx, b.cy))
    e = boundary_point(b, (a.cx, a.cy))
    if abs(a.row - b.row) == 0:
        path = [s, e]
        if _hits_other_nodes(path, nodes, {a.id, b.id}):
            lane_y = min(a.y, b.y) - 60.0
            path = [s, (s[0], lane_y), (e[0], lane_y), e]
        lab = _label(label, (path[0][0] + path[-1][0]) / 2 - 38.0, min(p[1] for p in path) - 40.0, edge_id) if label else None
        return Route(edge_id, path, lab)

    if abs(a.cx - b.cx) < 110.0:
        path = [s, e]
        if _hits_other_nodes(path, nodes, {a.id, b.id}):
            lane_x = min_x - 90.0 if a.col <= b.col else max_x + 90.0
            path = [s, (lane_x, s[1]), (lane_x, e[1]), e]
        label_x = max(p[0] for p in path) + 18.0
        lab = _label(label, label_x, (path[0][1] + path[-1][1]) / 2 - 16.0, edge_id) if label else None
        return Route(edge_id, path, lab)

    mid_y = (s[1] + e[1]) / 2
    path = [s, (s[0], mid_y), (e[0], mid_y), e]
    if _hits_other_nodes(path, nodes, {a.id, b.id}):
        lane_x = max_x + 90.0 if a.col > b.col else min_x - 90.0
        path = [s, (lane_x, s[1]), (lane_x, e[1]), e]
    lab = _label(label, (path[0][0] + path[-1][0]) / 2 - 38.0, min(path[0][1], path[-1][1]) - 38.0, edge_id) if label else None
    return Route(edge_id, path, lab)


def build_layered_architecture(diagram: SemanticDiagram, nodes: Dict[str, GeomNode]):
    _row_positions(nodes)
    routes: Dict[str, Route] = {}
    for e in diagram.edges:
        routes[e.id] = _route_and_label(e.id, e.label, nodes[e.src], nodes[e.dst], nodes)
    return nodes, routes, _group_bounds(nodes)
