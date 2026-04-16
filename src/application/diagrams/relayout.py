"""Helpers for constraining relayout to the locally impacted subgraph."""

from src.domain.diagrams.models import DiagramPatch, DiagramSpec


def _adjacency(spec: DiagramSpec) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for component in spec.components:
        graph.setdefault(component.id, set())
    for connector in spec.connectors:
        graph.setdefault(connector.from_component, set()).add(connector.to_component)
        graph.setdefault(connector.to_component, set()).add(connector.from_component)
    return graph


def _connector_endpoints(spec: DiagramSpec) -> dict[str, tuple[str, str]]:
    return {
        connector.id: (connector.from_component, connector.to_component)
        for connector in spec.connectors
    }


def _component_neighbor_hints(patch: DiagramPatch) -> set[str]:
    neighbors: set[str] = set()
    for component in patch.component_additions:
        raw_neighbors = component.data.get("relayoutNeighbors")
        if not isinstance(raw_neighbors, list):
            continue
        neighbors.update(
            neighbor
            for neighbor in raw_neighbors
            if isinstance(neighbor, str) and neighbor
        )
    return neighbors


def compute_relayout_scope(
    previous_spec: DiagramSpec,
    updated_spec: DiagramSpec,
    patch: DiagramPatch,
) -> set[str]:
    """Return impacted nodes plus one-hop neighbors that should remain movable."""

    previous_adjacency = _adjacency(previous_spec)
    updated_adjacency = _adjacency(updated_spec)
    previous_endpoints = _connector_endpoints(previous_spec)
    updated_endpoints = _connector_endpoints(updated_spec)
    updated_component_ids = {component.id for component in updated_spec.components}

    directly_impacted: set[str] = set(patch.component_updates)
    directly_impacted.update(component.id for component in patch.component_additions)
    directly_impacted.update(patch.component_removals)
    directly_impacted.update(_component_neighbor_hints(patch))

    for connector in patch.connector_additions:
        directly_impacted.add(connector.from_component)
        directly_impacted.add(connector.to_component)

    for connector_id in patch.connector_updates:
        for endpoints in (
            previous_endpoints.get(connector_id),
            updated_endpoints.get(connector_id),
        ):
            if endpoints is None:
                continue
            directly_impacted.update(endpoints)

    for connector_id in patch.connector_removals:
        endpoints = previous_endpoints.get(connector_id)
        if endpoints is not None:
            directly_impacted.update(endpoints)

    if not directly_impacted:
        return set()

    scope: set[str] = set()
    for component_id in directly_impacted:
        if component_id in updated_component_ids:
            scope.add(component_id)
        scope.update(
            neighbor
            for neighbor in previous_adjacency.get(component_id, set())
            if neighbor in updated_component_ids
        )
        scope.update(
            neighbor
            for neighbor in updated_adjacency.get(component_id, set())
            if neighbor in updated_component_ids
        )
    return scope


def compute_reroute_scope(
    previous_spec: DiagramSpec,
    updated_spec: DiagramSpec,
    patch: DiagramPatch,
    relayout_scope: set[str],
) -> set[str]:
    """Return updated edges whose geometry should be recomputed."""

    updated_endpoints = _connector_endpoints(updated_spec)
    previous_endpoints = _connector_endpoints(previous_spec)
    directly_impacted: set[str] = set(patch.connector_updates)
    directly_impacted.update(connector.id for connector in patch.connector_additions)

    for connector_id, (source_id, target_id) in updated_endpoints.items():
        if source_id in relayout_scope or target_id in relayout_scope:
            directly_impacted.add(connector_id)

    for connector_id in patch.connector_removals:
        if connector_id in previous_endpoints:
            directly_impacted.add(connector_id)

    return {
        connector_id
        for connector_id in directly_impacted
        if connector_id in updated_endpoints
    }
