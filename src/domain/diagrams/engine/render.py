"""Bridge from DiagramSpec to the vendored next-generation managed diagram engine."""

import random
from collections.abc import Collection
from typing import Any

from src.domain.diagrams.engine.excalidraw import (
    annotation_to_element,
    group_to_elements,
    node_to_elements,
    palette_for_family,
    route_to_elements,
    title_to_element,
)
from src.domain.diagrams.engine.ir import EngineRoute
from src.domain.diagrams.engine.vendor_bridge import build_vendor_layout
from src.domain.diagrams.models import (
    DiagramBundle,
    DiagramSpec,
    DiagramState,
    DiagramSummary,
    RenderManifest,
)


def _persist_route_metadata(spec: DiagramSpec, routes: dict[str, EngineRoute]) -> None:
    for connector in spec.connectors:
        route = routes.get(connector.id)
        if route is None:
            continue
        connector.data["routePoints"] = [
            [float(point_x), float(point_y)]
            for point_x, point_y in route.points
        ]
        if route.label is None:
            connector.data.pop("labelBox", None)
            continue
        connector.data["labelBox"] = {
            "text": route.label.text,
            "x": float(route.label.x),
            "y": float(route.label.y),
            "width": float(route.label.width),
            "height": float(route.label.height),
        }


def render_spec(
    spec: DiagramSpec,
    *,
    relayout_scope: Collection[str] | None = None,
    reroute_scope: Collection[str] | None = None,
) -> DiagramBundle:
    layout = build_vendor_layout(
        spec,
        relayout_scope=relayout_scope,
        reroute_scope=reroute_scope,
    )
    normalized_spec = layout.spec
    routes = layout.routes
    _persist_route_metadata(normalized_spec, routes)

    preview_elements: list[dict[str, Any]] = []
    entries = []
    rendered_shape_ids: dict[str, str] = {}
    palette = palette_for_family(normalized_spec.family)

    if normalized_spec.title:
        title_element, title_entry = title_to_element(
            normalized_spec.diagram_id,
            normalized_spec.title,
            float(normalized_spec.layout.get("titleX", 120)),
            float(normalized_spec.layout.get("titleY", 20)),
            float(normalized_spec.layout.get("titleWidth", 840)),
            normalized_spec.family,
        )
        preview_elements.append(title_element)
        entries.append(title_entry)

    for group in layout.groups:
        elements, entry = group_to_elements(normalized_spec.diagram_id, group)
        preview_elements.extend(elements)
        entries.append(entry)

    for node in layout.nodes:
        elements, entry = node_to_elements(normalized_spec.diagram_id, node)
        preview_elements.extend(elements)
        entries.append(entry)
        if elements and node.component_type != "caption":
            rendered_shape_ids[node.id] = elements[0]["id"]

    for annotation in normalized_spec.annotations:
        element, entry = annotation_to_element(
            normalized_spec.diagram_id,
            annotation.id,
            annotation.annotation_type,
            annotation.text,
            annotation.x,
            annotation.y,
            annotation.width,
            annotation.height,
            color=str(annotation.style.get("textColor") or palette["text"]),
            font_size=int(annotation.style.get("fontSize") or 16),
        )
        preview_elements.append(element)
        entries.append(entry)

    for connector in normalized_spec.connectors:
        route = routes.get(connector.id)
        if route is None:
            continue
        elements, entry = route_to_elements(
            normalized_spec.diagram_id,
            connector.id,
            connector.connector_type,
            route,
            stroke=str(connector.style.get("strokeColor") or palette["accent"]),
            source_shape_id=rendered_shape_ids.get(connector.from_component),
            target_shape_id=rendered_shape_ids.get(connector.to_component),
        )
        preview_elements.extend(elements)
        entries.append(entry)

    rng = random.Random(normalized_spec.diagram_id)
    for element in preview_elements:
        element["seed"] = rng.randint(1, 100000)
        element["version"] = normalized_spec.version
        element["versionNonce"] = rng.randint(1, 1000000000)

    manifest = RenderManifest(
        diagramId=normalized_spec.diagram_id,
        renderVersion=normalized_spec.version,
        entries=entries,
    )
    state = DiagramState(
        diagramId=normalized_spec.diagram_id,
        managedState="managed",
        managedScope=[component.id for component in normalized_spec.components],
        lastEditSource="system",
        lastPatchSummary="",
    )
    summary = DiagramSummary(
        diagramId=normalized_spec.diagram_id,
        title=normalized_spec.title or normalized_spec.diagram_type,
        family=normalized_spec.family,
        componentCount=len(normalized_spec.components),
        connectorCount=len(normalized_spec.connectors),
        managedState=state.managed_state,
        managedElementCount=sum(len(entry.element_ids) for entry in entries),
    )
    return DiagramBundle(
        spec=normalized_spec,
        manifest=manifest,
        state=state,
        previewElements=preview_elements,
        previewFiles={},
        summary=summary,
    )
