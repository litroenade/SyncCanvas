from typing import Dict

from .constraint_solver import solve_rails
from .router import route_edges
from .semantic_ir import GeomNode, Route, SemanticDiagram

_RAG_GRID: dict[str, tuple[int, int]] = {
    "doc": (0, 0),
    "chunk": (0, 1),
    "embed": (0, 2),
    "vecdb": (0, 3),
    "recall": (1, 1),
    "rerank": (1, 2),
    "pack": (1, 3),
    "llm": (1, 4),
    "answer": (1, 5),
    "feedback": (2, 5),
}


def _has_meaningful_grid(nodes: Dict[str, GeomNode]) -> bool:
    return len({node.row for node in nodes.values()}) > 1 or len(
        {node.col for node in nodes.values()}
    ) > 1


def _canonical_role(node: GeomNode) -> str | None:
    role = str(node.meta.get("role") or "").casefold()
    label = node.label.casefold()
    node_id = node.id.casefold()
    text = " ".join(part for part in (role, label, node_id) if part)
    if "document" in text or "import" in text or node_id == "doc":
        return "doc"
    if "chunk" in text:
        return "chunk"
    if "embed" in text:
        return "embed"
    if "vector" in text or "store" in text or "index" in text or node_id == "vecdb":
        return "vecdb"
    if "recall" in text or "retrieve" in text:
        return "recall"
    if "rerank" in text or "re-rank" in text:
        return "rerank"
    if "pack" in text or "context" in text:
        return "pack"
    if "llm" in text or "inference" in text or "model" in text:
        return "llm"
    if "answer" in text or "response" in text or "output" in text:
        return "answer"
    if "feedback" in text:
        return "feedback"
    return None


def _assign_rag_hints(nodes: Dict[str, GeomNode]) -> None:
    if _has_meaningful_grid(nodes):
        return
    next_col = max(col for _row, col in _RAG_GRID.values()) + 1
    for node in sorted(nodes.values(), key=lambda item: item.label.casefold()):
        role = _canonical_role(node)
        if role is None:
            node.row = 1
            node.col = next_col
            next_col += 1
            continue
        node.row, node.col = _RAG_GRID[role]


def build_rag_pipeline(diagram: SemanticDiagram, nodes: Dict[str, GeomNode]):
    _assign_rag_hints(nodes)
    node_list = list(nodes.values())
    rail_meta = solve_rails(diagram, node_list)
    routes: Dict[str, Route] = route_edges(
        {node.id: node for node in node_list},
        diagram.edges,
        list(diagram.keepouts),
        rail_meta["y_centers"],
    )
    return {node.id: node for node in node_list}, routes, {}
