"""Diagram semantic patch application and heuristic fallback logic."""

import re
from typing import Any, Optional

from src.domain.diagrams.models import (
    DiagramAnnotation,
    DiagramComponent,
    DiagramConnector,
    DiagramPatch,
    DiagramSpec,
)


class DiagramPatchService:
    """Owns semantic patch execution against a diagram spec."""

    _COLOR_PALETTE = {
        "green": {"backgroundColor": "#dcfce7", "strokeColor": "#16a34a"},
        "blue": {"backgroundColor": "#dbeafe", "strokeColor": "#2563eb"},
        "red": {"backgroundColor": "#fee2e2", "strokeColor": "#dc2626"},
        "yellow": {"backgroundColor": "#fef9c3", "strokeColor": "#ca8a04"},
        "purple": {"backgroundColor": "#f3e8ff", "strokeColor": "#9333ea"},
        "orange": {"backgroundColor": "#ffedd5", "strokeColor": "#ea580c"},
        "pink": {"backgroundColor": "#fce7f3", "strokeColor": "#db2777"},
        "teal": {"backgroundColor": "#ccfbf1", "strokeColor": "#0f766e"},
    }

    def apply_patch(self, spec: DiagramSpec, patch: DiagramPatch) -> DiagramSpec:
        updated = DiagramSpec.model_validate(spec.model_dump(by_alias=True))
        updated.version = spec.version + 1
        if "title" in patch.state_updates:
            updated.title = str(patch.state_updates["title"])

        removed_components = set(self._dedupe_ids(patch.component_removals))
        removed_connectors = set(self._dedupe_ids(patch.connector_removals))
        removed_annotations = set(self._dedupe_ids(patch.annotation_removals))

        if removed_components:
            updated.components = [
                component
                for component in updated.components
                if component.id not in removed_components
            ]
            removed_connectors.update(
                connector.id
                for connector in updated.connectors
                if connector.from_component in removed_components
                or connector.to_component in removed_components
            )
        if removed_connectors:
            updated.connectors = [
                connector
                for connector in updated.connectors
                if connector.id not in removed_connectors
            ]
        if removed_annotations:
            updated.annotations = [
                annotation
                for annotation in updated.annotations
                if annotation.id not in removed_annotations
            ]

        component_lookup = {component.id: component for component in updated.components}
        annotation_lookup = {annotation.id: annotation for annotation in updated.annotations}

        for addition in patch.component_additions:
            component = DiagramComponent.model_validate(addition.model_dump(by_alias=True))
            component_lookup[component.id] = component
        for addition in patch.annotation_additions:
            annotation = DiagramAnnotation.model_validate(addition.model_dump(by_alias=True))
            annotation_lookup[annotation.id] = annotation

        for component_id, changes in patch.component_updates.items():
            component = component_lookup.get(component_id)
            if component is not None:
                self._apply_changes(component, changes)
        for annotation_id, changes in patch.annotation_updates.items():
            annotation = annotation_lookup.get(annotation_id)
            if annotation is not None:
                self._apply_changes(annotation, changes)

        updated.components = list(component_lookup.values())
        updated.annotations = list(annotation_lookup.values())

        component_ids = {component.id for component in updated.components}
        connector_lookup: dict[str, DiagramConnector] = {
            connector.id: connector
            for connector in updated.connectors
            if connector.from_component in component_ids
            and connector.to_component in component_ids
        }
        for addition in patch.connector_additions:
            connector = DiagramConnector.model_validate(addition.model_dump(by_alias=True))
            if (
                connector.from_component in component_ids
                and connector.to_component in component_ids
            ):
                connector_lookup[connector.id] = connector
        for connector_id, changes in patch.connector_updates.items():
            connector = connector_lookup.get(connector_id)
            if connector is not None:
                self._apply_changes(connector, changes)

        updated.connectors = [
            connector
            for connector in connector_lookup.values()
            if connector.from_component in component_ids
            and connector.to_component in component_ids
        ]
        return updated

    def resolve_target_semantic_id(
        self,
        spec: DiagramSpec,
        semantic_id: Optional[str],
    ) -> Optional[str]:
        if not semantic_id:
            return None
        known_ids = {
            "diagram.title",
            *(component.id for component in spec.components),
            *(connector.id for connector in spec.connectors),
            *(annotation.id for annotation in spec.annotations),
        }
        if semantic_id in known_ids:
            return semantic_id
        parts = semantic_id.split(".")
        for index in range(len(parts) - 1, 0, -1):
            candidate = ".".join(parts[:index])
            if candidate in known_ids:
                return candidate
        return None

    def heuristic_patch(
        self,
        spec: DiagramSpec,
        prompt: str,
        *,
        target_semantic_id: Optional[str] = None,
    ) -> DiagramPatch:
        prompt = prompt.strip()
        resolved_target = self.resolve_target_semantic_id(spec, target_semantic_id)

        structural = self._match_structural_patch(spec, prompt)
        if structural is not None:
            return structural

        component_updates: dict[str, dict[str, Any]] = {}
        connector_updates: dict[str, dict[str, Any]] = {}
        annotation_updates: dict[str, dict[str, Any]] = {}
        state_updates: dict[str, Any] = {}

        color_style = self.extract_color_style(prompt)
        title_match = re.search(
            r"(?:rename title to|title to|\u628a\u6807\u9898\u6539\u4e3a|\u6807\u9898\u6539\u4e3a)\s*[\"']?([^\"'\n]+)",
            prompt,
            re.IGNORECASE,
        )
        if title_match:
            state_updates["title"] = self._clean_text(title_match.group(1))

        rename_value = self._match_targeted_rename(prompt)
        if resolved_target == "diagram.title":
            if rename_value:
                state_updates["title"] = rename_value
        elif resolved_target:
            component = self.find_component(spec, resolved_target)
            connector = self.find_connector(spec, resolved_target)
            annotation = self.find_annotation(spec, resolved_target)
            if component is not None:
                if color_style:
                    component_updates.setdefault(resolved_target, {}).setdefault(
                        "style", {}
                    ).update(color_style)
                if rename_value:
                    component_updates.setdefault(resolved_target, {}).update(
                        {"label": rename_value, "text": rename_value}
                    )
            elif connector is not None:
                if color_style:
                    connector_updates.setdefault(resolved_target, {}).setdefault(
                        "style", {}
                    ).update(color_style)
                if rename_value:
                    connector_updates.setdefault(resolved_target, {}).update(
                        {"label": rename_value}
                    )
            elif annotation is not None:
                if color_style:
                    annotation_updates.setdefault(resolved_target, {}).setdefault(
                        "style", {}
                    ).update({"textColor": color_style.get("strokeColor")})
                if rename_value:
                    annotation_updates.setdefault(resolved_target, {}).update(
                        {"text": rename_value}
                    )

        if (
            not component_updates
            and not connector_updates
            and not annotation_updates
            and color_style
            and spec.components
        ):
            target_id = resolved_target or spec.components[0].id
            if self.find_component(spec, target_id) is not None:
                component_updates[target_id] = {"style": color_style}

        return DiagramPatch(
            diagramId=spec.diagram_id,
            summary=prompt,
            componentUpdates=component_updates,
            connectorUpdates=connector_updates,
            annotationUpdates=annotation_updates,
            stateUpdates=state_updates,
        )

    def find_component(
        self,
        spec: DiagramSpec,
        semantic_id: str,
    ) -> Optional[DiagramComponent]:
        return next((item for item in spec.components if item.id == semantic_id), None)

    def find_connector(
        self,
        spec: DiagramSpec,
        semantic_id: str,
    ) -> Optional[DiagramConnector]:
        return next((item for item in spec.connectors if item.id == semantic_id), None)

    def find_annotation(
        self,
        spec: DiagramSpec,
        semantic_id: str,
    ) -> Optional[DiagramAnnotation]:
        return next((item for item in spec.annotations if item.id == semantic_id), None)

    def extract_color_style(self, prompt: str) -> Optional[dict[str, Any]]:
        lower = prompt.lower()
        for key, style in self._COLOR_PALETTE.items():
            if key in lower:
                return style
        return None

    def _apply_changes(self, target: Any, changes: dict[str, Any]) -> None:
        for key, value in changes.items():
            if key == "style" and isinstance(value, dict):
                target.style.update(value)
            elif hasattr(target, key):
                setattr(target, key, value)

    def _match_structural_patch(
        self,
        spec: DiagramSpec,
        prompt: str,
    ) -> Optional[DiagramPatch]:
        for matcher in (
            self._match_insert_between,
            self._match_add_right,
            self._match_delete_edge,
            self._match_add_edge,
            self._match_delete_node,
            self._match_rename_node,
        ):
            patch = matcher(spec, prompt)
            if patch is not None:
                return patch
        return None

    def _match_insert_between(
        self,
        spec: DiagramSpec,
        prompt: str,
    ) -> Optional[DiagramPatch]:
        match = self._first_match(
            (
                r"\u5728\s*(.+?)\s*(?:\u548c|\u4e0e)\s*(.+?)\s*\u4e4b\u95f4\u63d2\u5165\s*(.+)$",
                r"insert\s+(.+?)\s+between\s+(.+?)\s+and\s+(.+)$",
            ),
            prompt,
        )
        if match is None:
            return None
        if match.re.pattern.startswith("insert"):
            label, left_name, right_name = match.groups()
        else:
            left_name, right_name, label = match.groups()

        left = self._find_component_by_name(spec, left_name)
        right = self._find_component_by_name(spec, right_name)
        label = self._clean_text(label)
        if left is None or right is None or not label:
            return None

        new_component = self._build_component_like(
            spec,
            label,
            x=(left.x + left.width / 2 + right.x + right.width / 2) / 2 - 80,
            y=(left.y + left.height / 2 + right.y + right.height / 2) / 2 - 36,
            fallback=left,
            data={
                "relayoutNeighbors": [left.id, right.id],
                "placementHint": {"kind": "between", "left": left.id, "right": right.id},
            },
        )
        existing = self._find_connector_by_endpoints(spec, left.id, right.id)
        return DiagramPatch(
            diagramId=spec.diagram_id,
            summary=prompt,
            componentAdditions=[new_component],
            connectorAdditions=[
                self._build_connector(spec, left.id, new_component.id),
                self._build_connector(spec, new_component.id, right.id),
            ],
            connectorRemovals=[existing.id] if existing else [],
        )

    def _match_add_right(
        self,
        spec: DiagramSpec,
        prompt: str,
    ) -> Optional[DiagramPatch]:
        match = self._first_match(
            (
                r"\u5728\s*(.+?)\s*\u53f3\u4fa7\u65b0\u589e\s*(.+)$",
                r"add\s+(.+?)\s+to the right of\s+(.+)$",
            ),
            prompt,
        )
        if match is None:
            return None
        if match.re.pattern.startswith("add"):
            label, anchor_name = match.groups()
        else:
            anchor_name, label = match.groups()

        anchor = self._find_component_by_name(spec, anchor_name)
        label = self._clean_text(label)
        if anchor is None or not label:
            return None

        return DiagramPatch(
            diagramId=spec.diagram_id,
            summary=prompt,
            componentAdditions=[
                self._build_component_like(
                    spec,
                    label,
                    x=anchor.x + anchor.width + 160,
                    y=anchor.y + max((anchor.height - 72) / 2, 0),
                    fallback=anchor,
                    data={
                        "relayoutNeighbors": [anchor.id],
                        "placementHint": {"kind": "right_of", "anchor": anchor.id},
                    },
                )
            ],
        )

    def _match_delete_edge(
        self,
        spec: DiagramSpec,
        prompt: str,
    ) -> Optional[DiagramPatch]:
        match = self._first_match(
            (
                r"\u5220\u9664\s*(.+?)\s*(?:\u5230|->|\u2192)\s*(.+?)\s*\u7684?(?:\u8fde\u7ebf|\u8fde\u63a5)$",
                r"delete\s+(?:the\s+)?edge\s+from\s+(.+?)\s+to\s+(.+)$",
            ),
            prompt,
        )
        if match is None:
            return None

        source = self._find_component_by_name(spec, match.group(1))
        target = self._find_component_by_name(spec, match.group(2))
        if source is None or target is None:
            return None

        connector = self._find_connector_by_endpoints(spec, source.id, target.id)
        if connector is None:
            return None

        return DiagramPatch(
            diagramId=spec.diagram_id,
            summary=prompt,
            connectorRemovals=[connector.id],
        )

    def _match_add_edge(
        self,
        spec: DiagramSpec,
        prompt: str,
    ) -> Optional[DiagramPatch]:
        match = self._first_match(
            (
                r"(?:\u65b0\u589e|\u6dfb\u52a0|\u589e\u52a0)\s*(?:\u4ece)?\s*(.+?)\s*(?:\u5230|->|\u2192)\s*(.+?)\s*(?:\u7684)?(?:\u8fde\u7ebf|\u8fde\u63a5)?$",
                r"connect\s+(.+?)\s+to\s+(.+)$",
            ),
            prompt,
        )
        if match is None:
            return None

        source = self._find_component_by_name(spec, match.group(1))
        target = self._find_component_by_name(spec, match.group(2))
        if source is None or target is None:
            return None
        if self._find_connector_by_endpoints(spec, source.id, target.id) is not None:
            return None

        return DiagramPatch(
            diagramId=spec.diagram_id,
            summary=prompt,
            connectorAdditions=[self._build_connector(spec, source.id, target.id)],
        )

    def _match_delete_node(
        self,
        spec: DiagramSpec,
        prompt: str,
    ) -> Optional[DiagramPatch]:
        match = self._first_match(
            (
                r"(?:\u5220\u9664\u8282\u70b9|\u5220\u9664\u670d\u52a1|\u5220\u9664\u6a21\u5757|delete node|remove node)\s+(.+)$",
            ),
            prompt,
        )
        if match is None:
            return None

        component = self._find_component_by_name(spec, match.group(1))
        if component is None:
            return None

        return DiagramPatch(
            diagramId=spec.diagram_id,
            summary=prompt,
            componentRemovals=[component.id],
        )

    def _match_rename_node(
        self,
        spec: DiagramSpec,
        prompt: str,
    ) -> Optional[DiagramPatch]:
        match = self._first_match(
            (
                r"(?:\u628a)?\s*(.+?)\s*\u6539\u540d\u4e3a\s*(.+)$",
                r"rename\s+(.+?)\s+to\s+(.+)$",
            ),
            prompt,
        )
        if match is None:
            return None

        component = self._find_component_by_name(spec, match.group(1))
        new_name = self._clean_text(match.group(2))
        if component is None or not new_name:
            return None

        return DiagramPatch(
            diagramId=spec.diagram_id,
            summary=prompt,
            componentUpdates={
                component.id: {
                    "label": new_name,
                    "text": new_name,
                }
            },
        )

    def _match_targeted_rename(self, prompt: str) -> Optional[str]:
        match = self._first_match(
            (
                r"(?:\u6539\u540d\u4e3a|\u547d\u540d\u4e3a)\s*(.+)$",
                r"(?:rename|label|text|change text to|set label to)\s*[\"']?([^\"'\n]+)",
            ),
            prompt,
        )
        if match is None:
            return None
        value = self._clean_text(match.group(1))
        return value or None

    def _find_component_by_name(
        self,
        spec: DiagramSpec,
        name: str,
    ) -> Optional[DiagramComponent]:
        query = self._normalize_name(name)
        if not query:
            return None

        fuzzy_matches: list[tuple[int, DiagramComponent]] = []
        for component in spec.components:
            candidates = [
                self._normalize_name(component.id),
                self._normalize_name(component.label),
                self._normalize_name(component.text),
            ]
            if any(query == candidate for candidate in candidates if candidate):
                return component

            overlapping = [
                candidate
                for candidate in candidates
                if candidate and (query in candidate or candidate in query)
            ]
            if overlapping:
                score = min(abs(len(candidate) - len(query)) for candidate in overlapping)
                fuzzy_matches.append((score, component))

        if not fuzzy_matches:
            return None
        fuzzy_matches.sort(key=lambda item: item[0])
        if len(fuzzy_matches) == 1 or fuzzy_matches[0][0] < fuzzy_matches[1][0]:
            return fuzzy_matches[0][1]
        return None

    def _find_connector_by_endpoints(
        self,
        spec: DiagramSpec,
        source_id: str,
        target_id: str,
    ) -> Optional[DiagramConnector]:
        return next(
            (
                connector
                for connector in spec.connectors
                if connector.from_component == source_id
                and connector.to_component == target_id
            ),
            None,
        )

    def _build_component_like(
        self,
        spec: DiagramSpec,
        label: str,
        *,
        x: float,
        y: float,
        fallback: Optional[DiagramComponent] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> DiagramComponent:
        return DiagramComponent(
            id=self._unique_component_id(spec, label),
            componentType=fallback.component_type if fallback is not None else "block",
            label=label,
            text=label,
            shape=fallback.shape if fallback is not None else "rectangle",
            x=float(x),
            y=float(y),
            width=float(fallback.width if fallback is not None else 160.0),
            height=float(fallback.height if fallback is not None else 72.0),
            style=dict(fallback.style) if fallback is not None else {},
            data=dict(data or {}),
        )

    def _build_connector(
        self,
        spec: DiagramSpec,
        source_id: str,
        target_id: str,
    ) -> DiagramConnector:
        return DiagramConnector(
            id=self._unique_connector_id(spec, source_id, target_id),
            connectorType="arrow",
            fromComponent=source_id,
            toComponent=target_id,
            label="",
            style={},
            data={},
        )

    def _unique_component_id(self, spec: DiagramSpec, label: str) -> str:
        base = f"node.{self._slug(label)}"
        existing = {component.id for component in spec.components}
        if base not in existing:
            return base
        index = 2
        while f"{base}_{index}" in existing:
            index += 1
        return f"{base}_{index}"

    def _unique_connector_id(
        self,
        spec: DiagramSpec,
        source_id: str,
        target_id: str,
    ) -> str:
        base = f"edge.{self._slug(source_id)}.{self._slug(target_id)}"
        existing = {connector.id for connector in spec.connectors}
        if base not in existing:
            return base
        index = 2
        while f"{base}_{index}" in existing:
            index += 1
        return f"{base}_{index}"

    def _dedupe_ids(self, values: list[str]) -> list[str]:
        deduped: list[str] = []
        for value in values:
            if isinstance(value, str) and value and value not in deduped:
                deduped.append(value)
        return deduped

    def _slug(self, value: str) -> str:
        cleaned = re.sub(r"[^\w]+", "_", value.lower()).strip("_")
        return cleaned or "item"

    def _normalize_name(self, value: str) -> str:
        return re.sub(r"[\W_]+", "", self._clean_text(value).lower())

    def _clean_text(self, value: str) -> str:
        return value.strip(
            " \t\r\n\"'`.,;:!?()\uFF0C\u3002\uFF1B\uFF1A\uFF01\uFF1F"
        )

    def _first_match(
        self,
        patterns: tuple[str, ...],
        prompt: str,
    ) -> Optional[re.Match[str]]:
        for pattern in patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match is not None:
                return match
        return None
