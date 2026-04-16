from typing import Dict

from .constraint_solver import solve_rails
from .router import route_edges
from .semantic_ir import GeomNode, Route, SemanticDiagram

_REACT_GRID: dict[str, tuple[int, int]] = {
    "query": (0, 0),
    "reason": (-1, 1),
    "tool": (-1, 2),
    "observe": (1, 2),
    "memory": (1, 1),
    "answer": (0, 3),
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
    if "query" in text or "user request" in text:
        return "query"
    if "reason" in text or "think" in text or "planner" in text:
        return "reason"
    if "tool" in text or "act" in text or "action" in text:
        return "tool"
    if "observe" in text or "observation" in text or "environment" in text:
        return "observe"
    if "memory" in text or "context" in text:
        return "memory"
    if "answer" in text or "response" in text or "final" in text:
        return "answer"
    return None


def build_react_loop(diagram: SemanticDiagram, nodes: Dict[str, GeomNode]):
    if not _has_meaningful_grid(nodes):
        next_col = max(col for _row, col in _REACT_GRID.values()) + 1
        for node in sorted(nodes.values(), key=lambda item: item.label.casefold()):
            role = _canonical_role(node)
            if role is None:
                node.row = 0
                node.col = next_col
                next_col += 1
                continue
            node.row, node.col = _REACT_GRID[role]

    node_list = list(nodes.values())
    rail_meta = solve_rails(diagram, node_list)
    routes: Dict[str, Route] = route_edges(
        {node.id: node for node in node_list},
        diagram.edges,
        list(diagram.keepouts),
        rail_meta["y_centers"],
    )
    return {node.id: node for node in node_list}, routes, {}
