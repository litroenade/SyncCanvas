"""Thin bridge from DiagramSpec to the vendored next-generation engine."""


from collections import defaultdict, deque
from collections.abc import Collection
from dataclasses import dataclass
from typing import Callable

from src.domain.diagrams.engine.ir import EngineGroupFrame, EngineLabel, EngineNode, EngineRoute
from src.domain.diagrams.families import canonical_family
from src.domain.diagrams.models import DiagramSpec
from src.infra.logging import get_logger

from .vendor_nextgen.architecture_engine import build_architecture_flow
from .vendor_nextgen.blueprint_engine import build_blueprint
from .vendor_nextgen.component_engine import build_component_cluster
from .vendor_nextgen.constraint_solver import group_bounds, solve_rails
from .vendor_nextgen.istar_engine import build_istar
from .vendor_nextgen.layered_engine import build_layered_architecture
from .vendor_nextgen.rag_engine import build_rag_pipeline
from .vendor_nextgen.react_engine import build_react_loop
from .vendor_nextgen.router import route_edges
from .vendor_nextgen.semantic_ir import GeomNode, LabelBox, Route, SemanticDiagram, SemanticEdge, SemanticGroup, SemanticNode
from .vendor_nextgen.text_fit import fit_diagram
from .vendor_nextgen.transformer_engine import build_transformer_stack
from .vendor_nextgen.workflow_engine import build_workflow

RectTuple = tuple[float, float, float, float]
logger = get_logger(__name__)
FamilyEngine = Callable[
    [SemanticDiagram, dict[str, GeomNode]],
    tuple[dict[str, GeomNode], dict[str, Route], dict[str, RectTuple]],
]

_FAMILY_ENGINES: dict[str, FamilyEngine] = {
    "workflow": build_workflow,
    "component_cluster": build_component_cluster,
    "architecture_flow": build_architecture_flow,
    "layered_architecture": build_layered_architecture,
    "transformer_stack": build_transformer_stack,
    "react_loop": build_react_loop,
    "rag_pipeline": build_rag_pipeline,
    "technical_blueprint": build_blueprint,
    "istar": build_istar,
}

_FIXED_ID_FAMILY_REQUIREMENTS: dict[str, dict[str, set[str]]] = {
    "workflow": {
        "nodes": {"start", "validate", "stock", "reserve", "charge", "done", "notify"},
        "edges": {"e0", "e1", "e2", "e3", "e4", "e5", "e6"},
    },
    "component_cluster": {
        "nodes": {"web", "api", "auth", "order", "pay", "db"},
        "edges": {"e0", "e1", "e2", "e3", "e4", "e5", "e6"},
    },
    "architecture_flow": {
        "nodes": {"local", "build", "cache", "network", "maven", "ivy"},
        "edges": {"e0", "e1", "e2", "e3", "e4", "e5"},
    },
    "technical_blueprint": {
        "nodes": {"plc", "servo", "io", "hmi", "motor", "sensor", "tb"},
        "edges": {"e0", "e1", "e2", "e3", "e4"},
    },
    "istar": {
        "nodes": {"actor", "goal1", "task1", "res1", "soft1", "goal2"},
        "edges": {"e0", "e1", "e2", "e3"},
    },
}

_SHAPE_BY_KIND: dict[str, str] = {
    "decision": "diamond",
    "terminator": "ellipse",
    "goal": "ellipse",
    "softgoal": "ellipse",
    "network": "ellipse",
}

_DEFAULT_COMPONENT_TYPE_BY_KIND: dict[str, str] = {
    "process": "process",
    "decision": "decision",
    "terminator": "terminator",
    "class": "class",
    "interface": "interface",
    "component": "component",
    "database": "database",
    "device": "device",
    "title_block": "title_block",
    "goal": "goal",
    "task": "task",
    "resource": "resource",
    "softgoal": "softgoal",
    "network": "network",
}


@dataclass(frozen=True, slots=True)
class VendorLayoutResult:
    spec: DiagramSpec
    nodes: list[EngineNode]
    routes: dict[str, EngineRoute]
    groups: list[EngineGroupFrame]


def build_vendor_layout(
    spec: DiagramSpec,
    *,
    relayout_scope: Collection[str] | None = None,
    reroute_scope: Collection[str] | None = None,
) -> VendorLayoutResult:
    normalized_spec = DiagramSpec.model_validate(spec.model_dump(by_alias=True))
    normalized_spec.family = canonical_family(normalized_spec.family)
    normalized_spec.diagram_type = canonical_family(normalized_spec.diagram_type)
    use_family_engine = _use_family_engine(normalized_spec, relayout_scope)
    if use_family_engine and "vendorUseFamilyEngine" not in normalized_spec.layout_constraints:
        normalized_spec.layout_constraints["vendorUseFamilyEngine"] = True

    diagram = _spec_to_semantic_diagram(normalized_spec)
    locked_positions = _locked_positions(normalized_spec, relayout_scope)
    node_lookup, route_lookup, explicit_group_rects = _layout_diagram(
        diagram,
        use_family_engine=use_family_engine,
        locked_positions=locked_positions,
    )
    _update_component_geometry(normalized_spec, node_lookup)

    return VendorLayoutResult(
        spec=normalized_spec,
        nodes=_engine_nodes(normalized_spec, node_lookup),
        routes=_engine_routes(normalized_spec, diagram, route_lookup, reroute_scope),
        groups=_group_frames(normalized_spec, node_lookup, explicit_group_rects),
    )


