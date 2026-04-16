
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


def build_rag_pipeline(diagram: SemanticDiagram, nodes: Dict[str, GeomNode]):
    doc = nodes['doc']
    chunk = nodes['chunk']
    emb = nodes['embed']
    vec = nodes['vecdb']
    recall = nodes['recall']
    rerank = nodes['rerank']
    pack = nodes['pack']
    llm = nodes['llm']
    out = nodes['answer']
    feedback = nodes['feedback']

    _set_center(doc, 110.0, 130.0)
    _set_center(chunk, 320.0, 130.0)
    _set_center(emb, 540.0, 130.0)
    _set_center(vec, 790.0, 130.0)
    _set_center(recall, 320.0, 320.0)
    _set_center(rerank, 520.0, 320.0)
    _set_center(pack, 730.0, 320.0)
    _set_center(llm, 960.0, 320.0)
    _set_center(out, 1170.0, 320.0)
    _set_center(feedback, 1170.0, 480.0)

    routes: Dict[str, Route] = {}
    def link(eid, a, b, label=''):
        la = boundary_point(a, (b.cx, b.cy))
        lb = boundary_point(b, (a.cx, a.cy))
        lab = None if not label else _label(label, (la[0]+lb[0])/2 - 40.0, min(la[1], lb[1]) - 28.0, eid)
        routes[eid] = Route(eid, [la, lb], lab)
    link('e0', doc, chunk, '')
    link('e1', chunk, emb, '')
    link('e2', emb, vec, '')
    link('e3', vec, recall, '')
    link('e4', recall, rerank, '')
    link('e5', rerank, pack, '')
    link('e6', pack, llm, '')
    link('e7', llm, out, '')
    routes['e8'] = Route('e8', [boundary_point(out, (feedback.cx, feedback.cy)), boundary_point(feedback, (out.cx, out.cy))], None)
    routes['e9'] = Route('e9', [boundary_point(feedback, (1310.0, feedback.cy)), (1310.0, feedback.cy), (1310.0, rerank.cy), boundary_point(rerank, (1310.0, rerank.cy))], None)
    group_rects = {
        'Offline Ingestion': (doc.x - 60.0, doc.y - 46.0, vec.x + vec.w + 60.0, vec.y + vec.h + 46.0),
        'Online Inference': (recall.x - 60.0, recall.y - 46.0, out.x + out.w + 60.0, out.y + out.h + 46.0),
    }
    return nodes, routes, group_rects
