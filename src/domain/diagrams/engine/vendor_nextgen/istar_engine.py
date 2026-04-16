
from typing import Dict

from .geometry import boundary_point
from .semantic_ir import GeomNode, LabelBox, Route, SemanticDiagram
from .text_fit import text_size


def _set_center(node: GeomNode, cx: float, cy: float) -> None:
    node.x = cx - node.w / 2
    node.y = cy - node.h / 2


def _label(text: str, x: float, y: float, edge_id: str) -> LabelBox:
    tw, th = text_size(text)
    return LabelBox(text, x, y, tw + 14, th + 10, edge_id)


def build_istar(diagram: SemanticDiagram, nodes: Dict[str, GeomNode]):
    edge_labels = {edge.id: edge.label for edge in diagram.edges}
    group_names = {group.id: group.label for group in diagram.groups}

    actor = nodes["actor"]
    goal1 = nodes["goal1"]
    task1 = nodes["task1"]
    res1 = nodes["res1"]
    soft1 = nodes["soft1"]
    goal2 = nodes["goal2"]

    _set_center(actor, 190.0, 300.0)
    _set_center(goal1, 560.0, 132.0)
    _set_center(task1, 560.0, 298.0)
    _set_center(res1, 560.0, 474.0)
    _set_center(soft1, 910.0, 150.0)
    _set_center(goal2, 910.0, 474.0)

    routes: Dict[str, Route] = {}

    s = boundary_point(goal1, (task1.cx, task1.cy))
    e = boundary_point(task1, (goal1.cx, goal1.cy))
    routes["e0"] = Route("e0", [s, (s[0], e[1]), e], _label(edge_labels["e0"], s[0] + 28.0, (s[1] + e[1]) / 2 - 14.0, "e0"))

    s = boundary_point(task1, (res1.cx, res1.cy))
    e = boundary_point(res1, (task1.cx, task1.cy))
    routes["e1"] = Route("e1", [s, (s[0], e[1]), e], _label(edge_labels["e1"], s[0] + 24.0, (s[1] + e[1]) / 2 - 14.0, "e1"))

    s = boundary_point(task1, (soft1.cx, soft1.cy))
    e = boundary_point(soft1, (task1.cx, task1.cy))
    elbow_x = task1.x + task1.w + 98.0
    routes["e2"] = Route("e2", [s, (elbow_x, s[1]), (elbow_x, e[1]), e], _label(edge_labels["e2"], elbow_x + 16.0, (s[1] + e[1]) / 2 - 14.0, "e2"))

    s = boundary_point(res1, (goal2.cx, goal2.cy))
    e = boundary_point(goal2, (res1.cx, res1.cy))
    routes["e3"] = Route("e3", [s, (e[0], s[1]), e], _label(edge_labels["e3"], (s[0] + e[0]) / 2 - 22.0, s[1] + 16.0, "e3"))

    group_rects = {
        group_names.get("actor_boundary", "Subscription Management Actor"): (task1.x - 68.0, goal1.y - 56.0, goal2.x + goal2.w + 66.0, goal2.y + goal2.h + 52.0),
    }
    return nodes, routes, group_rects
