from collections import defaultdict, deque
from typing import Dict

from .constraint_solver import solve_rails
from .router import route_edges
from .semantic_ir import GeomNode, Route, SemanticDiagram


def _has_meaningful_grid(nodes: Dict[str, GeomNode]) -> bool:
    return len({node.row for node in nodes.values()}) > 1 or len(
        {node.col for node in nodes.values()}
    ) > 1


def _node_sort_key(node: GeomNode) -> tuple[int, int, str]:
    return (int(node.col), int(node.row), node.label.casefold())


def _infer_layered_hints(diagram: SemanticDiagram, nodes: Dict[str, GeomNode]) -> None:
    if _has_meaningful_grid(nodes):
        return

    incoming: dict[str, int] = {node_id: 0 for node_id in nodes}
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in nodes}
    for edge in diagram.edges:
        if edge.src not in nodes or edge.dst not in nodes or edge.src == edge.dst:
            continue
        outgoing[edge.src].append(edge.dst)
        incoming[edge.dst] += 1

    queue = deque(
        sorted(
            (nodes[node_id] for node_id, degree in incoming.items() if degree == 0),
            key=_node_sort_key,
        )
    )
    layer_by_id: dict[str, int] = {node_id: 0 for node_id in nodes}
    visited: set[str] = set()

    while queue:
        node = queue.popleft()
        visited.add(node.id)
        base_layer = layer_by_id[node.id]
        for child_id in sorted(outgoing[node.id], key=lambda node_id: _node_sort_key(nodes[node_id])):
            layer_by_id[child_id] = max(layer_by_id.get(child_id, 0), base_layer + 1)
            incoming[child_id] -= 1
            if incoming[child_id] == 0:
                queue.append(nodes[child_id])

    if len(visited) != len(nodes):
        for fallback_row, node in enumerate(sorted(nodes.values(), key=_node_sort_key)):
            layer_by_id.setdefault(node.id, fallback_row)

    buckets: dict[int, list[GeomNode]] = defaultdict(list)
    for node in nodes.values():
        buckets[layer_by_id.get(node.id, 0)].append(node)

    for row, members in sorted(buckets.items()):
        for col, node in enumerate(sorted(members, key=_node_sort_key)):
            node.row = row
            node.col = col


def build_layered_architecture(diagram: SemanticDiagram, nodes: Dict[str, GeomNode]):
    _infer_layered_hints(diagram, nodes)
    node_list = list(nodes.values())
    rail_meta = solve_rails(diagram, node_list)
    routes: Dict[str, Route] = route_edges(
        {node.id: node for node in node_list},
        diagram.edges,
        list(diagram.keepouts),
        rail_meta["y_centers"],
    )
    return {node.id: node for node in node_list}, routes, {}
