"""Excalidraw adapter for the managed diagram engine."""

from typing import Any

from src.domain.diagrams.engine.ir import EngineGroupFrame, EngineNode, EngineRoute
from src.domain.diagrams.families import canonical_family
from src.domain.diagrams.models import ManagedElementRef, ManifestEntry
from src.domain.diagrams.rendering.ids import stable_element_id
from src.domain.diagrams.rendering.refs import custom_data
from src.lib.excalidraw.constants import DEFAULT_FONT_FAMILY
from src.lib.excalidraw.helpers import base_excalidraw_element
from src.lib.math.text import calculate_centered_position

_PALETTES: dict[str, dict[str, str]] = {
    "workflow": {"panel": "#eff6ff", "card": "#ffffff", "accent": "#2563eb", "text": "#0f172a"},
    "static_structure": {"panel": "#f8fafc", "card": "#ffffff", "accent": "#334155", "text": "#0f172a"},
    "component_cluster": {"panel": "#ecfeff", "card": "#ffffff", "accent": "#0891b2", "text": "#0f172a"},
    "technical_blueprint": {"panel": "#eff6ff", "card": "#ffffff", "accent": "#2563eb", "text": "#0f172a"},
    "istar": {"panel": "#fff1f2", "card": "#ffffff", "accent": "#e11d48", "text": "#1f2937"},
    "architecture_flow": {"panel": "#ecfeff", "card": "#ffffff", "accent": "#0284c7", "text": "#0f172a"},
    "layered_architecture": {"panel": "#f8fafc", "card": "#ffffff", "accent": "#0f766e", "text": "#0f172a"},
    "transformer_stack": {"panel": "#eff6ff", "card": "#ffffff", "accent": "#2563eb", "text": "#0f172a"},
    "react_loop": {"panel": "#fafafa", "card": "#ffffff", "accent": "#dc2626", "text": "#1f2937"},
    "rag_pipeline": {"panel": "#fff7ed", "card": "#ffffff", "accent": "#ea580c", "text": "#1f2937"},
    "transformer": {"panel": "#eff6ff", "card": "#ffffff", "accent": "#2563eb", "text": "#0f172a"},
    "clip": {"panel": "#eff6ff", "card": "#ffffff", "accent": "#2563eb", "text": "#0f172a"},
    "llm_stack": {"panel": "#f8fafc", "card": "#ffffff", "accent": "#0f766e", "text": "#0f172a"},
    "comparison": {"panel": "#f8fafc", "card": "#ffffff", "accent": "#0f766e", "text": "#0f172a"},
    "matrix": {"panel": "#f8fafc", "card": "#ffffff", "accent": "#0f766e", "text": "#0f172a"},
    "paper_figure": {"panel": "#f8fafc", "card": "#ffffff", "accent": "#0f766e", "text": "#0f172a"},
}

_TEXT_ONLY_COMPONENTS = {"caption"}


def palette_for_family(family: str) -> dict[str, str]:
    resolved = canonical_family(family)
    return _PALETTES.get(resolved, _PALETTES["layered_architecture"])


def _shape_type(node: EngineNode) -> str:
    if node.shape in {"diamond", "ellipse"}:
        return node.shape
    if node.component_type == "badge":
        return "ellipse"
    return "rectangle"


def _text_color(node: EngineNode, palette: dict[str, str]) -> str:
    return str(node.style.get("textColor") or palette["text"])


def _font_size(node: EngineNode) -> int:
    return int(node.style.get("fontSize") or 18)


def _background_color(node: EngineNode, palette: dict[str, str]) -> str:
    if node.component_type in {"container", "panel"}:
        return str(node.style.get("backgroundColor") or palette["panel"])
    if node.component_type == "callout":
        return str(node.style.get("backgroundColor") or "#fff7ed")
    return str(node.style.get("backgroundColor") or palette["card"])


def _stroke_color(node: EngineNode, palette: dict[str, str]) -> str:
    return str(node.style.get("strokeColor") or palette["accent"])


