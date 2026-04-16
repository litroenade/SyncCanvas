
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


def build_architecture_flow(diagram: SemanticDiagram, nodes: Dict[str, GeomNode]):
    edge_labels = {edge.id: edge.label for edge in diagram.edges}

    local = nodes['local']
    build = nodes['build']
    cache = nodes['cache']
    network = nodes['network']
    maven = nodes['maven']
    ivy = nodes['ivy']

    left_x = 210.0
    center_x = 600.0
    right_x = 960.0
    top_y = 140.0
    mid_y = 320.0
    bottom_y = 500.0

    _set_center(local, left_x, top_y)
    _set_center(build, left_x, mid_y)
    _set_center(cache, left_x, bottom_y)
    _set_center(network, center_x, mid_y)
    _set_center(maven, right_x, top_y)
    _set_center(ivy, right_x, bottom_y)

    routes: Dict[str, Route] = {}

    # build -> local repository
    s = boundary_point(build, (local.cx, local.cy))
    e = boundary_point(local, (build.cx, build.cy))
    lane_x = build.cx
    routes['e0'] = Route('e0', [s, (lane_x, e[1]), e], _label(edge_labels['e0'], lane_x - 128.0, (s[1] + e[1]) / 2 - 18.0, 'e0'))

    # cache -> build on right lane
    s = boundary_point(cache, (build.cx + 110.0, build.cy))
    e = boundary_point(build, (cache.cx + 110.0, cache.cy))
    right_lane_x = max(s[0], e[0]) + 44.0
    routes['e1'] = Route('e1', [s, (right_lane_x, s[1]), (right_lane_x, e[1]), e], _label(edge_labels['e1'], right_lane_x + 18.0, (s[1] + e[1]) / 2 - 18.0, 'e1'))

    # build -> cache on left lane
    s = boundary_point(build, (cache.cx - 110.0, cache.cy))
    e = boundary_point(cache, (build.cx - 110.0, build.cy))
    left_lane_x = min(s[0], e[0]) - 44.0
    routes['e2'] = Route('e2', [s, (left_lane_x, s[1]), (left_lane_x, e[1]), e], _label(edge_labels['e2'], left_lane_x - 136.0, (s[1] + e[1]) / 2 - 18.0, 'e2'))

    # build -> network main transfer line
    s = boundary_point(build, (network.cx, network.cy))
    e = boundary_point(network, (build.cx, build.cy))
    routes['e3'] = Route('e3', [s, e], _label(edge_labels['e3'], (s[0] + e[0]) / 2 - 84.0, s[1] - 30.0, 'e3'))

    # network -> repositories share a split trunk
    split_x = network.x + network.w + 120.0

    s_top = boundary_point(network, (maven.cx, maven.cy))
    e_top = boundary_point(maven, (network.cx, network.cy))
    routes['e4'] = Route('e4', [s_top, (split_x, s_top[1]), (split_x, e_top[1]), e_top], None)

    s_bot = boundary_point(network, (ivy.cx, ivy.cy))
    e_bot = boundary_point(ivy, (network.cx, network.cy))
    routes['e5'] = Route('e5', [s_bot, (split_x, s_bot[1]), (split_x, e_bot[1]), e_bot], None)

    return nodes, routes, {}
