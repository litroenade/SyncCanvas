"""Canvas state summarization helpers for prompts."""

from collections import Counter
from typing import Any, Dict, List, Optional

from sqlmodel import Session

from src.infra.logging import get_logger
from src.persistence.db.engine import engine
from src.persistence.db.repositories import rooms as room_repo
from src.realtime.canvas_backend import get_canvas_backend

logger = get_logger(__name__)


class CanvasStateProvider:
    """Build prompt-friendly summaries of the current canvas state."""

    TYPE_NAMES = {
        "rectangle": "rectangle",
        "ellipse": "ellipse",
        "diamond": "diamond",
        "arrow": "arrow",
        "line": "line",
        "text": "text",
        "freedraw": "freedraw",
        "image": "image",
    }

    def get_element_summary(self, elements: List[Dict[str, Any]]) -> str:
        if not elements:
            return "Canvas is empty."

        type_counts: Counter[str] = Counter()
        texts: List[str] = []
        managed_diagrams = set()

        for element in elements:
            if element.get("isDeleted"):
                continue
            element_type = str(element.get("type", "unknown"))
            type_counts[element_type] += 1

            text = element.get("text")
            if element_type == "text" and isinstance(text, str) and text.strip():
                texts.append(text.strip()[:50])

            sync_data = ((element.get("customData") or {}).get("syncCanvas") or {})
            diagram_id = sync_data.get("diagramId")
            if isinstance(diagram_id, str) and diagram_id:
                managed_diagrams.add(diagram_id)

        if not type_counts:
            return "Canvas is empty."

        parts = [
            f"{count} {self.TYPE_NAMES.get(element_type, element_type)}"
            for element_type, count in type_counts.most_common()
        ]
        summary = f"Canvas contains: {', '.join(parts)}."
        if managed_diagrams:
            summary += f" Managed diagrams: {len(managed_diagrams)}."
        if texts:
            preview = ", ".join(texts[:3])
            summary += f" Text preview: {preview}"
            if len(texts) > 3:
                summary += f" (+{len(texts) - 3} more)"
        return summary

    def get_element_details(
        self,
        elements: List[Dict[str, Any]],
        max_items: int = 20,
    ) -> str:
        if not elements:
            return "(no elements)"

        container_texts: Dict[str, str] = {}
        for element in elements:
            if element.get("isDeleted"):
                continue
            if element.get("type") == "text" and element.get("containerId"):
                container_texts[str(element["containerId"])] = str(
                    element.get("text", "")
                )[:40]

        lines: List[str] = []
        visible = [element for element in elements if not element.get("isDeleted")]
        for index, element in enumerate(visible):
            if index >= max_items:
                remaining = len(visible) - max_items
                if remaining > 0:
                    lines.append(f"... and {remaining} more elements")
                break

            element_type = str(element.get("type", "unknown"))
            element_id = str(element.get("id", "?"))
            x = int(element.get("x", 0))
            y = int(element.get("y", 0))

            sync_data = ((element.get("customData") or {}).get("syncCanvas") or {})
            managed_path = sync_data.get("semanticId")
            managed_suffix = (
                f" managed={managed_path}"
                if isinstance(managed_path, str) and managed_path
                else ""
            )

            if element_type == "text" and element.get("containerId"):
                continue
            if element_type in {"rectangle", "ellipse", "diamond"}:
                label = container_texts.get(element_id, "")
                description = (
                    f'- {element_type} [{element_id}] "{label}" at ({x}, {y}){managed_suffix}'
                    if label
                    else f"- {element_type} [{element_id}] at ({x}, {y}){managed_suffix}"
                )
            elif element_type == "arrow":
                start_id = ((element.get("startBinding") or {}).get("elementId")) or "?"
                end_id = ((element.get("endBinding") or {}).get("elementId")) or "?"
                description = (
                    f"- arrow [{element_id}] {start_id} -> {end_id}{managed_suffix}"
                )
            elif element_type == "text":
                description = (
                    f'- text [{element_id}] "{str(element.get("text", ""))[:30]}"{managed_suffix}'
                )
            else:
                description = f"- {element_type} [{element_id}] at ({x}, {y}){managed_suffix}"
            lines.append(description)

        return "\n".join(lines) if lines else "(no visible elements)"

    def get_version_info(self, room_id: str) -> Dict[str, Any]:
        with Session(engine) as session:
            room = room_repo.get_room(session, room_id)
            if not room or room.head_commit_id is None:
                return {"has_history": False, "message": "No version history available."}

            latest_commit = room_repo.get_commit_by_id(session, room.head_commit_id)
            if latest_commit is None:
                return {"has_history": False, "message": "No version history available."}

            return {
                "has_history": True,
                "latest_commit": {
                    "id": latest_commit.id,
                    "hash": latest_commit.hash,
                    "message": latest_commit.message,
                    "author": latest_commit.author_name,
                    "timestamp": latest_commit.timestamp,
                },
            }

    def get_version_summary(self, room_id: str) -> str:
        info = self.get_version_info(room_id)
        if not info.get("has_history"):
            return "No version summary available."
        latest = info.get("latest_commit", {})
        commit_hash = latest.get("hash") or "unknown"
        return (
            f"Latest commit: {latest.get('message', 'unknown')} "
            f"by {latest.get('author', 'unknown')} ({commit_hash})"
        )

    async def get_multimodal_snapshot(self, room_id: str) -> Optional[bytes]:
        try:
            doc, _ = await get_canvas_backend().get_room_doc(room_id)
            return doc.get_update()
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Failed to build multimodal snapshot from live doc for room %s: %s",
                room_id,
                exc,
            )

        with Session(engine) as session:
            room = room_repo.get_room(session, room_id)
            if not room or room.head_commit_id is None:
                return None
            latest_commit = room_repo.get_commit_by_id(session, room.head_commit_id)
            return latest_commit.data if latest_commit else None

    def build_context_prompt(
        self,
        elements: List[Dict[str, Any]],
        room_id: str,
        include_details: bool = True,
    ) -> str:
        parts = [f"[Current Canvas]\n{self.get_element_summary(elements)}"]
        if include_details and elements:
            parts.append(
                f"[Element Details]\n{self.get_element_details(elements, max_items=15)}"
            )
            parts.append(
                "Hint: use element ids for incremental edits and prefer preserving managed diagram structure."
            )
        parts.append(f"[Version History]\n{self.get_version_summary(room_id)}")
        return "\n\n".join(parts)


canvas_state_provider = CanvasStateProvider()
