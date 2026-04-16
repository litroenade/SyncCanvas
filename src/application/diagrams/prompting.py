"""LLM/spec generation helpers for managed diagrams."""

import json
import re
import uuid
from copy import deepcopy
from typing import Any, Dict, Optional

from src.application.ai.prompts.manager import prompt_manager
from src.domain.diagrams.engine.vendor_nextgen.fallbacks import (
    MANAGED_DIAGRAM_STYLE,
    build_seed_spec,
)
from src.domain.diagrams.families import canonical_family, route_family, supports_prompt
from src.domain.diagrams.models import DiagramPatch, DiagramSpec
from src.infra.ai.llm import LLMClient
from src.infra.logging import get_logger

logger = get_logger(__name__)


def _diagram_id() -> str:
    return f"diagram_{uuid.uuid4().hex[:10]}"


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^\w]+", "_", value.casefold()).strip("_")
    return cleaned or "item"


def _normalize_ref(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.casefold())


def _preview_text(text: str, limit: int = 240) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}..."


def _string_or_none(value: Any) -> Optional[str]:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _first_string(mapping: Dict[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = _string_or_none(mapping.get(key))
        if value:
            return value
    return None


def _dict_or_empty(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_of_dicts(value: Any) -> list[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _iter_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    resolved: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            resolved.append(item.strip())
            continue
        if isinstance(item, dict):
            candidate = _first_string(
                item,
                "id",
                "componentId",
                "component_id",
                "label",
                "text",
                "title",
            )
            if candidate:
                resolved.append(candidate)
    return resolved


def _register_alias(alias_map: Dict[str, str], candidate: Optional[str], resolved: str) -> None:
    if not candidate:
        return
    key = _normalize_ref(candidate)
    if key:
        alias_map[key] = resolved


def _resolve_alias(alias_map: Dict[str, str], candidate: Optional[str]) -> Optional[str]:
    if not candidate:
        return None
    return alias_map.get(_normalize_ref(candidate), candidate)


def _unique_id(base: str, used: set[str]) -> str:
    candidate = base
    index = 2
    while candidate in used:
        candidate = f"{base}_{index}"
        index += 1
    used.add(candidate)
    return candidate


def _iter_json_candidates(text: str) -> list[str]:
    stripped = text.strip()
    candidates: list[str] = []
    fenced_blocks = re.findall(r"```(?:json)?\s*(.*?)\s*```", stripped, re.DOTALL | re.IGNORECASE)
    candidates.extend(block.strip() for block in fenced_blocks if block.strip())

    start: Optional[int] = None
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(stripped):
        if start is None:
            if char == "{":
                start = index
                depth = 1
                in_string = False
                escaped = False
            continue

        if escaped:
            escaped = False
            continue
        if char == "\\" and in_string:
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidates.append(stripped[start : index + 1].strip())
                start = None

    if stripped:
        candidates.append(stripped)

    deduped: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    for candidate in _iter_json_candidates(text):
        if "{" not in candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _normalize_component_payload(
    payload: Dict[str, Any],
    *,
    index: int,
    used_ids: set[str],
    aliases: Dict[str, str],
) -> Dict[str, Any]:
    normalized = dict(payload)
    label = _first_string(normalized, "label", "title", "name")
    text = _first_string(normalized, "text", "description")
    if label and "label" not in normalized:
        normalized["label"] = label
    if not _string_or_none(normalized.get("text")):
        normalized["text"] = text or label or ""
    if not _string_or_none(normalized.get("label")):
        normalized["label"] = normalized["text"]

    component_id = _first_string(normalized, "id", "semanticId", "semantic_id")
    component_id = component_id or _slug(
        normalized["label"] or normalized["text"] or f"component_{index + 1}"
    )
    normalized["id"] = _unique_id(component_id, used_ids)

    component_type = _first_string(
        normalized,
        "componentType",
        "component_type",
        "type",
        "kind",
    ) or "block"
    normalized["componentType"] = component_type

    for candidate in (
        payload.get("id"),
        payload.get("semanticId"),
        payload.get("semantic_id"),
        payload.get("label"),
        payload.get("title"),
        payload.get("name"),
        payload.get("text"),
        payload.get("description"),
    ):
        _register_alias(aliases, _string_or_none(candidate), normalized["id"])
    return normalized


def _normalize_connector_payload(
    payload: Dict[str, Any],
    *,
    index: int,
    used_ids: set[str],
    component_aliases: Dict[str, str],
) -> Dict[str, Any]:
    normalized = dict(payload)
    source = _resolve_alias(
        component_aliases,
        _first_string(
            normalized,
            "fromComponent",
            "from_component",
            "from",
            "source",
            "sourceComponent",
            "source_component",
        ),
    )
    target = _resolve_alias(
        component_aliases,
        _first_string(
            normalized,
            "toComponent",
            "to_component",
            "to",
            "target",
            "targetComponent",
            "target_component",
        ),
    )
    if source:
        normalized["fromComponent"] = source
    if target:
        normalized["toComponent"] = target
    connector_id = _first_string(normalized, "id")
    connector_id = connector_id or f"edge.{_slug(source or 'source')}.{_slug(target or f'target_{index + 1}')}"
    normalized["id"] = _unique_id(connector_id, used_ids)
    normalized["connectorType"] = _first_string(
        normalized,
        "connectorType",
        "connector_type",
        "type",
        "kind",
    ) or "arrow"
    if not _string_or_none(normalized.get("label")):
        normalized["label"] = _first_string(normalized, "text", "title") or ""
    return normalized


def _normalize_group_payload(
    payload: Dict[str, Any],
    *,
    index: int,
    component_aliases: Dict[str, str],
) -> Dict[str, Any]:
    normalized = dict(payload)
    label = _first_string(normalized, "label", "title", "name") or ""
    normalized["label"] = label
    normalized["id"] = _first_string(normalized, "id") or f"group.{_slug(label or f'group_{index + 1}')}"
    component_ids = _iter_string_list(
        normalized.get("componentIds")
        or normalized.get("component_ids")
        or normalized.get("components")
    )
    normalized["componentIds"] = [
        _resolve_alias(component_aliases, component_id) or component_id
        for component_id in component_ids
    ]
    return normalized


def _normalize_annotation_payload(payload: Dict[str, Any], *, index: int) -> Dict[str, Any]:
    normalized = dict(payload)
    text = _first_string(normalized, "text", "label", "title") or ""
    normalized["text"] = text
    normalized["id"] = _first_string(normalized, "id") or f"note.{_slug(text or f'annotation_{index + 1}')}"
    normalized["annotationType"] = _first_string(
        normalized,
        "annotationType",
        "annotation_type",
        "type",
        "kind",
    ) or "caption"
    return normalized


def _normalize_asset_payload(payload: Dict[str, Any], *, index: int) -> Dict[str, Any]:
    normalized = dict(payload)
    label = _first_string(normalized, "label", "title", "name") or ""
    normalized["label"] = label
    normalized["id"] = _first_string(normalized, "id") or f"asset.{_slug(label or f'asset_{index + 1}')}"
    normalized["assetType"] = _first_string(
        normalized,
        "assetType",
        "asset_type",
        "type",
        "kind",
    ) or "image"
    return normalized


def _build_component_aliases(spec: DiagramSpec) -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for component in spec.components:
        for candidate in (component.id, component.label, component.text):
            _register_alias(aliases, candidate, component.id)
    return aliases


def _build_connector_aliases(spec: DiagramSpec) -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for connector in spec.connectors:
        for candidate in (connector.id, connector.label):
            _register_alias(aliases, candidate, connector.id)
    return aliases


def _build_annotation_aliases(spec: DiagramSpec) -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for annotation in spec.annotations:
        for candidate in (annotation.id, annotation.text):
            _register_alias(aliases, candidate, annotation.id)
    return aliases


def _normalize_component_update(changes: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(changes)
    if "componentType" in normalized and "component_type" not in normalized:
        normalized["component_type"] = normalized.pop("componentType")
    elif "type" in normalized and "component_type" not in normalized:
        normalized["component_type"] = normalized.pop("type")
    return normalized


def _normalize_connector_update(
    changes: Dict[str, Any],
    component_aliases: Dict[str, str],
) -> Dict[str, Any]:
    normalized = dict(changes)
    if "connectorType" in normalized and "connector_type" not in normalized:
        normalized["connector_type"] = normalized.pop("connectorType")
    elif "type" in normalized and "connector_type" not in normalized:
        normalized["connector_type"] = normalized.pop("type")

    for raw_key, target_key in (
        ("fromComponent", "from_component"),
        ("from_component", "from_component"),
        ("from", "from_component"),
        ("source", "from_component"),
        ("toComponent", "to_component"),
        ("to_component", "to_component"),
        ("to", "to_component"),
        ("target", "to_component"),
    ):
        if raw_key not in normalized or target_key in normalized:
            continue
        normalized[target_key] = _resolve_alias(
            component_aliases,
            _string_or_none(normalized.pop(raw_key)),
        )
    return normalized


def _normalize_annotation_update(changes: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(changes)
    if "annotationType" in normalized and "annotation_type" not in normalized:
        normalized["annotation_type"] = normalized.pop("annotationType")
    elif "type" in normalized and "annotation_type" not in normalized:
        normalized["annotation_type"] = normalized.pop("type")
    return normalized


def _normalize_spec_payload(payload: Dict[str, Any], family: str) -> Dict[str, Any]:
    normalized = dict(payload)
    resolved_family = canonical_family(_first_string(normalized, "family") or family)
    raw_diagram_type = _first_string(
        normalized,
        "diagramType",
        "diagram_type",
        "type",
    )
    normalized["diagramId"] = _first_string(
        normalized,
        "diagramId",
        "diagram_id",
        "id",
    ) or _diagram_id()
    normalized["diagramType"] = canonical_family(raw_diagram_type or resolved_family)
    normalized["family"] = resolved_family
    normalized["style"] = _dict_or_empty(normalized.get("style")) or deepcopy(MANAGED_DIAGRAM_STYLE)
    normalized["layout"] = _dict_or_empty(normalized.get("layout"))
    normalized["layoutConstraints"] = _dict_or_empty(
        normalized.get("layoutConstraints")
        or normalized.get("layout_constraints")
        or normalized.get("constraints")
    )
    normalized["overrides"] = _dict_or_empty(normalized.get("overrides"))

    component_aliases: Dict[str, str] = {}
    used_component_ids: set[str] = set()
    normalized["components"] = [
        _normalize_component_payload(
            item,
            index=index,
            used_ids=used_component_ids,
            aliases=component_aliases,
        )
        for index, item in enumerate(_list_of_dicts(normalized.get("components")))
    ]

    used_connector_ids: set[str] = set()
    normalized["connectors"] = [
        _normalize_connector_payload(
            item,
            index=index,
            used_ids=used_connector_ids,
            component_aliases=component_aliases,
        )
        for index, item in enumerate(_list_of_dicts(normalized.get("connectors")))
    ]
    normalized["groups"] = [
        _normalize_group_payload(
            item,
            index=index,
            component_aliases=component_aliases,
        )
        for index, item in enumerate(_list_of_dicts(normalized.get("groups")))
    ]
    normalized["annotations"] = [
        _normalize_annotation_payload(item, index=index)
        for index, item in enumerate(_list_of_dicts(normalized.get("annotations")))
    ]
    normalized["assets"] = [
        _normalize_asset_payload(item, index=index)
        for index, item in enumerate(_list_of_dicts(normalized.get("assets")))
    ]
    return normalized


def _normalize_patch_payload(payload: Dict[str, Any], spec: DiagramSpec) -> Dict[str, Any]:
    normalized = dict(payload)
    normalized["diagramId"] = _first_string(
        normalized,
        "diagramId",
        "diagram_id",
        "id",
    ) or spec.diagram_id

    component_aliases = _build_component_aliases(spec)
    connector_aliases = _build_connector_aliases(spec)
    annotation_aliases = _build_annotation_aliases(spec)
    used_component_ids = {component.id for component in spec.components}
    normalized["componentAdditions"] = [
        _normalize_component_payload(
            item,
            index=index,
            used_ids=used_component_ids,
            aliases=component_aliases,
        )
        for index, item in enumerate(
            _list_of_dicts(
                normalized.get("componentAdditions")
                or normalized.get("component_additions")
            )
        )
    ]

    used_connector_ids = {connector.id for connector in spec.connectors}
    normalized["connectorAdditions"] = [
        _normalize_connector_payload(
            item,
            index=index,
            used_ids=used_connector_ids,
            component_aliases=component_aliases,
        )
        for index, item in enumerate(
            _list_of_dicts(
                normalized.get("connectorAdditions")
                or normalized.get("connector_additions")
            )
        )
    ]
    normalized["annotationAdditions"] = [
        _normalize_annotation_payload(item, index=index)
        for index, item in enumerate(
            _list_of_dicts(
                normalized.get("annotationAdditions")
                or normalized.get("annotation_additions")
            )
        )
    ]

    raw_component_updates = _dict_or_empty(
        normalized.get("componentUpdates")
        or normalized.get("component_updates")
    )
    normalized["componentUpdates"] = {
        _resolve_alias(component_aliases, key) or key: _normalize_component_update(value)
        for key, value in raw_component_updates.items()
        if isinstance(key, str) and isinstance(value, dict)
    }

    raw_connector_updates = _dict_or_empty(
        normalized.get("connectorUpdates")
        or normalized.get("connector_updates")
    )
    normalized["connectorUpdates"] = {
        _resolve_alias(connector_aliases, key) or key: _normalize_connector_update(
            value,
            component_aliases,
        )
        for key, value in raw_connector_updates.items()
        if isinstance(key, str) and isinstance(value, dict)
    }

    raw_annotation_updates = _dict_or_empty(
        normalized.get("annotationUpdates")
        or normalized.get("annotation_updates")
    )
    normalized["annotationUpdates"] = {
        _resolve_alias(annotation_aliases, key) or key: _normalize_annotation_update(value)
        for key, value in raw_annotation_updates.items()
        if isinstance(key, str) and isinstance(value, dict)
    }

    normalized["componentRemovals"] = [
        _resolve_alias(component_aliases, value) or value
        for value in _iter_string_list(
            normalized.get("componentRemovals")
            or normalized.get("component_removals")
        )
    ]
    normalized["connectorRemovals"] = [
        _resolve_alias(connector_aliases, value) or value
        for value in _iter_string_list(
            normalized.get("connectorRemovals")
            or normalized.get("connector_removals")
        )
    ]
    normalized["annotationRemovals"] = [
        _resolve_alias(annotation_aliases, value) or value
        for value in _iter_string_list(
            normalized.get("annotationRemovals")
            or normalized.get("annotation_removals")
        )
    ]
    normalized["stateUpdates"] = _dict_or_empty(
        normalized.get("stateUpdates")
        or normalized.get("state_updates")
    )
    return normalized


class DiagramPromptService:
    """Owns prompt routing, LLM spec generation, and deterministic fallback."""

    def supports_prompt(self, prompt: str, mode: str = "agent") -> bool:
        return supports_prompt(prompt, mode)

    def route_family(self, prompt: str) -> str:
        return route_family(prompt)

    async def spec_from_llm(
        self,
        prompt: str,
        family: str,
        llm_client: Optional[LLMClient],
    ) -> Optional[DiagramSpec]:
        if llm_client is None:
            return None
        try:
            logger.debug(
                "Diagram spec LLM request: family=%s prompt=%s",
                canonical_family(family),
                _preview_text(prompt, 600),
            )
            rendered = prompt_manager.render(
                "managed_diagram_spec.jinja2",
                prompt=prompt,
                family=canonical_family(family),
            )
            logger.debug(
                "Diagram spec prompt rendered: family=%s payload=%s",
                canonical_family(family),
                _preview_text(rendered, 1200),
            )
            response = await llm_client.chat_completion(
                messages=[{"role": "user", "content": rendered}],
                temperature=0.2,
                max_tokens=2400,
            )
            raw_content = response.content or ""
            logger.debug(
                "Diagram spec LLM response: family=%s finish_reason=%s usage=%s payload=%s",
                canonical_family(family),
                response.finish_reason,
                response.usage,
                _preview_text(raw_content, 1200),
            )
            payload = _extract_json_object(raw_content)
            if not payload:
                logger.warning(
                    "Diagram LLM spec response had no valid JSON object for family=%s preview=%s",
                    family,
                    _preview_text(raw_content),
                )
                return None
            normalized = _normalize_spec_payload(payload, family)
            logger.debug(
                "Diagram spec normalized: family=%s diagram_id=%s components=%s connectors=%s annotations=%s",
                canonical_family(family),
                normalized.get("diagramId") or normalized.get("diagram_id"),
                len(normalized.get("components") or []),
                len(normalized.get("connectors") or []),
                len(normalized.get("annotations") or []),
            )
            return DiagramSpec.model_validate(normalized)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Diagram LLM spec generation fell back to deterministic seed: family=%s prompt=%s error=%s",
                canonical_family(family),
                _preview_text(prompt, 300),
                exc,
            )
            return None

    async def patch_from_llm(
        self,
        spec: DiagramSpec,
        prompt: str,
        *,
        target_diagram_id: Optional[str],
        target_semantic_id: Optional[str],
        edit_scope: str,
        llm_client: Optional[LLMClient],
    ) -> Optional[DiagramPatch]:
        if llm_client is None:
            return None
        try:
            logger.debug(
                "Diagram patch LLM request: diagram_id=%s target_diagram_id=%s target_semantic_id=%s edit_scope=%s prompt=%s",
                spec.diagram_id,
                target_diagram_id,
                target_semantic_id,
                edit_scope,
                _preview_text(prompt, 600),
            )
            rendered = prompt_manager.render(
                "diagram_patch.jinja2",
                prompt=prompt,
                spec=spec.model_dump(by_alias=True),
                target_diagram_id=target_diagram_id,
                target_semantic_id=target_semantic_id,
                edit_scope=edit_scope,
            )
            logger.debug(
                "Diagram patch prompt rendered: diagram_id=%s payload=%s",
                spec.diagram_id,
                _preview_text(rendered, 1200),
            )
            response = await llm_client.chat_completion(
                messages=[{"role": "user", "content": rendered}],
                temperature=0.1,
                max_tokens=1800,
            )
            raw_content = response.content or ""
            logger.debug(
                "Diagram patch LLM response: diagram_id=%s finish_reason=%s usage=%s payload=%s",
                spec.diagram_id,
                response.finish_reason,
                response.usage,
                _preview_text(raw_content, 1200),
            )
            payload = _extract_json_object(raw_content)
            if not payload:
                logger.warning(
                    "Diagram LLM patch response had no valid JSON object for diagram=%s preview=%s",
                    spec.diagram_id,
                    _preview_text(raw_content),
                )
                return None
            normalized = _normalize_patch_payload(payload, spec)
            logger.debug(
                "Diagram patch normalized: diagram_id=%s summary=%s updates=%s removals=%s edge_updates=%s edge_removals=%s annotation_updates=%s annotation_removals=%s",
                spec.diagram_id,
                normalized.get("summary"),
                len(normalized.get("componentUpdates") or []),
                len(normalized.get("componentRemovals") or []),
                len(normalized.get("edgeUpdates") or []),
                len(normalized.get("edgeRemovals") or []),
                len(normalized.get("annotationUpdates") or []),
                len(normalized.get("annotationRemovals") or []),
            )
            return DiagramPatch.model_validate(normalized)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Diagram LLM patch generation fell back to heuristic path: diagram_id=%s target_semantic_id=%s edit_scope=%s prompt=%s error=%s",
                spec.diagram_id,
                target_semantic_id,
                edit_scope,
                _preview_text(prompt, 300),
                exc,
            )
            return None

    def build_family_spec(
        self,
        prompt: str,
        family: str,
        *,
        session_id: str,
        theme: str,
    ) -> DiagramSpec:
        _ = session_id, theme
        return build_seed_spec(
            prompt,
            canonical_family(family),
            diagram_id=_diagram_id(),
        )