def _use_family_engine(spec: DiagramSpec, relayout_scope: Collection[str] | None) -> bool:
    if relayout_scope is not None:
        return False
    family = canonical_family(spec.family)
    if family not in _FAMILY_ENGINES:
        return False
    if "vendorUseFamilyEngine" in spec.layout_constraints:
        return bool(spec.layout_constraints.get("vendorUseFamilyEngine"))
    return not _has_meaningful_component_grid(spec)


def _locked_positions(
    spec: DiagramSpec,
    relayout_scope: Collection[str] | None,
) -> dict[str, tuple[float, float]] | None:
    if relayout_scope is None:
        return None
    scope = set(relayout_scope)
    return {
        component.id: (float(component.x), float(component.y))
        for component in spec.components
        if component.id not in scope
    }


def _spec_to_semantic_diagram(spec: DiagramSpec) -> SemanticDiagram:
    family = canonical_family(spec.family)
    groups = [
        SemanticGroup(
            id=group.id,
            label=group.label,
            kind=str(group.style.get("kind") or "frame"),
            members=list(group.component_ids),
        )
        for group in spec.groups
    ]
    component_groups: dict[str, str] = {}
    for group in groups:
        for member in group.members:
            component_groups.setdefault(member, group.id)

    nodes = [
        SemanticNode(
            id=component.id,
            label=component.label or component.text,
            kind=_component_kind(component.component_type, component.shape, component.data),
            family=family,
            row_hint=_as_int(component.data.get("rowHint")),
            col_hint=_as_int(component.data.get("colHint")),
            attrs=_string_list(component.data.get("attrs")),
            methods=_string_list(component.data.get("methods")),
            group=component_groups.get(component.id) or _string_or_none(component.data.get("groupId")),
            style_role=_string_or_none(component.data.get("styleRole")) or "default",
            meta={
                **dict(component.data),
                "componentType": component.component_type,
                "shape": component.shape,
                "style": dict(component.style),
                "data": dict(component.data),
            },
        )
        for component in spec.components
    ]
    edges = [
        SemanticEdge(
            id=connector.id,
            src=connector.from_component,
            dst=connector.to_component,
            kind=_string_or_none(connector.data.get("vendorKind")) or connector.connector_type,
            label=connector.label,
            dashed=connector.connector_type == "dashed-arrow",
            preferred_dir=_string_or_none(connector.data.get("preferredDir")),
            meta=dict(connector.data),
        )
        for connector in spec.connectors
        if connector.from_component != connector.to_component
    ]
    return SemanticDiagram(
        id=spec.diagram_id,
        title=spec.title,
        family=family,
        nodes=nodes,
        edges=edges,
        groups=groups,
        keepouts=_keepouts(spec),
        meta=dict(spec.layout_constraints),
    )


def _layout_diagram(
    diagram: SemanticDiagram,
    *,
    use_family_engine: bool,
    locked_positions: dict[str, tuple[float, float]] | None,
) -> tuple[dict[str, GeomNode], dict[str, Route], dict[str, RectTuple]]:
    fitted_nodes = fit_diagram(diagram)
    fitted_lookup = {node.id: node for node in fitted_nodes}
    if use_family_engine:
        builder = _FAMILY_ENGINES.get(diagram.family)
        if builder is not None:
            compatible, reason = _specialized_engine_compatibility(diagram)
            if compatible:
                try:
                    nodes, routes, group_rects = builder(diagram, fitted_lookup)
                    return nodes, routes, group_rects
                except Exception as exc:  # pylint: disable=broad-except
                    logger.warning(
                        "Vendored family engine failed; falling back to generic solver: diagram_id=%s family=%s error=%s",
                        diagram.id,
                        diagram.family,
                        exc,
                    )
            else:
                logger.info(
                    "Skipping vendored family engine for diagram_id=%s family=%s reason=%s",
                    diagram.id,
                    diagram.family,
                    reason,
                )
    if not _has_meaningful_geom_grid(fitted_lookup):
        _infer_graph_hints(diagram, fitted_lookup)
    rail_meta = solve_rails(diagram, fitted_nodes, patch_locked=locked_positions)
    routes = route_edges(
        {node.id: node for node in fitted_nodes},
        diagram.edges,
        list(diagram.keepouts),
        rail_meta["y_centers"],
    )
    return {node.id: node for node in fitted_nodes}, routes, group_bounds(fitted_nodes)


