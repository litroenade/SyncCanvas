
from heapq import heappop, heappush
from typing import Dict, List, Optional, Tuple

from src.lib.math.text import estimate_text_size

from .geometry import boundary_point, inflate, port_candidates, rect_intersects, segment_hits_rect
from .semantic_ir import GeomNode, LabelBox, Route, SemanticEdge

try:
    from PIL import Image, ImageDraw, ImageFont
except ModuleNotFoundError:  # pragma: no cover - depends on runtime environment
    Image = None
    ImageDraw = None
    ImageFont = None

Point = Tuple[float, float]
Rect = Tuple[float, float, float, float]


def build_coord_lines(nodes: Dict[str, GeomNode], keepouts: List[Rect], rail_y: List[float], extra: List[Point]) -> Tuple[List[float], List[float]]:
    xs, ys = set(), set()
    for node in nodes.values():
        for value in [node.x - 40, node.x - 16, node.x, node.x + node.w, node.x + node.w + 16, node.x + node.w + 40]:
            xs.add(round(float(value), 2))
        for value in [node.y - 40, node.y - 16, node.y, node.y + node.h, node.y + node.h + 16, node.y + node.h + 40]:
            ys.add(round(float(value), 2))
    for x1, y1, x2, y2 in keepouts:
        for value in [x1 - 28, x1 - 8, x1, x2, x2 + 8, x2 + 28]:
            xs.add(round(float(value), 2))
        for value in [y1 - 28, y1 - 8, y1, y2, y2 + 8, y2 + 28]:
            ys.add(round(float(value), 2))
    for value in rail_y:
        ys.add(round(float(value), 2))
    for x, y in extra:
        xs.add(round(float(x), 2))
        ys.add(round(float(y), 2))
    return sorted(xs)[:180] if len(xs) > 180 else sorted(xs), sorted(ys)[:180] if len(ys) > 180 else sorted(ys)


def build_graph(xs: List[float], ys: List[float], obstacles: List[Rect]):
    valid: Dict[Point, List[Point]] = {}
    rows = {y: [] for y in ys}
    cols = {x: [] for x in xs}
    for x in xs:
        for y in ys:
            point = (x, y)
            if any(r[0] < x < r[2] and r[1] < y < r[3] for r in obstacles):
                continue
            valid[point] = []
            rows[y].append(point)
            cols[x].append(point)
    for row in rows.values():
        row.sort()
        for a, b in zip(row, row[1:]):
            if not any(segment_hits_rect(a, b, r) for r in obstacles):
                valid[a].append(b)
                valid[b].append(a)
    for col in cols.values():
        col.sort(key=lambda p: p[1])
        for a, b in zip(col, col[1:]):
            if not any(segment_hits_rect(a, b, r) for r in obstacles):
                valid[a].append(b)
                valid[b].append(a)
    return valid


def compress(path: List[Point]) -> List[Point]:
    if len(path) <= 2:
        return path
    out = [path[0]]
    for idx in range(1, len(path) - 1):
        a, b, c = out[-1], path[idx], path[idx + 1]
        if (abs(a[0] - b[0]) < 1e-6 and abs(b[0] - c[0]) < 1e-6) or (abs(a[1] - b[1]) < 1e-6 and abs(b[1] - c[1]) < 1e-6):
            continue
        out.append(b)
    out.append(path[-1])
    return out


def astar(start: Point, goal: Point, adj, penalty_rows: Optional[List[float]] = None):
    penalty_rows = penalty_rows or []

    def heuristic(point: Point) -> float:
        return abs(point[0] - goal[0]) + abs(point[1] - goal[1])

    pq = []
    heappush(pq, (heuristic(start), 0.0, start, None))
    best = {(start, None): 0.0}
    prev = {}
    while pq:
        _, cost, cur, prev_dir = heappop(pq)
        if cur == goal:
            break
        for nxt in adj.get(cur, []):
            direction = "h" if abs(nxt[1] - cur[1]) < 1e-6 else "v"
            step = abs(nxt[0] - cur[0]) + abs(nxt[1] - cur[1])
            bend_penalty = 0.0 if prev_dir in (None, direction) else 38.0
            rail_penalty = 0.0
            if direction == "v":
                for rail in penalty_rows:
                    if abs(cur[1] - rail) < 1e-6:
                        rail_penalty += 10.0
            new_cost = cost + step + bend_penalty + rail_penalty
            state = (nxt, direction)
            if new_cost + 1e-6 < best.get(state, 1e18):
                best[state] = new_cost
                prev[state] = (cur, prev_dir)
                heappush(pq, (new_cost + heuristic(nxt), new_cost, nxt, direction))
    goal_states = [state for state in best if state[0] == goal]
    if not goal_states:
        return [start, goal]
    end = min(goal_states, key=lambda state: best[state])
    path = [goal]
    current = end
    while current in prev:
        current = prev[current]
        path.append(current[0])
    path.reverse()
    return compress(path)