def _text_element(
    diagram_id: str,
    semantic_id: str,
    role: str,
    text: str,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    color: str,
    font_size: int,
    container_id: str | None = None,
) -> dict[str, Any]:
    element_id = stable_element_id(diagram_id, semantic_id, role)
    element = base_excalidraw_element(
        "text",
        x=x,
        y=y,
        width=width,
        height=height,
        stroke_color=color,
        bg_color="transparent",
    )
    element.update(
        {
            "id": element_id,
            "text": text,
            "originalText": text,
            "fontSize": font_size,
            "fontFamily": DEFAULT_FONT_FAMILY,
            "textAlign": "center",
            "verticalAlign": "middle",
            "containerId": container_id,
            "autoResize": False,
            "lineHeight": 1.25,
            "customData": custom_data(
                ManagedElementRef(
                    diagramId=diagram_id,
                    semanticId=semantic_id,
                    role=role,
                    renderVersion=1,
                )
            ),
        }
    )
    return element


def node_to_elements(
    diagram_id: str,
    node: EngineNode,
) -> tuple[list[dict[str, Any]], ManifestEntry]:
    palette = palette_for_family(node.family)
    role = node.component_type
    if node.component_type in _TEXT_ONLY_COMPONENTS:
        font_size = _font_size(node)
        text = _text_element(
            diagram_id,
            node.id,
            role,
            node.label,
            node.x,
            node.y,
            node.width,
            node.height,
            color=_text_color(node, palette),
            font_size=font_size,
        )
        return (
            [text],
            ManifestEntry(
                semanticId=node.id,
                role=role,
                elementIds=[text["id"]],
                bounds={"x": node.x, "y": node.y, "width": node.width, "height": node.height},
                renderVersion=1,
            ),
        )

    shape_id = stable_element_id(diagram_id, node.id, role)
    text_id = stable_element_id(diagram_id, node.id, f"{role}_text")
    shape = base_excalidraw_element(
        _shape_type(node),
        x=node.x,
        y=node.y,
        width=node.width,
        height=node.height,
        stroke_color=_stroke_color(node, palette),
        bg_color=_background_color(node, palette),
    )
    shape.update(
        {
            "id": shape_id,
            "fillStyle": str(node.style.get("fillStyle") or "solid"),
            "roughness": int(node.style.get("roughness") or 1),
            "strokeStyle": "dashed" if node.component_type == "callout" else str(node.style.get("strokeStyle") or "solid"),
            "boundElements": [{"id": text_id, "type": "text"}],
            "customData": custom_data(
                ManagedElementRef(
                    diagramId=diagram_id,
                    semanticId=node.id,
                    role=role,
                    renderVersion=1,
                )
            ),
        }
    )
    font_size = _font_size(node)
    text_x, text_y, text_width, text_height = calculate_centered_position(
        node.x + 8,
        node.y + 8,
        max(node.width - 16, 10),
        max(node.height - 16, 10),
        node.label,
        font_size=font_size,
        font_family=DEFAULT_FONT_FAMILY,
    )
    text = _text_element(
        diagram_id,
        node.id,
        f"{role}_text",
        node.label,
        text_x,
        text_y,
        text_width,
        text_height,
        color=_text_color(node, palette),
        font_size=font_size,
        container_id=shape_id,
    )
    return (
        [shape, text],
        ManifestEntry(
            semanticId=node.id,
            role=role,
            elementIds=[shape["id"], text["id"]],
            bounds={"x": node.x, "y": node.y, "width": node.width, "height": node.height},
            renderVersion=1,
        ),
    )


def annotation_to_element(
    diagram_id: str,
    annotation_id: str,
    role: str,
    text: str,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    color: str,
    font_size: int,
) -> tuple[dict[str, Any], ManifestEntry]:
    element = _text_element(
        diagram_id,
        annotation_id,
        role,
        text,
        x,
        y,
        width,
        height,
        color=color,
        font_size=font_size,
    )
    return (
        element,
        ManifestEntry(
            semanticId=annotation_id,
            role=role,
            elementIds=[element["id"]],
            bounds={"x": x, "y": y, "width": width, "height": height},
            renderVersion=1,
        ),
    )


def title_to_element(
    diagram_id: str,
    title: str,
    x: float,
    y: float,
    width: float,
    family: str = "layered_architecture",
) -> tuple[dict[str, Any], ManifestEntry]:
    return annotation_to_element(
        diagram_id,
        "diagram.title",
        "title",
        title,
        x,
        y,
        width,
        40,
        color=palette_for_family(family)["text"],
        font_size=28,
    )


