"""Helpers for commit hashes and Yjs-aware diffing."""

import hashlib
import json
from typing import Dict, List, Tuple

from pycrdt import Array, Doc, Map

from src.persistence.yjs.diagrams import DIAGRAM_SPECS_KEY, DIAGRAM_STATE_KEY
from src.domain.diagrams.models import DiagramSpec
from src.domain.versioning.models import DiagramChange, DiagramSummaryItem, ElementChange
from src.infra.logging import get_logger

logger = get_logger(__name__)


def generate_commit_hash(commit_id: int, timestamp: int) -> str:
    """Generate a stable short hash for local commits."""

    payload = f"{commit_id}-{timestamp}"
    return hashlib.sha1(payload.encode()).hexdigest()[:7]


def parse_yjs_elements(data: bytes) -> dict:
    """Extract Excalidraw elements from a Yjs document update."""

    if not data:
        return {}

    try:
        ydoc = Doc()
        ydoc.apply_update(data)

        result = {}
        elements_array = ydoc.get("elements", type=Array)
        if elements_array is None:
            return result

        for element in elements_array:
            if isinstance(element, Map):
                element_dict = dict(element)
            elif isinstance(element, dict):
                element_dict = element
            else:
                continue

            element_id = element_dict.get("id")
            if element_id:
                result[element_id] = element_dict

        return result
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Failed to parse Yjs elements: %s", exc)
        return {}


def parse_yjs_diagrams(data: bytes) -> dict[str, dict]:
    """Extract spec-first managed diagrams from a Yjs document update."""

    if not data:
        return {}

    try:
        ydoc = Doc()
        ydoc.apply_update(data)

        specs_map = ydoc.get(DIAGRAM_SPECS_KEY, type=Map)
        states_map = ydoc.get(DIAGRAM_STATE_KEY, type=Map)
        if specs_map is None:
            return {}

        diagrams: dict[str, dict] = {}
        for diagram_id, raw_spec in specs_map.items():
            if not isinstance(raw_spec, str):
                continue
            try:
                spec_payload = json.loads(raw_spec)
                spec = DiagramSpec.model_validate(spec_payload)
            except Exception:  # pylint: disable=broad-except
                continue

            managed_state = "managed"
            if states_map is not None:
                raw_state = states_map.get(diagram_id)
                if isinstance(raw_state, str):
                    try:
                        state_payload = json.loads(raw_state)
                        managed_state = str(
                            state_payload.get("managedState")
                            or state_payload.get("managed_state")
                            or managed_state
                        )
                    except json.JSONDecodeError:
                        pass

            diagrams[diagram_id] = {
                "diagram_id": spec.diagram_id,
                "title": spec.title or spec.diagram_type,
                "family": spec.family,
                "managed_state": managed_state,
                "component_count": len(spec.components),
                "connector_count": len(spec.connectors),
                "version": spec.version,
            }

        return diagrams
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Failed to parse Yjs diagrams: %s", exc)
        return {}


def compute_elements_diff(
    old_elements: dict, new_elements: dict
) -> Tuple[int, int, int, List[ElementChange]]:
    """Compute element-level diff between two element maps."""

    old_ids = set(old_elements.keys())
    new_ids = set(new_elements.keys())

    added_ids = new_ids - old_ids
    removed_ids = old_ids - new_ids
    common_ids = old_ids & new_ids

    modified_ids = {
        element_id
        for element_id in common_ids
        if _element_changed(
            old_elements.get(element_id, {}),
            new_elements.get(element_id, {}),
        )
    }

    changes: List[ElementChange] = []

    for element_id in added_ids:
        element = new_elements.get(element_id, {})
        changes.append(
            ElementChange(
                element_id=element_id,
                action="added",
                element_type=element.get("type") if isinstance(element, dict) else None,
                text=element.get("text") if isinstance(element, dict) else None,
            )
        )

    for element_id in removed_ids:
        element = old_elements.get(element_id, {})
        changes.append(
            ElementChange(
                element_id=element_id,
                action="removed",
                element_type=element.get("type") if isinstance(element, dict) else None,
                text=element.get("text") if isinstance(element, dict) else None,
            )
        )

    for element_id in modified_ids:
        element = new_elements.get(element_id, {})
        changes.append(
            ElementChange(
                element_id=element_id,
                action="modified",
                element_type=element.get("type") if isinstance(element, dict) else None,
                text=element.get("text") if isinstance(element, dict) else None,
            )
        )

    return len(added_ids), len(removed_ids), len(modified_ids), changes