def _text_box(text: str) -> Tuple[float, float]:
    if Image is None or ImageDraw is None or ImageFont is None:
        width, height = estimate_text_size(
            text,
            font_size=16,
            font_family=1,
            line_height=1.25,
        )
        return width + 20, height + 16
    font = ImageFont.load_default()
    img = Image.new("RGB", (1, 1), "white")
    draw = ImageDraw.Draw(img)
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=4)
    return bbox[2] - bbox[0] + 20, bbox[3] - bbox[1] + 16


def _workflow_route(edge: SemanticEdge, src: GeomNode, dst: GeomNode) -> List[Point]:
    start = boundary_point(src, (dst.cx, dst.cy))
    end = boundary_point(dst, (src.cx, src.cy))
    if edge.id == "e6":
        y = max(src.y + src.h, dst.y + dst.h) + 72
        return compress([start, (start[0], y), (dst.cx, y), end])
    if src.kind == "decision":
        if dst.cy < src.cy:
            midy = src.y - 56
            return compress([start, (start[0], midy), (dst.cx - 24, midy), end])
        if dst.cy > src.cy:
            midy = src.y + src.h + 56
            return compress([start, (start[0], midy), (dst.cx - 24, midy), end])
    if src.row == dst.row:
        return compress([start, end])
    midx = (src.cx + dst.cx) / 2
    return compress([start, (midx, start[1]), (midx, end[1]), end])


def _blueprint_route(edge: SemanticEdge, src: GeomNode, dst: GeomNode, nodes: Dict[str, GeomNode], keepouts: List[Rect]) -> List[Point]:
    start = boundary_point(src, (dst.cx, dst.cy))
    end = boundary_point(dst, (src.cx, src.cy))
    ko_left = min(ko[0] for ko in keepouts)
    ko_top = min(ko[1] for ko in keepouts)
    ko_right = max(ko[2] for ko in keepouts)
    ko_bottom = max(ko[3] for ko in keepouts)
    if edge.id == "e5":
        lane_y = min(src.cy, dst.cy) + 18.0
        return compress([start, (start[0] + 44.0, lane_y), (dst.x - 36.0, lane_y), end])
    if edge.id == "e4":
        lane_y = ko_bottom + 56.0
        return compress([start, (start[0], lane_y), (end[0], lane_y), end])
    if edge.id == "e6":
        lane_x = max(ko_right + 52.0, src.x + src.w + 38.0)
        return compress([start, (lane_x, start[1]), (lane_x, end[1]), end])
    if abs(src.cy - dst.cy) < 1e-6:
        return [start, end]
    return _generic_route(src, dst, nodes, keepouts, [src.cy, dst.cy])


def _segment_cost(path: List[Point]) -> Tuple[float, int]:
    bends = sum(
        1 for idx in range(1, len(path) - 1)
        if not (
            (abs(path[idx - 1][0] - path[idx][0]) < 1e-6 and abs(path[idx][0] - path[idx + 1][0]) < 1e-6)
            or (abs(path[idx - 1][1] - path[idx][1]) < 1e-6 and abs(path[idx][1] - path[idx + 1][1]) < 1e-6)
        )
    )
    length = sum(abs(path[idx][0] - path[idx + 1][0]) + abs(path[idx][1] - path[idx + 1][1]) for idx in range(len(path) - 1))
    return length, bends


