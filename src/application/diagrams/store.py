"""Yjs persistence boundary for managed diagram bundles."""

from typing import Any, Optional

from pycrdt import Array, Map

from src.application.diagrams.state import DiagramBundleStateService
from src.domain.diagrams.models import DiagramBundle, DiagramSpec
from src.infra.logging import get_logger
from src.lib.excalidraw.helpers import append_element_as_ymap, update_element_in_array
from src.persistence.yjs.diagrams import (
    list_diagram_specs,
    load_diagram_bundle,
    save_diagram_bundle,
)
from src.realtime.canvas_backend import get_canvas_backend

logger = get_logger(__name__)


class DiagramBundleStore:
    """Handles Yjs room loading and managed diagram persistence."""

    def __init__(self, state_service: DiagramBundleStateService) -> None:
        self._state_service = state_service

    async def get_room_doc(self, room_id: str) -> tuple[Any, Array]:
        backend = get_canvas_backend()
        return await backend.get_room_doc(room_id)

    async def load_room_bundle_for_update(
        self, room_id: str, diagram_id: str
    ) -> tuple[Any, Array, Optional[DiagramBundle]]:
        doc, elements_array = await self.get_room_doc(room_id)
        return doc, elements_array, load_diagram_bundle(doc, diagram_id)

    async def list_room_diagrams(self, room_id: str) -> list[DiagramSpec]:
        doc, _ = await self.get_room_doc(room_id)
        return list_diagram_specs(doc)

    async def get_room_bundle(
        self, room_id: str, diagram_id: str
    ) -> Optional[DiagramBundle]:
        doc, _ = await self.get_room_doc(room_id)
        return load_diagram_bundle(doc, diagram_id)

    def persist_bundle(self, doc: Any, elements_array: Array, bundle: DiagramBundle) -> None:
        self._state_service.refresh_bundle_metadata(bundle)
        stale_ids: set[str] = set()
        with doc.transaction(origin=f"diagram/{bundle.spec.diagram_id}/persist"):
            save_diagram_bundle(doc, bundle)
            rendered_ids = {element["id"] for element in bundle.preview_elements}
            existing_ids = set()
            for item in elements_array:
                data = (
                    dict(item)
                    if isinstance(item, Map)
                    else item
                    if isinstance(item, dict)
                    else None
                )
                if not isinstance(data, dict):
                    continue
                sync_data = (data.get("customData") or {}).get("syncCanvas")
                if (
                    isinstance(sync_data, dict)
                    and sync_data.get("diagramId") == bundle.spec.diagram_id
                ):
                    element_id = data.get("id")
                    if isinstance(element_id, str):
                        existing_ids.add(element_id)

            for element in bundle.preview_elements:
                if element["id"] in existing_ids:
                    update_element_in_array(elements_array, element["id"], element)
                else:
                    append_element_as_ymap(elements_array, element)

            stale_ids = existing_ids - rendered_ids
            for stale_id in stale_ids:
                update_element_in_array(elements_array, stale_id, {"isDeleted": True})
        logger.info(
            "Persisted diagram %s state=%s scope=%s warnings=%s rendered=%s stale=%s",
            bundle.spec.diagram_id,
            bundle.state.managed_state,
            len(bundle.state.managed_scope),
            len(bundle.state.warnings),
            len(bundle.preview_elements),
            len(stale_ids),
        )