def _specialized_engine_compatibility(diagram: SemanticDiagram) -> tuple[bool, str]:
    requirements = _FIXED_ID_FAMILY_REQUIREMENTS.get(diagram.family)
    if requirements is None:
        return True, "dynamic"
    node_ids = {node.id for node in diagram.nodes}
    edge_ids = {edge.id for edge in diagram.edges}
    if requirements["nodes"].issubset(node_ids) and requirements["edges"].issubset(edge_ids):
        return True, "fixed-id"
    return False, "missing_required_ids"


def _update_component_geometry(spec: DiagramSpec, node_lookup: dict[str, GeomNode]) -> None:
    for component in spec.components:
        node = node_lookup.get(component.id)
        if node is None:
            continue
        component.x = float(node.x)
        component.y = float(node.y)
        component.width = float(node.w)
        component.height = float(node.h)
        component.data = {
            **component.data,
            "rowHint": int(node.row),
            "colHint": int(node.col),
        }
        component.style = {**component.style, "fontSize": int(component.style.get("fontSize") or 18)}


def _engine_nodes(spec: DiagramSpec, node_lookup: dict[str, GeomNode]) -> list[EngineNode]:
    nodes: list[EngineNode] = []
    for component in spec.components:
        node = node_lookup.get(component.id)
        if node is None:
            continue
        meta = dict(node.meta)
        nodes.append(
            EngineNode(
                id=node.id,
                component_type=_string_or_none(meta.get("componentType"))
                or _DEFAULT_COMPONENT_TYPE_BY_KIND.get(node.kind, "block"),
                label=node.label,
                shape=_string_or_none(meta.get("shape")) or _SHAPE_BY_KIND.get(node.kind, "rectangle"),
                family=canonical_family(spec.family),
                x=float(node.x),
                y=float(node.y),
                width=float(node.w),
                height=float(node.h),
                row_hint=int(node.row),
                col_hint=int(node.col),
                style=dict(meta.get("style") or component.style),
                data=dict(meta.get("data") or component.data),
                layout_locked=False,
            )
        )
    return nodes


def _engine_routes(
    spec: DiagramSpec,
    diagram: SemanticDiagram,
    route_lookup: dict[str, Route],
    reroute_scope: Collection[str] | None,
) -> dict[str, EngineRoute]:
    edge_lookup = {edge.id: edge for edge in diagram.edges}
    scope = set(reroute_scope) if reroute_scope is not None else None
    routes: dict[str, EngineRoute] = {}
    for connector in spec.connectors:
        if scope is not None and connector.id not in scope:
            preserved = _preserved_route(connector)
            if preserved is not None:
                routes[connector.id] = preserved
                continue
        route = route_lookup.get(connector.id)
        edge = edge_lookup.get(connector.id)
        if route is None or edge is None:
            preserved = _preserved_route(connector)
            if preserved is not None:
                routes[connector.id] = preserved
            continue
        routes[connector.id] = EngineRoute(
            edge_id=connector.id,
            source_id=edge.src,
            target_id=edge.dst,
            points=[(float(point_x), float(point_y)) for point_x, point_y in route.points],
            label=_engine_label(route.label),
        )
    return routes


def _group_frames(
    spec: DiagramSpec,
    node_lookup: dict[str, GeomNode],
    explicit_rects: dict[str, RectTuple] | None = None,
) -> list[EngineGroupFrame]:
    groups: list[EngineGroupFrame] = []
    remaining_rects = dict(explicit_rects or {})
    for group in spec.groups:
        rect = remaining_rects.pop(group.id, None)
        if rect is None:
            matching_key = next(
                (
                    key
                    for key in remaining_rects
                    if key.casefold() == (group.label or group.id).casefold()
                ),
                None,
            )
            if matching_key is not None:
                rect = remaining_rects.pop(matching_key)
        if rect is None:
            members = [
                node_lookup[component_id]
                for component_id in group.component_ids
                if component_id in node_lookup
            ]
            if not members:
                continue
            left = min(member.x for member in members) - 40.0
            top = min(member.y for member in members) - 44.0
            right = max(member.x + member.w for member in members) + 40.0
            bottom = max(member.y + member.h for member in members) + 44.0
        else:
            left, top, right, bottom = rect
        groups.append(
            EngineGroupFrame(
                id=group.id,
                label=group.label or group.id,
                family=canonical_family(spec.family),
                x=float(left),
                y=float(top),
                width=float(right - left),
                height=float(bottom - top),
                style=dict(group.style),
            )
        )
    for group_id, rect in remaining_rects.items():
        left, top, right, bottom = rect
        groups.append(
            EngineGroupFrame(
                id=group_id,
                label=group_id,
                family=canonical_family(spec.family),
                x=float(left),
                y=float(top),
                width=float(right - left),
                height=float(bottom - top),
                style={},
            )
        )
    return groups