def _generic_route(src: GeomNode, dst: GeomNode, nodes: Dict[str, GeomNode], keepouts: List[Rect], rail_y: List[float]):
    node_obstacles = {node_id: inflate(node.bbox(), 18.0) for node_id, node in nodes.items()}
    base_obstacles = [ob for node_id, ob in node_obstacles.items() if node_id not in {src.id, dst.id}] + [inflate(ko, 30.0) for ko in keepouts]
    best_path = None
    best_cost = 1e18
    for _, sb, sp in port_candidates(src, dst):
        for _, tb, tp in port_candidates(dst, src):
            xs, ys = build_coord_lines(nodes, keepouts, rail_y, [sp, tp])
            graph = build_graph(xs, ys, base_obstacles)
            if sp not in graph or tp not in graph:
                continue
            mid_path = astar(sp, tp, graph, penalty_rows=rail_y)
            full_path = [sb, sp] + mid_path[1:-1] + [tp, tb]
            full_path = compress(full_path)
            if len(full_path) >= 2:
                full_path[0] = boundary_point(src, full_path[1])
                full_path[-1] = boundary_point(dst, full_path[-2])
            length, bends = _segment_cost(full_path)
            cost = length + 28.0 * bends
            if cost < best_cost:
                best_cost = cost
                best_path = full_path
    if best_path is None:
        best_path = _orthogonal_fallback(src, dst, base_obstacles)
    return best_path


def _orthogonal_fallback(src: GeomNode, dst: GeomNode, obstacles: List[Rect]) -> List[Point]:
    start = boundary_point(src, (dst.cx, dst.cy))
    end = boundary_point(dst, (src.cx, src.cy))
    mid_x = (src.cx + dst.cx) / 2
    mid_y = (src.cy + dst.cy) / 2
    candidates = [
        [start, (end[0], start[1]), end],
        [start, (start[0], end[1]), end],
        [start, (mid_x, start[1]), (mid_x, end[1]), end],
        [start, (start[0], mid_y), (end[0], mid_y), end],
    ]
    best_path = [start, end]
    best_penalty = 1e18
    for candidate in candidates:
        path = compress(candidate)
        penalty = 0.0
        for a, b in zip(path, path[1:]):
            for obstacle in obstacles:
                if segment_hits_rect(a, b, obstacle):
                    penalty += 1200.0
        length, bends = _segment_cost(path)
        score = penalty + length + 40.0 * bends
        if score < best_penalty:
            best_penalty = score
            best_path = path
    return best_path


def _workflow_label_candidates(edge: SemanticEdge, path: List[Point], text_w: float, text_h: float, src: GeomNode, dst: GeomNode):
    candidates = []
    if src.kind == "decision" and len(path) >= 2:
        s0, s1 = path[0], path[1]
        mx, my = (s0[0] + s1[0]) / 2, (s0[1] + s1[1]) / 2
        above = dst.cy < src.cy
        if above:
            candidates += [(mx - text_w / 2, my - text_h - 32), (mx + 18, my - text_h - 24)]
        else:
            candidates += [(mx - text_w / 2, my + 24), (mx + 18, my + 24)]
    if edge.dashed or edge.label.lower() in {"retry", "fallback"}:
        if len(path) >= 3:
            bottom_y = max(p[1] for p in path)
            left_x = min(p[0] for p in path)
            right_x = max(p[0] for p in path)
            candidates += [
                ((left_x + right_x) / 2 - text_w / 2, bottom_y + 22),
                (left_x + 18, bottom_y + 22),
            ]
    return candidates


def _blueprint_label_candidates(edge: SemanticEdge, path: List[Point], text_w: float, text_h: float, keepouts: List[Rect]):
    candidates = []
    for a, b in zip(path, path[1:]):
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        crosses_keepout = any(segment_hits_rect(a, b, ko) for ko in keepouts)
        if abs(a[1] - b[1]) < 1e-6:
            if edge.label == "Quality":
                candidates += [(mx - text_w / 2, my + 28), (mx - text_w / 2, my - text_h - 28), (a[0] + 18, my + 28)]
            elif crosses_keepout:
                candidates += [
                    (a[0] + 10, my - text_h - 20),
                    (b[0] - text_w - 10, my - text_h - 20),
                    (a[0] + 10, my + 20),
                    (b[0] - text_w - 10, my + 20),
                ]
            else:
                candidates += [(mx - text_w / 2, my - text_h - 24), (mx - text_w / 2, my + 24)]
        elif abs(a[0] - b[0]) < 1e-6:
            top = min(a[1], b[1])
            bottom = max(a[1], b[1])
            if crosses_keepout:
                candidates += [(a[0] + 16, top - text_h - 14), (a[0] - text_w - 16, top - text_h - 14), (a[0] + 16, bottom + 14)]
            else:
                candidates += [(a[0] + 16, my - text_h / 2), (a[0] - text_w - 16, my - text_h / 2)]
    return candidates