def compute_diagrams_diff(
    old_diagrams: Dict[str, dict], new_diagrams: Dict[str, dict]
) -> Tuple[int, int, int, List[DiagramChange]]:
    """Compute diagram-level diff between two diagram maps."""

    old_ids = set(old_diagrams.keys())
    new_ids = set(new_diagrams.keys())

    added_ids = new_ids - old_ids
    removed_ids = old_ids - new_ids
    common_ids = old_ids & new_ids

    modified_ids = {
        diagram_id
        for diagram_id in common_ids
        if _diagram_changed(
            old_diagrams.get(diagram_id, {}),
            new_diagrams.get(diagram_id, {}),
        )
    }

    changes: List[DiagramChange] = []

    for diagram_id in added_ids:
        diagram = new_diagrams.get(diagram_id, {})
        changes.append(
            DiagramChange(
                diagram_id=diagram_id,
                action="added",
                title=str(diagram.get("title", "")),
                family=str(diagram.get("family", "layered_architecture")),
                managed_state=_optional_str(diagram.get("managed_state")),
                component_count=_optional_int(diagram.get("component_count")),
                connector_count=_optional_int(diagram.get("connector_count")),
            )
        )

    for diagram_id in removed_ids:
        diagram = old_diagrams.get(diagram_id, {})
        changes.append(
            DiagramChange(
                diagram_id=diagram_id,
                action="removed",
                title=str(diagram.get("title", "")),
                family=str(diagram.get("family", "layered_architecture")),
                managed_state=_optional_str(diagram.get("managed_state")),
                component_count=_optional_int(diagram.get("component_count")),
                connector_count=_optional_int(diagram.get("connector_count")),
            )
        )

    for diagram_id in modified_ids:
        diagram = new_diagrams.get(diagram_id, {})
        changes.append(
            DiagramChange(
                diagram_id=diagram_id,
                action="modified",
                title=str(diagram.get("title", "")),
                family=str(diagram.get("family", "layered_architecture")),
                managed_state=_optional_str(diagram.get("managed_state")),
                component_count=_optional_int(diagram.get("component_count")),
                connector_count=_optional_int(diagram.get("connector_count")),
            )
        )

    return len(added_ids), len(removed_ids), len(modified_ids), changes


def summarize_diagrams(diagrams: Dict[str, dict]) -> tuple[list[DiagramSummaryItem], dict, dict]:
    """Build summary items plus family/state counters."""

    items: list[DiagramSummaryItem] = []
    families: dict[str, int] = {}
    managed_states: dict[str, int] = {}

    for diagram in diagrams.values():
        family = str(diagram.get("family", "layered_architecture"))
        managed_state = str(diagram.get("managed_state", "managed"))
        items.append(
            DiagramSummaryItem(
                diagram_id=str(diagram.get("diagram_id", "")),
                title=str(diagram.get("title", "")),
                family=family,
                managed_state=managed_state,
                component_count=int(diagram.get("component_count", 0) or 0),
                connector_count=int(diagram.get("connector_count", 0) or 0),
                version=int(diagram.get("version", 1) or 1),
            )
        )
        families[family] = families.get(family, 0) + 1
        managed_states[managed_state] = managed_states.get(managed_state, 0) + 1

    items.sort(key=lambda item: item.diagram_id)
    return items, families, managed_states


def _element_changed(old: dict, new: dict) -> bool:
    if not isinstance(old, dict) or not isinstance(new, dict):
        return str(old) != str(new)

    key_fields = [
        "x",
        "y",
        "width",
        "height",
        "text",
        "strokeColor",
        "backgroundColor",
        "isDeleted",
    ]
    for field in key_fields:
        if old.get(field) != new.get(field):
            return True

    return old.get("version") != new.get("version")


def _diagram_changed(old: dict, new: dict) -> bool:
    fields = [
        "title",
        "family",
        "managed_state",
        "component_count",
        "connector_count",
        "version",
    ]
    return any(old.get(field) != new.get(field) for field in fields)


def _optional_str(value: object) -> str | None:
    return str(value) if value is not None else None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None

