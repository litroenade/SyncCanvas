"""Managed diagram bundle state normalization and metadata refresh."""

from typing import Literal, Optional

from src.domain.diagrams.models import DiagramBundle, DiagramSpec, DiagramState
from src.infra.logging import get_logger

logger = get_logger(__name__)


class DiagramBundleStateService:
    """Owns managed/unmanaged scope normalization and summary refresh."""

    def default_managed_scope(self, spec: DiagramSpec) -> list[str]:
        return [component.id for component in spec.components]

    def known_semantic_ids(self, spec: DiagramSpec) -> set[str]:
        return {
            "diagram.title",
            *(component.id for component in spec.components),
            *(annotation.id for annotation in spec.annotations),
            *(connector.id for connector in spec.connectors),
        }

    def dedupe_strings(self, values: Optional[list[str]]) -> list[str]:
        deduped: list[str] = []
        for value in values or []:
            if not isinstance(value, str) or not value:
                continue
            if value not in deduped:
                deduped.append(value)
        return deduped

    def normalize_managed_scope(
        self, spec: DiagramSpec, managed_scope: Optional[list[str]]
    ) -> list[str]:
        known_ids = self.known_semantic_ids(spec)
        normalized = [
            semantic_id
            for semantic_id in self.dedupe_strings(managed_scope)
            if semantic_id in known_ids
        ]
        return normalized or self.default_managed_scope(spec)

    def refresh_bundle_metadata(self, bundle: DiagramBundle) -> DiagramBundle:
        bundle.state.managed_scope = self.normalize_managed_scope(
            bundle.spec, bundle.state.managed_scope
        )
        bundle.state.unmanaged_paths = self.dedupe_strings(bundle.state.unmanaged_paths)
        bundle.state.warnings = self.dedupe_strings(bundle.state.warnings)
        bundle.summary.title = bundle.spec.title or bundle.spec.diagram_type
        bundle.summary.family = bundle.spec.family
        bundle.summary.component_count = len(bundle.spec.components)
        bundle.summary.connector_count = len(bundle.spec.connectors)
        bundle.summary.managed_state = bundle.state.managed_state
        bundle.summary.managed_element_count = sum(
            len(entry.element_ids) for entry in bundle.manifest.entries
        )
        return bundle

    def configure_bundle_state(
        self,
        bundle: DiagramBundle,
        *,
        previous_state: Optional[DiagramState] = None,
        managed_state: Optional[Literal["managed", "semi_managed", "unmanaged"]] = None,
        managed_scope: Optional[list[str]] = None,
        unmanaged_paths: Optional[list[str]] = None,
        warnings: Optional[list[str]] = None,
        last_edit_source: str,
        last_patch_summary: str,
    ) -> DiagramBundle:
        if previous_state is not None:
            bundle.state.managed_state = previous_state.managed_state
            if managed_scope is None:
                managed_scope = list(previous_state.managed_scope)
            if unmanaged_paths is None:
                unmanaged_paths = list(previous_state.unmanaged_paths)
            if warnings is None:
                warnings = list(previous_state.warnings)

        if managed_state is not None:
            bundle.state.managed_state = managed_state

        bundle.state.managed_scope = list(managed_scope or [])
        bundle.state.unmanaged_paths = list(unmanaged_paths or [])
        bundle.state.warnings = list(warnings or [])
        bundle.state.last_edit_source = last_edit_source
        bundle.state.last_patch_summary = last_patch_summary
        return self.refresh_bundle_metadata(bundle)

    def preserve_bundle_state(
        self,
        bundle: DiagramBundle,
        previous_state: DiagramState,
        *,
        managed_scope: Optional[list[str]] = None,
        last_edit_source: str,
        last_patch_summary: str,
    ) -> DiagramBundle:
        return self.configure_bundle_state(
            bundle,
            previous_state=previous_state,
            managed_scope=managed_scope,
            last_edit_source=last_edit_source,
            last_patch_summary=last_patch_summary,
        )

    def reset_bundle_to_managed(
        self,
        bundle: DiagramBundle,
        *,
        managed_scope: Optional[list[str]] = None,
        last_edit_source: str = "system",
        last_patch_summary: str = "Rebuilt from spec",
    ) -> DiagramBundle:
        rebuilt = self.configure_bundle_state(
            bundle,
            managed_state="managed",
            managed_scope=managed_scope,
            unmanaged_paths=[],
            warnings=[],
            last_edit_source=last_edit_source,
            last_patch_summary=last_patch_summary,
        )
        logger.info(
            "Diagram %s rebuilt to managed state scope=%s",
            rebuilt.spec.diagram_id,
            len(rebuilt.state.managed_scope),
        )
        return rebuilt
