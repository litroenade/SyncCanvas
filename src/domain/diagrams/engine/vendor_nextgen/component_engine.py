
from typing import Dict, Tuple

from .geometry import boundary_point
from .semantic_ir import GeomNode, LabelBox, Route, SemanticDiagram
from .text_fit import text_size


def _set_center(node: GeomNode, cx: float, cy: float) -> None:
    node.x = cx - node.w / 2
    node.y = cy - node.h / 2


def _label(text: str, x: float, y: float, edge_id: str) -> LabelBox:
    tw, th = text_size(text)
    return LabelBox(text, x, y, tw + 14, th + 10, edge_id)


def _side(node: GeomNode, which: str) -> Tuple[float, float]:
    if which == "left":
        return (node.x, node.cy)
    if which == "right":
        return (node.x + node.w, node.cy)
    if which == "top":
        return (node.cx, node.y)
    return (node.cx, node.y + node.h)


def build_component_cluster(diagram: SemanticDiagram, nodes: Dict[str, GeomNode]):
    edge_labels = {edge.id: edge.label for edge in diagram.edges}
    group_names = {group.id: group.label for group in diagram.groups}

    web = nodes["web"]
    api = nodes["api"]
    auth = nodes["auth"]
    order = nodes["order"]
    pay = nodes["pay"]
    db = nodes["db"]

    top_y = 142.0
    bottom_y = 338.0
    left_x = 132.0
    plat_x = 382.0
    domain_x = 640.0
    db_x = 970.0

    _set_center(web, left_x, 238.0)
    _set_center(api, plat_x, top_y)
    _set_center(auth, plat_x, bottom_y)
    _set_center(order, domain_x, top_y)
    _set_center(pay, domain_x, bottom_y)
    _set_center(db, db_x, 240.0)

    routes: Dict[str, Route] = {}

    start = _side(web, "right")
    end = _side(api, "left")
    elbow_x = web.x + web.w + 42.0
    r = [start, (elbow_x, start[1]), (elbow_x, end[1]), end]
    routes["e0"] = Route("e0", r, _label(edge_labels["e0"], elbow_x - 18.0, start[1] + 18.0, "e0"))

    start = _side(api, "bottom")
    end = _side(auth, "top")
    mid_y = (start[1] + end[1]) / 2
    r = [start, (start[0], mid_y), end]
    routes["e1"] = Route("e1", r, _label(edge_labels["e1"], start[0] + 22.0, mid_y - 18.0, "e1"))

    start = _side(api, "right")
    end = _side(order, "left")
    mid_x = (start[0] + end[0]) / 2
    r = [start, (mid_x, start[1]), (mid_x, end[1]), end]
    routes["e2"] = Route("e2", r, _label(edge_labels["e2"], mid_x - 16.0, start[1] - 28.0, "e2"))

    start = _side(order, "bottom")
    end = _side(pay, "top")
    mid_y = (start[1] + end[1]) / 2
    r = [start, (start[0], mid_y), end]
    routes["e3"] = Route("e3", r, _label(edge_labels["e3"], start[0] + 22.0, mid_y - 18.0, "e3"))

    def to_db(edge_id: str, src: GeomNode, entry_y: float, label_dx: float, label_dy: float):
        start = _side(src, "right")
        end = boundary_point(db, (db.x, entry_y))
        trunk_x = db.x - 106.0
        r = [start, (trunk_x, start[1]), (trunk_x, entry_y), end]
        lx = trunk_x + label_dx
        ly = min(start[1], entry_y) + label_dy
        return Route(edge_id, r, _label(edge_labels[edge_id], lx, ly, edge_id))

    routes["e4"] = to_db("e4", auth, db.cy - 44.0, 18.0, 14.0)
    routes["e5"] = to_db("e5", order, db.cy - 6.0, 18.0, -24.0)
    routes["e6"] = to_db("e6", pay, db.cy + 46.0, 18.0, -24.0)

    group_rects = {
        group_names.get("ui", "UI"): (web.x - 54, web.y - 42, web.x + web.w + 54, web.y + web.h + 42),
        group_names.get("control", "Control"): (api.x - 58, api.y - 42, api.x + api.w + 58, auth.y + auth.h + 42),
        group_names.get("domain", "Domain"): (order.x - 58, order.y - 42, order.x + order.w + 58, pay.y + pay.h + 42),
        group_names.get("infra", "Infra"): (db.x - 70, db.y - 46, db.x + db.w + 70, db.y + db.h + 46),
    }
    return nodes, routes, group_rects
