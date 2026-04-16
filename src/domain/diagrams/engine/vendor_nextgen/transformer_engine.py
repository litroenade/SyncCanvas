
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


def build_transformer_stack(diagram: SemanticDiagram, nodes: Dict[str, GeomNode]):
    input_t = nodes['input']
    emb = nodes['embed']
    attn = nodes['attn']
    ffn = nodes['ffn']
    cross = nodes['cross']
    dec = nodes['decoder']
    out = nodes['output']

    _set_center(input_t, 120.0, 230.0)
    _set_center(emb, 330.0, 230.0)
    _set_center(attn, 560.0, 150.0)
    _set_center(ffn, 560.0, 300.0)
    _set_center(cross, 820.0, 230.0)
    _set_center(dec, 1050.0, 230.0)
    _set_center(out, 1290.0, 230.0)

    routes: Dict[str, Route] = {}
    routes['e0'] = Route('e0', [boundary_point(input_t, (emb.cx, emb.cy)), boundary_point(emb, (input_t.cx, input_t.cy))])
    routes['e1'] = Route('e1', [boundary_point(emb, (attn.cx, attn.cy)), boundary_point(attn, (emb.cx, emb.cy))], None)
    routes['e2'] = Route('e2', [boundary_point(attn, (ffn.cx, ffn.cy)), boundary_point(ffn, (attn.cx, attn.cy))], None)
    routes['e3'] = Route('e3', [boundary_point(ffn, (cross.cx, cross.cy)), (680.0, ffn.cy), (680.0, cross.cy), boundary_point(cross, (ffn.cx, ffn.cy))], None)
    routes['e4'] = Route('e4', [boundary_point(cross, (dec.cx, dec.cy)), boundary_point(dec, (cross.cx, cross.cy))], None)
    routes['e5'] = Route('e5', [boundary_point(dec, (out.cx, out.cy)), boundary_point(out, (dec.cx, dec.cy))])

    group_rects = {
        'Encoder Stack': (attn.x - 90.0, attn.y - 55.0, ffn.x + ffn.w + 90.0, ffn.y + ffn.h + 55.0),
        'Decoder Stack': (cross.x - 70.0, cross.y - 55.0, dec.x + dec.w + 70.0, dec.y + dec.h + 55.0),
    }
    return nodes, routes, group_rects
