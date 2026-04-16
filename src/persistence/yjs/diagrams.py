"""Y.Doc storage helpers for diagram specs and manifests."""

import json
from typing import Any, Dict, List, Optional

from pycrdt import Doc, Map

from src.domain.diagrams.models import (
    DiagramBundle,
    DiagramSpec,
    DiagramState,
    ManagedElementRef,
    RenderManifest,
)

DIAGRAM_SPECS_KEY = "diagram_specs"
DIAGRAM_MANIFESTS_KEY = "diagram_manifests"
DIAGRAM_STATE_KEY = "diagram_state"
DIAGRAM_INDEX_KEY = "diagram_index"


def _get_json_map(doc: Doc, key: str) -> Map:
    return doc.get(key, type=Map)


def _loads_map_value(mapping: Map, key: str) -> Optional[Dict[str, Any]]:
    raw = mapping.get(key)
    if not isinstance(raw, str) or not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _store_json(mapping: Map, key: str, payload: Dict[str, Any]) -> None:
    mapping[key] = json.dumps(payload, ensure_ascii=False)


def _preview_element_ref(element: Dict[str, Any]) -> Optional[ManagedElementRef]:
    custom_data = element.get("customData")
    if not isinstance(custom_data, dict):
        return None
    sync_data = custom_data.get("syncCanvas")
    if not isinstance(sync_data, dict):
        return None
    try:
        return ManagedElementRef.model_validate(sync_data)
    except Exception:
        return None


def get_storage_maps(doc: Doc) -> Dict[str, Map]:
    return {
        DIAGRAM_SPECS_KEY: _get_json_map(doc, DIAGRAM_SPECS_KEY),
        DIAGRAM_MANIFESTS_KEY: _get_json_map(doc, DIAGRAM_MANIFESTS_KEY),
        DIAGRAM_STATE_KEY: _get_json_map(doc, DIAGRAM_STATE_KEY),
        DIAGRAM_INDEX_KEY: _get_json_map(doc, DIAGRAM_INDEX_KEY),
    }


def save_diagram_bundle(doc: Doc, bundle: DiagramBundle) -> None:
    maps = get_storage_maps(doc)

    _store_json(
        maps[DIAGRAM_SPECS_KEY],
        bundle.spec.diagram_id,
        bundle.spec.model_dump(by_alias=True),
    )
    _store_json(
        maps[DIAGRAM_MANIFESTS_KEY],
        bundle.spec.diagram_id,
        bundle.manifest.model_dump(by_alias=True),
    )
    _store_json(
        maps[DIAGRAM_STATE_KEY],
        bundle.spec.diagram_id,
        bundle.state.model_dump(by_alias=True),
    )

    index_map = maps[DIAGRAM_INDEX_KEY]
    stale_keys = []
    for key, raw in index_map.items():
        if not isinstance(raw, str):
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if parsed.get("diagramId") == bundle.spec.diagram_id:
            stale_keys.append(key)

    for key in stale_keys:
        del index_map[key]

    indexed_element_ids = set()
    for element in bundle.preview_elements:
        if not isinstance(element, dict):
            continue
        element_id = element.get("id")
        if not isinstance(element_id, str):
            continue
        ref = _preview_element_ref(element)
        if ref is None:
            continue
        index_map[element_id] = ref.model_dump_json(by_alias=True)
        indexed_element_ids.add(element_id)

    for entry in bundle.manifest.entries:
        for element_id in entry.element_ids:
            if element_id in indexed_element_ids:
                continue
            ref = ManagedElementRef(
                diagramId=bundle.spec.diagram_id,
                semanticId=entry.semantic_id,
                role=entry.role,
                managed=bundle.state.managed_state != "unmanaged",
                renderVersion=bundle.manifest.render_version,
            )
            index_map[element_id] = ref.model_dump_json(by_alias=True)


def load_diagram_bundle(doc: Doc, diagram_id: str) -> Optional[DiagramBundle]:
    maps = get_storage_maps(doc)
    spec_data = _loads_map_value(maps[DIAGRAM_SPECS_KEY], diagram_id)
    manifest_data = _loads_map_value(maps[DIAGRAM_MANIFESTS_KEY], diagram_id)
    state_data = _loads_map_value(maps[DIAGRAM_STATE_KEY], diagram_id)
    if not spec_data or not manifest_data or not state_data:
        return None

    spec = DiagramSpec.model_validate(spec_data)
    manifest = RenderManifest.model_validate(manifest_data)
    state = DiagramState.model_validate(state_data)
    managed_element_count = sum(len(entry.element_ids) for entry in manifest.entries)
    summary = {
        "diagramId": spec.diagram_id,
        "title": spec.title or spec.diagram_type,
        "family": spec.family,
        "componentCount": len(spec.components),
        "connectorCount": len(spec.connectors),
        "managedState": state.managed_state,
        "managedElementCount": managed_element_count,
    }
    return DiagramBundle.model_validate(
        {
            "spec": spec.model_dump(by_alias=True),
            "manifest": manifest.model_dump(by_alias=True),
            "state": state.model_dump(by_alias=True),
            "previewElements": [],
            "previewFiles": {},
            "summary": summary,
        }
    )


def list_diagram_specs(doc: Doc) -> List[DiagramSpec]:
    specs_map = _get_json_map(doc, DIAGRAM_SPECS_KEY)
    specs: List[DiagramSpec] = []
    for _, raw in specs_map.items():
        if not isinstance(raw, str):
            continue
        try:
            specs.append(DiagramSpec.model_validate_json(raw))
        except Exception:
            continue
    return specs


def get_managed_ref(doc: Doc, element_id: str) -> Optional[ManagedElementRef]:
    index_map = _get_json_map(doc, DIAGRAM_INDEX_KEY)
    raw = index_map.get(element_id)
    if not isinstance(raw, str):
        return None
    try:
        return ManagedElementRef.model_validate_json(raw)
    except Exception:
        return None


def upsert_spec(doc: Doc, spec: DiagramSpec) -> None:
    specs_map = _get_json_map(doc, DIAGRAM_SPECS_KEY)
    _store_json(specs_map, spec.diagram_id, spec.model_dump(by_alias=True))


def upsert_state(doc: Doc, state: DiagramState) -> None:
    state_map = _get_json_map(doc, DIAGRAM_STATE_KEY)
    _store_json(state_map, state.diagram_id, state.model_dump(by_alias=True))