def label_candidates(edge: SemanticEdge, path: List[Point], text_w: float, text_h: float, src: GeomNode, dst: GeomNode, keepouts: List[Rect]):
    candidates = []
    if src.family == "workflow":
        candidates += _workflow_label_candidates(edge, path, text_w, text_h, src, dst)
    elif src.family == "technical_blueprint":
        candidates += _blueprint_label_candidates(edge, path, text_w, text_h, keepouts)
    if len(path) >= 2:
        segments = list(zip(path, path[1:]))
        lengths = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in segments]
        idx = max(range(len(segments)), key=lambda i: lengths[i])
        a, b = segments[idx]
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        candidates += [(mx - text_w / 2, my - text_h - 20), (mx - text_w / 2, my + 20)]
        candidates += [(mx + 12, my - text_h - 16), (mx - text_w - 12, my - text_h - 16)]
    for point in path[1:-1]:
        candidates += [(point[0] + 18, point[1] - text_h - 16), (point[0] + 18, point[1] + 16)]
        candidates += [(point[0] - text_w - 18, point[1] - text_h - 16), (point[0] - text_w - 18, point[1] + 16)]
    return candidates[:40]


def _nudge_positions(x: float, y: float):
    offsets = [(0, 0), (0, -6), (0, 6), (-8, 0), (8, 0), (-8, -6), (8, -6), (-8, 6), (8, 6)]
    for dx, dy in offsets:
        yield x + dx, y + dy


def place_label(edge: SemanticEdge, path: List[Point], obstacles: List[Rect], source_rect: Rect, target_rect: Rect, placed: List[Rect], src: GeomNode, dst: GeomNode, keepouts: List[Rect]):
    if not edge.label:
        return None
    text_w, text_h = _text_box(edge.label)
    best = None
    best_penalty = 1e18
    all_obstacles = obstacles + [source_rect, target_rect]
    for cx, cy in label_candidates(edge, path, text_w, text_h, src, dst, keepouts):
        for x, y in _nudge_positions(cx, cy):
            rect = (x, y, x + text_w, y + text_h)
            penalty = 0.0
            for obstacle in all_obstacles:
                if rect_intersects(rect, obstacle):
                    penalty += 1200.0
            for obstacle in placed:
                if rect_intersects(rect, obstacle):
                    penalty += 800.0
            for keepout in keepouts:
                if rect_intersects(rect, inflate(keepout, 4.0)):
                    penalty += 1800.0
            for a, b in zip(path, path[1:]):
                if segment_hits_rect(a, b, inflate(rect, 3.0)):
                    penalty += 1100.0
            penalty += 0.004 * ((x - src.cx) ** 2 + (y - src.cy) ** 2)
            if penalty < best_penalty:
                best_penalty = penalty
                best = LabelBox(edge.label, x, y, text_w, text_h, edge.id)
    return best


def route_edges(nodes: Dict[str, GeomNode], edges: List[SemanticEdge], keepouts: List[Rect], rail_y: List[float]):
    node_obstacles = {node_id: inflate(node.bbox(), 18.0) for node_id, node in nodes.items()}
    routes: Dict[str, Route] = {}
    label_obstacles: List[Rect] = []
    ordered = sorted(edges, key=lambda edge: abs(nodes[edge.src].col - nodes[edge.dst].col) + abs(nodes[edge.src].row - nodes[edge.dst].row))
    for edge in ordered:
        src = nodes[edge.src]
        dst = nodes[edge.dst]
        if src.family == "workflow":
            path = _workflow_route(edge, src, dst)
        elif src.family == "technical_blueprint":
            path = _blueprint_route(edge, src, dst, nodes, keepouts)
        else:
            path = _generic_route(src, dst, nodes, keepouts, rail_y)
        base_obstacles = [ob for node_id, ob in node_obstacles.items() if node_id not in {src.id, dst.id}] + [inflate(ko, 30.0) for ko in keepouts] + label_obstacles
        label = place_label(edge, path, base_obstacles, node_obstacles[src.id], node_obstacles[dst.id], label_obstacles, src, dst, keepouts)
        if label is not None:
            label_obstacles.append(inflate(label.bbox(), 6.0))
        routes[edge.id] = Route(edge.id, path, label)
    return routes
