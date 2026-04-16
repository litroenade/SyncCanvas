"""Spec-first managed diagram service orchestration."""

from dataclasses import dataclass
from typing import Literal, Optional

from src.application.diagrams.patching import DiagramPatchService
from src.application.diagrams.prompting import DiagramPromptService
from src.application.diagrams.relayout import (
    compute_relayout_scope,
    compute_reroute_scope,
)
from src.application.diagrams.state import DiagramBundleStateService
from src.application.diagrams.store import DiagramBundleStore
from src.domain.diagrams.models import (
    DiagramBundle,
    DiagramGenerationMode,
    DiagramPatch,
    DiagramSpec,
)
from src.domain.diagrams.rendering.render import render_spec
from src.infra.ai.llm import LLMClient
from src.infra.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class DiagramPromptRunResult:
    bundle: DiagramBundle
    generation_mode: DiagramGenerationMode


class DiagramService:
    """Application orchestrator for the managed diagram chain."""

    def __init__(self) -> None:
        self._state = DiagramBundleStateService()
        self._patching = DiagramPatchService()
        self._prompting = DiagramPromptService()
        self._store = DiagramBundleStore(self._state)

    def refresh_bundle_metadata(self, bundle: DiagramBundle) -> DiagramBundle:
        return self._state.refresh_bundle_metadata(bundle)

    def configure_bundle_state(
        self,
        bundle: DiagramBundle,
        *,
        previous_state=None,
        managed_state: Optional[Literal['managed', 'semi_managed', 'unmanaged']] = None,
        managed_scope: Optional[list[str]] = None,
        unmanaged_paths: Optional[list[str]] = None,
        warnings: Optional[list[str]] = None,
        last_edit_source: str,
        last_patch_summary: str,
    ) -> DiagramBundle:
        return self._state.configure_bundle_state(
            bundle,
            previous_state=previous_state,
            managed_state=managed_state,
            managed_scope=managed_scope,
            unmanaged_paths=unmanaged_paths,
            warnings=warnings,
            last_edit_source=last_edit_source,
            last_patch_summary=last_patch_summary,
        )

    def preserve_bundle_state(
        self,
        bundle: DiagramBundle,
        previous_state,
        *,
        managed_scope: Optional[list[str]] = None,
        last_edit_source: str,
        last_patch_summary: str,
    ) -> DiagramBundle:
        return self._state.preserve_bundle_state(
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
        return self._state.reset_bundle_to_managed(
            bundle,
            managed_scope=managed_scope,
            last_edit_source=last_edit_source,
            last_patch_summary=last_patch_summary,
        )

    def supports_prompt(self, prompt: str, mode: str = "agent") -> bool:
        return self._prompting.supports_prompt(prompt, mode)

    def route_family(self, prompt: str) -> str:
        return self._prompting.route_family(prompt)

    def apply_patch(self, spec: DiagramSpec, patch: DiagramPatch) -> DiagramSpec:
        return self._patching.apply_patch(spec, patch)

    def resolve_target_semantic_id(
        self, spec: DiagramSpec, semantic_id: Optional[str]
    ) -> Optional[str]:
        return self._patching.resolve_target_semantic_id(spec, semantic_id)

    async def create_from_prompt(
        self,
        prompt: str,
        *,
        session_id: str,
        theme: str,
        llm_client: Optional[LLMClient] = None,
        persist: bool = True,
    ) -> DiagramBundle:
        return (
            await self.create_from_prompt_result(
                prompt,
                session_id=session_id,
                theme=theme,
                llm_client=llm_client,
                persist=persist,
            )
        ).bundle

    async def create_from_prompt_result(
        self,
        prompt: str,
        *,
        session_id: str,
        theme: str,
        llm_client: Optional[LLMClient] = None,
        llm_timeout_seconds: Optional[float] = None,
        persist: bool = True,
    ) -> DiagramPromptRunResult:
        family = self.route_family(prompt)
        logger.debug(
            "Diagram create request: session_id=%s family=%s persist=%s prompt=%s",
            session_id,
            family,
            persist,
            prompt,
        )
        spec = await self._prompting.spec_from_llm(
            prompt,
            family,
            llm_client,
            timeout_seconds=llm_timeout_seconds,
        )
        generation_mode: DiagramGenerationMode = "llm"
        if spec is None:
            generation_mode = "deterministic_seed"
            logger.debug(
                "Diagram create falling back to deterministic seed: session_id=%s family=%s",
                session_id,
                family,
            )
            spec = self._prompting.build_family_spec(
                prompt,
                family,
                session_id=session_id,
                theme=theme,
            )
        bundle = render_spec(spec)
        bundle = self.configure_bundle_state(
            bundle,
            last_edit_source="system",
            last_patch_summary=f"Created {family} diagram from prompt",
        )
        if persist:
            doc, elements_array = await self._store.get_room_doc(session_id)
            self._store.persist_bundle(doc, elements_array, bundle)
        logger.debug(
            "Diagram create complete: session_id=%s family=%s generation_mode=%s diagram_id=%s components=%s connectors=%s",
            session_id,
            family,
            generation_mode,
            bundle.spec.diagram_id,
            bundle.summary.component_count,
            bundle.summary.connector_count,
        )
        return DiagramPromptRunResult(
            bundle=bundle,
            generation_mode=generation_mode,
        )

    async def update_from_prompt(
        self,
        room_id: str,
        diagram_id: str,
        prompt: str,
        *,
        target_semantic_id: Optional[str] = None,
        edit_scope: str = "diagram",
        llm_client: Optional[LLMClient] = None,
        persist: bool = True,
    ) -> DiagramBundle:
        return (
            await self.update_from_prompt_result(
                room_id,
                diagram_id,
                prompt,
                target_semantic_id=target_semantic_id,
                edit_scope=edit_scope,
                llm_client=llm_client,
                persist=persist,
            )
        ).bundle

    async def update_from_prompt_result(
        self,
        room_id: str,
        diagram_id: str,
        prompt: str,
        *,
        target_semantic_id: Optional[str] = None,
        edit_scope: str = "diagram",
        llm_client: Optional[LLMClient] = None,
        llm_timeout_seconds: Optional[float] = None,
        persist: bool = True,
    ) -> DiagramPromptRunResult:
        doc, elements_array, existing = await self._store.load_room_bundle_for_update(
            room_id,
            diagram_id,
        )
        if not existing:
            raise ValueError(f"Diagram {diagram_id} not found")

        resolved_target = self.resolve_target_semantic_id(
            existing.spec,
            target_semantic_id,
        )
        logger.debug(
            "Diagram update request: room_id=%s diagram_id=%s family=%s target_semantic_id=%s resolved_target=%s edit_scope=%s persist=%s prompt=%s",
            room_id,
            diagram_id,
            existing.summary.family,
            target_semantic_id,
            resolved_target,
            edit_scope,
            persist,
            prompt,
        )
        if target_semantic_id and resolved_target != target_semantic_id:
            logger.info(
                "Diagram %s target semantic resolved from %s to %s",
                diagram_id,
                target_semantic_id,
                resolved_target or "diagram_scope",
            )
        patch = await self._prompting.patch_from_llm(
            existing.spec,
            prompt,
            target_diagram_id=diagram_id,
            target_semantic_id=resolved_target,
            edit_scope=edit_scope,
            llm_client=llm_client,
            timeout_seconds=llm_timeout_seconds,
        )
        generation_mode: DiagramGenerationMode = "llm"
        if patch is None:
            generation_mode = "heuristic_patch"
            logger.debug(
                "Diagram update falling back to heuristic patch: room_id=%s diagram_id=%s resolved_target=%s",
                room_id,
                diagram_id,
                resolved_target,
            )
            patch = self._patching.heuristic_patch(
                existing.spec,
                prompt,
                target_semantic_id=resolved_target,
            )

        updated = self.apply_patch(existing.spec, patch)
        relayout_scope = compute_relayout_scope(existing.spec, updated, patch)
        reroute_scope = compute_reroute_scope(
            existing.spec,
            updated,
            patch,
            relayout_scope,
        )
        logger.debug(
            "Diagram update scopes: room_id=%s diagram_id=%s relayout_scope=%s reroute_scope=%s",
            room_id,
            diagram_id,
            relayout_scope,
            reroute_scope,
        )
        bundle = render_spec(
            updated,
            relayout_scope=relayout_scope,
            reroute_scope=reroute_scope,
        )
        requested_scope = (
            [resolved_target]
            if resolved_target and edit_scope == "semantic"
            else list(existing.state.managed_scope)
        )
        next_scope = self._state.normalize_managed_scope(updated, requested_scope)
        if edit_scope == "semantic" and target_semantic_id and (
            not resolved_target or next_scope != [resolved_target]
        ):
            logger.info(
                "Diagram %s semantic edit fell back to diagram scope after rerender",
                diagram_id,
            )
        self.preserve_bundle_state(
            bundle,
            existing.state,
            managed_scope=next_scope,
            last_edit_source="ai",
            last_patch_summary=patch.summary or prompt,
        )
        if persist:
            self._store.persist_bundle(doc, elements_array, bundle)
        logger.debug(
            "Diagram update complete: room_id=%s diagram_id=%s generation_mode=%s components=%s connectors=%s managed_scope=%s",
            room_id,
            diagram_id,
            generation_mode,
            bundle.summary.component_count,
            bundle.summary.connector_count,
            bundle.state.managed_scope,
        )
        return DiagramPromptRunResult(
            bundle=bundle,
            generation_mode=generation_mode,
        )

    async def list_room_diagrams(self, room_id: str) -> list[DiagramSpec]:
        return await self._store.list_room_diagrams(room_id)

    async def get_room_bundle(
        self, room_id: str, diagram_id: str
    ) -> Optional[DiagramBundle]:
        return await self._store.get_room_bundle(room_id, diagram_id)

    async def apply_patch_to_bundle(
        self,
        room_id: str,
        diagram_id: str,
        patch: DiagramPatch,
        *,
        last_edit_source: str = "api",
        persist: bool = True,
    ) -> DiagramBundle:
        doc, elements_array, existing = await self._store.load_room_bundle_for_update(
            room_id,
            diagram_id,
        )
        if not existing:
            raise ValueError(f"Diagram {diagram_id} not found")

        updated_spec = self.apply_patch(existing.spec, patch)
        relayout_scope = compute_relayout_scope(existing.spec, updated_spec, patch)
        reroute_scope = compute_reroute_scope(
            existing.spec,
            updated_spec,
            patch,
            relayout_scope,
        )
        rebuilt = render_spec(
            updated_spec,
            relayout_scope=relayout_scope,
            reroute_scope=reroute_scope,
        )
        self.preserve_bundle_state(
            rebuilt,
            existing.state,
            managed_scope=list(existing.state.managed_scope),
            last_edit_source=last_edit_source,
            last_patch_summary=patch.summary or "Applied patch",
        )
        if persist:
            self._store.persist_bundle(doc, elements_array, rebuilt)
        return rebuilt

    async def rebuild_bundle(self, room_id: str, diagram_id: str) -> DiagramBundle:
        doc, elements_array, bundle = await self._store.load_room_bundle_for_update(
            room_id,
            diagram_id,
        )
        if not bundle:
            raise ValueError(f"Diagram {diagram_id} not found")
        rebuilt = render_spec(bundle.spec)
        self.reset_bundle_to_managed(
            rebuilt,
            managed_scope=list(bundle.state.managed_scope),
        )
        self._store.persist_bundle(doc, elements_array, rebuilt)
        return rebuilt


DiagramApplicationService = DiagramService
diagram_service = DiagramApplicationService()


async def create_diagram_from_prompt(
    prompt: str,
    *,
    session_id: str,
    theme: str,
    llm_client: Optional[LLMClient] = None,
    persist: bool = True,
) -> DiagramBundle:
    return await diagram_service.create_from_prompt(
        prompt,
        session_id=session_id,
        theme=theme,
        llm_client=llm_client,
        persist=persist,
    )


async def update_diagram_from_prompt(
    room_id: str,
    diagram_id: str,
    prompt: str,
    *,
    target_semantic_id: Optional[str] = None,
    edit_scope: str = "diagram",
    llm_client: Optional[LLMClient] = None,
    persist: bool = True,
) -> DiagramBundle:
    return await diagram_service.update_from_prompt(
        room_id,
        diagram_id,
        prompt,
        target_semantic_id=target_semantic_id,
        edit_scope=edit_scope,
        llm_client=llm_client,
        persist=persist,
    )


async def apply_diagram_patch(
    room_id: str,
    diagram_id: str,
    patch: DiagramPatch,
    *,
    last_edit_source: str = "api",
    persist: bool = True,
) -> DiagramBundle:
    return await diagram_service.apply_patch_to_bundle(
        room_id,
        diagram_id,
        patch,
        last_edit_source=last_edit_source,
        persist=persist,
    )


async def rebuild_diagram_bundle(room_id: str, diagram_id: str) -> DiagramBundle:
    return await diagram_service.rebuild_bundle(room_id, diagram_id)


async def get_room_diagram_bundle(
    room_id: str, diagram_id: str
) -> Optional[DiagramBundle]:
    return await diagram_service.get_room_bundle(room_id, diagram_id)


async def list_managed_diagrams(room_id: str) -> list[DiagramSpec]:
    return await diagram_service.list_room_diagrams(room_id)


def resolve_target_semantic_id(
    spec: DiagramSpec,
    semantic_id: Optional[str],
) -> Optional[str]:
    return diagram_service.resolve_target_semantic_id(spec, semantic_id)
