from typing import Dict

from .constraint_solver import solve_rails
from .router import route_edges
from .semantic_ir import GeomNode, Route, SemanticDiagram

RectTuple = tuple[float, float, float, float]

_TRANSFORMER_BASIC_GRID: dict[str, tuple[int, int]] = {
    "input": (0, 0),
    "embed": (0, 1),
    "attn": (-1, 2),
    "ffn": (1, 2),
    "cross": (0, 3),
    "decoder": (0, 4),
    "output": (0, 5),
}

_TRANSFORMER_DETAILED_GRID: dict[str, tuple[int, int]] = {
    "input": (0, 0),
    "position": (-1, 1),
    "embed": (0, 1),
    "encoder_stack": (0, 2),
    "encoder_layer": (0, 3),
    "encoder_attn": (-1, 3),
    "encoder_ffn": (1, 3),
    "encoder_output": (0, 4),
    "decoder_stack": (0, 5),
    "decoder_layer": (0, 6),
    "decoder_attn": (-1, 6),
    "cross": (0, 7),
    "decoder_ffn": (1, 7),
    "decoder_output": (0, 8),
    "output_projection": (0, 9),
}


def _has_meaningful_grid(nodes: Dict[str, GeomNode]) -> bool:
    return len({node.row for node in nodes.values()}) > 1 or len(
        {node.col for node in nodes.values()}
    ) > 1


def _looks_detailed_transformer(nodes: Dict[str, GeomNode]) -> bool:
    markers = (
        "encoder.",
        "decoder.",
        "projection",
        "positional",
        "attention.",
        "feed.forward",
    )
    return any(
        any(marker in node.id.casefold() for marker in markers)
        for node in nodes.values()
    )


def _canonical_role(node: GeomNode, *, detailed: bool) -> str | None:
    role = str(node.meta.get("role") or "").casefold()
    label = node.label.casefold()
    node_id = node.id.casefold()
    text = " ".join(part for part in (role, label, node_id) if part)

    if detailed:
        if "positional" in text or "position" in text:
            return "position"
        if "projection" in text or "softmax" in text or "logits" in text:
            return "output_projection"
        if "encoder.output" in node_id or "encoder output" in text:
            return "encoder_output"
        if "decoder.output" in node_id or "decoder output" in text:
            return "decoder_output"
        if "embedding" in text or "embed" in text:
            return "embed"
        if "encoder.stack" in node_id or "encoder stack" in text:
            return "encoder_stack"
        if "encoder.layer" in node_id or "encoder layer" in text:
            return "encoder_layer"
        if "decoder.stack" in node_id or "decoder stack" in text:
            return "decoder_stack"
        if "decoder.layer" in node_id or "decoder layer" in text:
            return "decoder_layer"
        if "cross attention" in text or "attention.cross" in node_id or node_id.endswith("cross"):
            return "cross"
        is_self_attention = (
            "self-attention" in text
            or "self attention" in text
            or "multi-head" in text
            or "attn" in text
            or "attention.self" in node_id
        )
        if is_self_attention and ("decoder" in text or "masked" in text):
            return "decoder_attn"
        if is_self_attention and "encoder" in text:
            return "encoder_attn"
        is_ffn = (
            "ffn" in text
            or "feed-forward" in text
            or "feed forward" in text
            or "feed.forward" in text
        )
        if is_ffn and "decoder" in text:
            return "decoder_ffn"
        if is_ffn and "encoder" in text:
            return "encoder_ffn"

    if "input" in text:
        return "input"
    if "embed" in text or "embedding" in text:
        return "embed"
    if "self-attention" in text or "self attention" in text or "multi-head" in text or "attn" in text:
        return "attn"
    if "ffn" in text or "feed-forward" in text or "feed forward" in text or "feed.forward" in text:
        return "ffn"
    if "cross" in text:
        return "cross"
    if "decoder" in text:
        return "decoder"
    if "output" in text:
        return "output"
    return None


def _spread_duplicate_slots(nodes: list[GeomNode]) -> None:
    grouped: dict[tuple[int, int], list[GeomNode]] = {}
    for node in nodes:
        grouped.setdefault((node.row, node.col), []).append(node)

    occupied: set[tuple[int, int]] = set()

    for (base_row, base_col), members in sorted(grouped.items()):
        ordered = sorted(members, key=lambda item: (item.label.casefold(), item.id.casefold()))
        anchor = ordered[0]
        anchor.row = base_row
        anchor.col = base_col
        occupied.add((base_row, base_col))
        for node in ordered[1:]:
            for offset in range(1, len(nodes) + 2):
                candidates = [
                    (base_row - offset, base_col),
                    (base_row + offset, base_col),
                    (base_row, base_col + offset),
                    (base_row, base_col - offset),
                ]
                placed = False
                for candidate_row, candidate_col in candidates:
                    if (candidate_row, candidate_col) in occupied:
                        continue
                    node.row = candidate_row
                    node.col = candidate_col
                    occupied.add((candidate_row, candidate_col))
                    placed = True
                    break
                if placed:
                    break


def _assign_transformer_hints(nodes: Dict[str, GeomNode]) -> None:
    detailed = _looks_detailed_transformer(nodes)
    grid = _TRANSFORMER_DETAILED_GRID if detailed else _TRANSFORMER_BASIC_GRID
    extras: list[GeomNode] = []
    should_reassign = not _has_meaningful_grid(nodes)

    for node in nodes.values():
        role = _canonical_role(node, detailed=detailed)
        if role is None or role not in grid:
            extras.append(node)
            continue
        if should_reassign:
            node.row, node.col = grid[role]

    if should_reassign:
        next_col = max(col for _row, col in grid.values()) + 1
        for node in sorted(extras, key=lambda item: item.label.casefold()):
            node.row = 0
            node.col = next_col
            next_col += 1
        _spread_duplicate_slots(list(nodes.values()))


def _rect_for(nodes: list[GeomNode], pad_x: float = 70.0, pad_y: float = 55.0) -> RectTuple:
    left = min(node.x for node in nodes) - pad_x
    top = min(node.y for node in nodes) - pad_y
    right = max(node.x + node.w for node in nodes) + pad_x
    bottom = max(node.y + node.h for node in nodes) + pad_y
    return (left, top, right, bottom)


def build_transformer_stack(diagram: SemanticDiagram, nodes: Dict[str, GeomNode]):
    _assign_transformer_hints(nodes)
    node_list = list(nodes.values())
    rail_meta = solve_rails(diagram, node_list)
    routes: Dict[str, Route] = route_edges(
        {node.id: node for node in node_list},
        diagram.edges,
        list(diagram.keepouts),
        rail_meta["y_centers"],
    )

    groups: dict[str, RectTuple] = {}
    encoder_nodes = [
        node for node in node_list if "encoder" in node.id.casefold()
    ]
    decoder_nodes = [
        node for node in node_list if "decoder" in node.id.casefold() or "cross" in node.id.casefold()
    ]
    if encoder_nodes:
        groups["Encoder Stack"] = _rect_for(encoder_nodes, pad_x=90.0, pad_y=55.0)
    if decoder_nodes:
        groups["Decoder Stack"] = _rect_for(decoder_nodes, pad_x=70.0, pad_y=55.0)
    return {node.id: node for node in node_list}, routes, groups
