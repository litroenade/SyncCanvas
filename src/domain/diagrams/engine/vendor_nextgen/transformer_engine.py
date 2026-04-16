from typing import Dict

from .constraint_solver import solve_rails
from .router import route_edges
from .semantic_ir import GeomNode, Route, SemanticDiagram

RectTuple = tuple[float, float, float, float]

_TRANSFORMER_GRID: dict[str, tuple[int, int]] = {
    "input": (0, 0),
    "embed": (0, 1),
    "attn": (-1, 2),
    "ffn": (1, 2),
    "cross": (0, 3),
    "decoder": (0, 4),
    "output": (0, 5),
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
    if "input" in text:
        return "input"
    if "embed" in text:
        return "embed"
    if "self-attention" in text or "self attention" in text or "multi-head" in text or "attn" in text:
        return "attn"
    if "ffn" in text or "feed-forward" in text or "feed forward" in text:
        return "ffn"
    if "cross" in text:
        return "cross"
    if "decoder" in text:
        return "decoder"
    if "output" in text:
        return "output"
    return None


def _assign_transformer_hints(nodes: Dict[str, GeomNode]) -> dict[str, list[GeomNode]]:
    buckets: dict[str, list[GeomNode]] = {role: [] for role in _TRANSFORMER_GRID}
    extras: list[GeomNode] = []
    should_reassign = not _has_meaningful_grid(nodes)
    for node in nodes.values():
        role = _canonical_role(node)
        if role is None:
            extras.append(node)
            continue
        if should_reassign:
            row, col = _TRANSFORMER_GRID[role]
            node.row = row
            node.col = col
        buckets[role].append(node)

    if should_reassign:
        next_col = max(col for _row, col in _TRANSFORMER_GRID.values()) + 1
        for node in sorted(extras, key=lambda item: item.label.casefold()):
            node.row = 0
            node.col = next_col
            next_col += 1
    return buckets


def _rect_for(nodes: list[GeomNode], pad_x: float = 70.0, pad_y: float = 55.0) -> RectTuple:
    left = min(node.x for node in nodes) - pad_x
    top = min(node.y for node in nodes) - pad_y
    right = max(node.x + node.w for node in nodes) + pad_x
    bottom = max(node.y + node.h for node in nodes) + pad_y
    return (left, top, right, bottom)


def build_transformer_stack(diagram: SemanticDiagram, nodes: Dict[str, GeomNode]):
    buckets = _assign_transformer_hints(nodes)
    node_list = list(nodes.values())
    rail_meta = solve_rails(diagram, node_list)
    routes: Dict[str, Route] = route_edges(
        {node.id: node for node in node_list},
        diagram.edges,
        list(diagram.keepouts),
        rail_meta["y_centers"],
    )

    groups: dict[str, RectTuple] = {}
    encoder_nodes = buckets["attn"] + buckets["ffn"]
    decoder_nodes = buckets["cross"] + buckets["decoder"]
    if encoder_nodes:
        groups["Encoder Stack"] = _rect_for(encoder_nodes, pad_x=90.0, pad_y=55.0)
    if decoder_nodes:
        groups["Decoder Stack"] = _rect_for(decoder_nodes, pad_x=70.0, pad_y=55.0)
    return {node.id: node for node in node_list}, routes, groups