def _preserved_route(connector) -> EngineRoute | None:
    raw_points = connector.data.get("routePoints")
    if not isinstance(raw_points, list) or len(raw_points) < 2:
        return None
    points: list[tuple[float, float]] = []
    for item in raw_points:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            return None
        try:
            points.append((float(item[0]), float(item[1])))
        except (TypeError, ValueError):
            return None
    label = None
    raw_label = connector.data.get("labelBox")
    if isinstance(raw_label, dict) and isinstance(raw_label.get("text"), str):
        try:
            label = EngineLabel(
                text=str(raw_label["text"]),
                x=float(raw_label.get("x", 0.0)),
                y=float(raw_label.get("y", 0.0)),
                width=float(raw_label.get("width", 0.0)),
                height=float(raw_label.get("height", 0.0)),
                edge_id=connector.id,
            )
        except (TypeError, ValueError):
            label = None
    return EngineRoute(
        edge_id=connector.id,
        source_id=connector.from_component,
        target_id=connector.to_component,
        points=points,
        label=label,
    )


def _engine_label(label: LabelBox | None) -> EngineLabel | None:
    if label is None:
        return None
    return EngineLabel(
        text=label.text,
        x=float(label.x),
        y=float(label.y),
        width=float(label.w),
        height=float(label.h),
        edge_id=label.edge_id,
    )


def _keepouts(spec: DiagramSpec) -> list[RectTuple]:
    keepouts = spec.layout_constraints.get("keepouts")
    if not isinstance(keepouts, list):
        return []
    parsed: list[RectTuple] = []
    for keepout in keepouts:
        if isinstance(keepout, dict):
            values = (keepout.get("x1"), keepout.get("y1"), keepout.get("x2"), keepout.get("y2"))
        elif isinstance(keepout, (list, tuple)) and len(keepout) == 4:
            values = keepout
        else:
            continue
        try:
            parsed.append(
                (
                    float(values[0]),
                    float(values[1]),
                    float(values[2]),
                    float(values[3]),
                )
            )
        except (TypeError, ValueError):
            continue
    return parsed


def _component_kind(component_type: str, shape: str, data: dict) -> str:
    vendor_kind = _string_or_none(data.get("vendorKind"))
    if vendor_kind:
        return vendor_kind
    if component_type in _DEFAULT_COMPONENT_TYPE_BY_KIND:
        return component_type
    if shape == "diamond":
        return "decision"
    if shape == "ellipse":
        return "terminator"
    return "process"


def _has_meaningful_component_grid(spec: DiagramSpec) -> bool:
    explicit = False
    rows: set[int] = set()
    cols: set[int] = set()
    for component in spec.components:
        row_hint = component.data.get("rowHint")
        col_hint = component.data.get("colHint")
        if row_hint is None and col_hint is None:
            continue
        explicit = True
        if row_hint is not None:
            rows.add(_as_int(row_hint))
        if col_hint is not None:
            cols.add(_as_int(col_hint))
    return explicit and (len(rows) > 1 or len(cols) > 1)


def _has_meaningful_geom_grid(nodes: dict[str, GeomNode]) -> bool:
    return len({node.row for node in nodes.values()}) > 1 or len(
        {node.col for node in nodes.values()}
    ) > 1


def _node_sort_key(node: GeomNode) -> tuple[int, int, str, str]:
    return (int(node.col), int(node.row), node.label.casefold(), node.id.casefold())


def _infer_graph_hints(diagram: SemanticDiagram, nodes: dict[str, GeomNode]) -> None:
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
        for child_id in sorted(outgoing[node.id], key=lambda item: _node_sort_key(nodes[item])):
            layer_by_id[child_id] = max(layer_by_id.get(child_id, 0), base_layer + 1)
            incoming[child_id] -= 1
            if incoming[child_id] == 0:
                queue.append(nodes[child_id])

    if len(visited) != len(nodes):
        fallback_col = max(layer_by_id.values(), default=-1) + 1
        for node in sorted(nodes.values(), key=_node_sort_key):
            if node.id in visited:
                continue
            layer_by_id[node.id] = fallback_col
            fallback_col += 1

    buckets: dict[int, list[GeomNode]] = defaultdict(list)
    for node in nodes.values():
        buckets[layer_by_id.get(node.id, 0)].append(node)

    for col, members in sorted(buckets.items()):
        for row, node in enumerate(sorted(members, key=_node_sort_key)):
            node.row = row
            node.col = col


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _string_or_none(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
