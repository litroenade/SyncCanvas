
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


def build_react_loop(diagram: SemanticDiagram, nodes: Dict[str, GeomNode]):
    q = nodes['query']
    reason = nodes['reason']
    tool = nodes['tool']
    obs = nodes['observe']
    memory = nodes['memory']
    final = nodes['answer']

    _set_center(q, 120.0, 220.0)
    _set_center(reason, 380.0, 120.0)
    _set_center(tool, 680.0, 140.0)
    _set_center(obs, 820.0, 320.0)
    _set_center(memory, 470.0, 420.0)
    _set_center(final, 1050.0, 220.0)

    routes: Dict[str, Route] = {}
    routes['e0'] = Route('e0', [boundary_point(q, (reason.cx, reason.cy)), boundary_point(reason, (q.cx, q.cy))])
    routes['e1'] = Route('e1', [boundary_point(reason, (tool.cx, tool.cy)), boundary_point(tool, (reason.cx, reason.cy))], _label('thought', 520.0, 108.0, 'e1'))
    routes['e2'] = Route('e2', [boundary_point(tool, (obs.cx, obs.cy)), boundary_point(obs, (tool.cx, tool.cy))], _label('tool action', 742.0, 196.0, 'e2'))
    routes['e3'] = Route('e3', [boundary_point(obs, (memory.cx, memory.cy)), boundary_point(memory, (obs.cx, obs.cy))], _label('observation', 620.0, 374.0, 'e3'))
    routes['e4'] = Route('e4', [boundary_point(memory, (reason.cx, reason.cy)), (430.0, 330.0), (330.0, 330.0), boundary_point(reason, (memory.cx, memory.cy))], _label('memory update', 300.0, 296.0, 'e4'))
    routes['e5'] = Route('e5', [boundary_point(reason, (final.cx, final.cy)), (880.0, reason.cy), (880.0, final.cy), boundary_point(final, (reason.cx, reason.cy))], _label('final answer', 900.0, 176.0, 'e5'))

    return nodes, routes, {}
