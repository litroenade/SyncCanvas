
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


def _decision_branch_point(node: GeomNode, branch: str) -> Tuple[float, float]:
    if branch == "yes":
        return (node.cx + node.w * 0.26, node.cy - node.h * 0.18)
    return (node.cx + node.w * 0.18, node.cy + node.h * 0.24)


def build_workflow(diagram: SemanticDiagram, nodes: Dict[str, GeomNode]):
    baseline_y = 286.0
    top_y = 164.0
    reject_y = 436.0

    start = nodes["start"]
    validate = nodes["validate"]
    stock = nodes["stock"]
    reserve = nodes["reserve"]
    charge = nodes["charge"]
    done = nodes["done"]
    notify = nodes["notify"]

    gap_start_validate = max(136.0, 86.0 + 0.28 * validate.w)
    gap_validate_stock = max(212.0, 118.0 + 0.34 * (validate.w + stock.w) / 2)
    gap_stock_reserve = max(198.0, 112.0 + 0.30 * (stock.w + reserve.w) / 2)
    gap_reserve_charge = max(126.0, 74.0 + 0.24 * (reserve.w + charge.w) / 2)
    gap_charge_done = max(126.0, 74.0 + 0.24 * (charge.w + done.w) / 2)

    _set_center(start, 138.0, baseline_y)
    _set_center(validate, start.cx + start.w / 2 + gap_start_validate + validate.w / 2, baseline_y)
    _set_center(stock, validate.cx + validate.w / 2 + gap_validate_stock + stock.w / 2, baseline_y)

    reserve_cx = stock.cx + stock.w / 2 + gap_stock_reserve + reserve.w / 2
    _set_center(reserve, reserve_cx, top_y)
    _set_center(charge, reserve.cx + reserve.w / 2 + gap_reserve_charge + charge.w / 2, top_y)
    _set_center(done, charge.cx + charge.w / 2 + gap_charge_done + done.w / 2, top_y)

    notify_cx = stock.cx + max(164.0, notify.w * 0.72)
    _set_center(notify, notify_cx, reject_y)

    routes: Dict[str, Route] = {}

    routes["e0"] = Route("e0", [boundary_point(start, (validate.cx, validate.cy)), boundary_point(validate, (start.cx, start.cy))])
    routes["e1"] = Route("e1", [boundary_point(validate, (stock.cx, stock.cy)), boundary_point(stock, (validate.cx, validate.cy))])
    routes["e4"] = Route("e4", [boundary_point(reserve, (charge.cx, charge.cy)), boundary_point(charge, (reserve.cx, reserve.cy))])
    routes["e5"] = Route("e5", [boundary_point(charge, (done.cx, done.cy)), boundary_point(done, (charge.cx, charge.cy))])

    start_yes = _decision_branch_point(stock, "yes")
    end_yes = boundary_point(reserve, (stock.cx, stock.cy))
    yes_lane_y = min(reserve.y, stock.y) - 38.0
    path_yes = [start_yes, (start_yes[0], yes_lane_y), (end_yes[0], yes_lane_y), end_yes]
    yes_label = _label("yes", (start_yes[0] + end_yes[0]) / 2 - 18.0, yes_lane_y - 34.0, "e2")
    routes["e2"] = Route("e2", path_yes, yes_label)

    start_no = _decision_branch_point(stock, "no")
    no_lane_y = min(notify.y - 52.0, stock.y + stock.h + 44.0)
    end_no = boundary_point(notify, (stock.cx, no_lane_y))
    path_no = [start_no, (start_no[0], no_lane_y), (end_no[0], no_lane_y), end_no]
    no_label = _label("no", end_no[0] + 18.0, no_lane_y + 18.0, "e3")
    routes["e3"] = Route("e3", path_no, no_label)

    retry_start = boundary_point(notify, (notify.cx, notify.y + notify.h + 96.0))
    retry_end = boundary_point(validate, (validate.cx, validate.y + validate.h + 96.0))
    retry_lane_y = max(notify.y + notify.h, validate.y + validate.h) + 96.0
    retry_lane_x = min(validate.x, notify.x) - 118.0
    path_retry = [
        retry_start,
        (retry_start[0], retry_lane_y),
        (retry_lane_x, retry_lane_y),
        (retry_lane_x, retry_end[1]),
        retry_end,
    ]
    retry_label = _label("retry", (retry_start[0] + retry_lane_x) / 2 - 18.0, retry_lane_y - 34.0, "e6")
    routes["e6"] = Route("e6", path_retry, retry_label)

    return nodes, routes, {}
