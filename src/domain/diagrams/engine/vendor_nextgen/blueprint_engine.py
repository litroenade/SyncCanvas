
from typing import Dict, Tuple

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


def build_blueprint(diagram: SemanticDiagram, nodes: Dict[str, GeomNode]):
    edge_labels = {edge.id: edge.label for edge in diagram.edges}
    group_names = {group.id: group.label for group in diagram.groups}

    plc = nodes["plc"]
    servo = nodes["servo"]
    io = nodes["io"]
    hmi = nodes["hmi"]
    motor = nodes["motor"]
    sensor = nodes["sensor"]
    tb = nodes["tb"]
    insp = nodes.get("insp")

    _set_center(hmi, 160.0, 260.0)
    _set_center(plc, 420.0, 260.0)
    _set_center(servo, 700.0, 128.0)
    _set_center(io, 700.0, 392.0)
    if insp:
        _set_center(insp, 980.0, 260.0)
    _set_center(motor, 1230.0, 128.0)
    _set_center(sensor, 1230.0, 392.0)
    _set_center(tb, 1180.0, 590.0)

    routes: Dict[str, Route] = {}

    s = _side(hmi, "right")
    e = _side(plc, "left")
    mid_x = (s[0] + e[0]) / 2
    routes["e0"] = Route("e0", [s, (mid_x, s[1]), (mid_x, e[1]), e], _label(edge_labels["e0"], mid_x - 18.0, s[1] + 14.0, "e0"))

    s = _side(plc, "top")
    e = _side(servo, "left")
    lane_y = servo.cy
    routes["e1"] = Route("e1", [s, (s[0], lane_y), e], _label(edge_labels["e1"], s[0] + 20.0, lane_y - 26.0, "e1"))

    s = _side(servo, "right")
    e = _side(motor, "left")
    routes["e2"] = Route("e2", [s, e], _label(edge_labels["e2"], (s[0] + e[0]) / 2 - 14.0, s[1] - 26.0, "e2"))

    s = _side(plc, "bottom")
    e = _side(io, "left")
    lane_y = io.cy
    routes["e3"] = Route("e3", [s, (s[0], lane_y), e], _label(edge_labels["e3"], s[0] + 22.0, lane_y - 42.0, "e3"))

    bottom_lane = 530.0
    s = _side(io, "bottom")
    e = _side(sensor, "bottom")
    routes["e4"] = Route("e4", [s, (s[0], bottom_lane), (e[0], bottom_lane), e], _label(edge_labels["e4"], (s[0] + e[0]) / 2 - 18.0, bottom_lane + 18.0, "e4"))

    if insp:
        s = _side(plc, "right")
        e = _side(insp, "left")
        elbow_x = e[0] - 46.0
        routes["e5"] = Route("e5", [s, (elbow_x, s[1]), (elbow_x, e[1]), e], _label(edge_labels["e5"], (s[0] + e[0]) / 2 - 16.0, s[1] - 28.0, "e5"))

        s = _side(insp, "right")
        e = _side(sensor, "top")
        top_lane = insp.y + 26.0
        routes["e6"] = Route("e6", [s, (e[0], s[1]), (e[0], e[1] - 18), e], _label(edge_labels["e6"], e[0] - 28.0, s[1] - 30.0, "e6"))

    group_rects = {
        group_names.get("cab", "Cabinet"): (plc.x - 84, servo.y - 44, (insp.x + insp.w + 84) if insp else (io.x + io.w + 84), io.y + io.h + 60),
    }
    return nodes, routes, group_rects