def group_to_elements(
    diagram_id: str,
    group: EngineGroupFrame,
) -> tuple[list[dict[str, Any]], ManifestEntry]:
    palette = palette_for_family(group.family)
    shape_id = stable_element_id(diagram_id, group.id, "group")
    label_id = stable_element_id(diagram_id, group.id, "group_label")
    shape = base_excalidraw_element(
        "rectangle",
        x=group.x,
        y=group.y,
        width=group.width,
        height=group.height,
        stroke_color=str(group.style.get("strokeColor") or palette["accent"]),
        bg_color=str(group.style.get("backgroundColor") or palette["panel"]),
    )
    shape.update(
        {
            "id": shape_id,
            "fillStyle": "solid",
            "roughness": 1,
            "strokeStyle": "dashed",
            "opacity": int(group.style.get("opacity") or 35),
            "customData": custom_data(
                ManagedElementRef(
                    diagramId=diagram_id,
                    semanticId=group.id,
                    role="group",
                    renderVersion=1,
                )
            ),
        }
    )
    label = _text_element(
        diagram_id,
        group.id,
        "group_label",
        group.label,
        group.x + 14,
        group.y + 10,
        max(group.width - 28, 40),
        24,
        color=str(group.style.get("textColor") or palette["accent"]),
        font_size=int(group.style.get("fontSize") or 16),
    )
    label["id"] = label_id
    label["textAlign"] = "left"
    label["verticalAlign"] = "top"
    return (
        [shape, label],
        ManifestEntry(
            semanticId=group.id,
            role="group",
            elementIds=[shape_id, label_id],
            bounds={"x": group.x, "y": group.y, "width": group.width, "height": group.height},
            renderVersion=1,
        ),
    )


def _route_bounds(route: EngineRoute) -> dict[str, float]:
    xs = [point[0] for point in route.points]
    ys = [point[1] for point in route.points]
    return {
        "x": min(xs),
        "y": min(ys),
        "width": max(xs) - min(xs) if len(xs) > 1 else 0.0,
        "height": max(ys) - min(ys) if len(ys) > 1 else 0.0,
    }


def route_to_elements(
    diagram_id: str,
    edge_id: str,
    connector_type: str,
    route: EngineRoute,
    *,
    stroke: str,
    source_shape_id: str | None,
    target_shape_id: str | None,
) -> tuple[list[dict[str, Any]], ManifestEntry]:
    bounds = _route_bounds(route)
    points = [
        [point_x - bounds["x"], point_y - bounds["y"]]
        for point_x, point_y in route.points
    ]
    arrow = base_excalidraw_element(
        "arrow",
        x=bounds["x"],
        y=bounds["y"],
        width=bounds["width"],
        height=bounds["height"],
        stroke_color=stroke,
        bg_color="transparent",
    )
    arrow.update(
        {
            "id": stable_element_id(diagram_id, edge_id, "connector"),
            "points": points,
            "startBinding": {"elementId": source_shape_id, "focus": 0, "gap": 0} if source_shape_id else None,
            "endBinding": {"elementId": target_shape_id, "focus": 0, "gap": 0} if target_shape_id else None,
            "startArrowhead": None,
            "endArrowhead": "arrow" if connector_type != "line" else None,
            "strokeStyle": "dashed" if connector_type == "dashed-arrow" else "solid",
            "customData": custom_data(
                ManagedElementRef(
                    diagramId=diagram_id,
                    semanticId=edge_id,
                    role="connector",
                    renderVersion=1,
                )
            ),
        }
    )
    elements: list[dict[str, Any]] = [arrow]
    element_ids = [arrow["id"]]
    if route.label is not None:
        label = _text_element(
            diagram_id,
            edge_id,
            "connector_label",
            route.label.text,
            route.label.x,
            route.label.y,
            route.label.width,
            route.label.height,
            color=stroke,
            font_size=14,
        )
        elements.append(label)
        element_ids.append(label["id"])
    return (
        elements,
        ManifestEntry(
            semanticId=edge_id,
            role="connector",
            elementIds=element_ids,
            bounds=bounds,
            renderVersion=1,
        ),
    )
