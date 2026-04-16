"""
Library service support.
"""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import aiohttp
import numpy as np
from openai import AsyncOpenAI
from sqlmodel import Session, asc, select

from src.infra.config import config
from src.infra.logging import get_logger
from src.persistence.db.engine import engine
from src.persistence.db.models.library_records import Library, LibraryItem

if TYPE_CHECKING:
    import faiss

logger = get_logger(__name__)

LIBRARIES_INDEX_URL = "https://libraries.excalidraw.com/libraries.json"
LIBRARY_BASE_URL = "https://libraries.excalidraw.com"
HTTP_TIMEOUT_SECONDS = 30
EMBEDDING_DIMENSION = 1536
UPLOADED_ASSETS_LIBRARY_ID = "uploaded-assets"
UPLOADED_ASSETS_LIBRARY_NAME = "Uploaded Assets"
UPLOADED_ASSETS_LIBRARY_DESCRIPTION = (
    "Locally uploaded image assets indexed from data/images for repeated model reuse."
)
UPLOADED_ASSETS_LIBRARY_SOURCE = "data/images"

LIBRARY_DIR = Path(__file__).parent.parent.parent.parent / "data" / "lib"
LIBRARY_DIR.mkdir(parents=True, exist_ok=True)

_faiss_module = None


def _get_faiss():
    global _faiss_module
    if _faiss_module is None:
        import faiss

        _faiss_module = faiss
    return _faiss_module


class LibraryService:
    _instance: Optional["LibraryService"] = None

    def __init__(self) -> None:
        self._client: Optional[AsyncOpenAI] = None
        self._model_name = ""
        self._index: Optional["faiss.IndexFlatIP"] = None
        self._item_id_map: List[int] = []
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "LibraryService":
        if cls._instance is None:
            cls._instance = LibraryService()
        return cls._instance

    def _init_embedding_client(self) -> bool:
        if self._client is not None:
            return True

        ai_config = config.ai
        current_group = ai_config.model_groups.get(ai_config.current_model_group)
        if not current_group or not current_group.embedding_model:
            return False

        embedding_config = current_group.embedding_model
        self._client = AsyncOpenAI(
            base_url=embedding_config.base_url,
            api_key=embedding_config.api_key,
        )
        self._model_name = embedding_config.model
        return True

    def initialize(self, force_reload: bool = False) -> bool:
        if self._initialized and not force_reload:
            return True
        self._init_embedding_client()
        self._load_faiss_index()
        self._initialized = True
        return True

    def _load_faiss_index(self) -> None:
        faiss = _get_faiss()
        self._index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
        self._item_id_map = []

        with Session(engine) as session:
            items = session.exec(
                select(LibraryItem).where(LibraryItem.embedding != None)  # noqa: E711
            ).all()
            if not items:
                return

            embeddings_list: List[np.ndarray] = []
            for item in items:
                if not item.embedding:
                    continue
                embedding = np.frombuffer(item.embedding, dtype=np.float32)
                embeddings_list.append(embedding)
                if item.id is not None:
                    self._item_id_map.append(item.id)

            if embeddings_list:
                embeddings_matrix = np.vstack(embeddings_list)
                self._index.add(embeddings_matrix)  # type: ignore[union-attr]

    async def fetch_remote_index(self) -> List[Dict[str, Any]]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    LIBRARIES_INDEX_URL,
                    timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS),
                ) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception:
            return []

    async def fetch_remote_library(self, source: str) -> Optional[Dict[str, Any]]:
        library_url = f"{LIBRARY_BASE_URL}/{source}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    library_url,
                    timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS),
                ) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception:
            return None

    async def import_library(
        self,
        library_id: str,
        name: str,
        description: str,
        source: str,
        items: List[Dict[str, Any]],
        auto_load: bool = False,
    ) -> Library:
        with Session(engine) as session:
            library = Library(
                id=library_id,
                name=name,
                description=description,
                source=source,
            )
            session.add(library)
            session.commit()

            for item_data in items:
                item_id = item_data.get("id", "")
                item_name = item_data.get("name", "Unnamed")
                elements = item_data.get("elements", [])
                embedding_bytes = await self._build_embedding_bytes(f"{item_name} {name}")

                db_item = LibraryItem(
                    library_id=library_id,
                    item_id=item_id,
                    name=item_name,
                    description="",
                    tags=[],
                    elements=elements,
                    embedding=embedding_bytes,
                )
                session.add(db_item)

            session.commit()
            session.refresh(library)
            self._save_library_to_file(
                library_id=library_id,
                name=name,
                description=description,
                items=items,
                auto_load=auto_load,
            )
            self._load_faiss_index()
            return library

    async def index_uploaded_asset(
        self,
        filename: str,
        original_name: str,
        content_type: str,
        size: int,
    ) -> None:
        display_name = self._truncate_text(original_name or filename, 100)
        description = self._build_uploaded_asset_description(
            filename=filename,
            original_name=display_name,
            content_type=content_type,
            size=size,
        )
        tags = self._build_uploaded_asset_tags(filename=filename, content_type=content_type)
        embedding_bytes = await self._build_embedding_bytes(f"{display_name} {description}")

        with Session(engine) as session:
            library = session.get(Library, UPLOADED_ASSETS_LIBRARY_ID)
            if library is None:
                library = Library(
                    id=UPLOADED_ASSETS_LIBRARY_ID,
                    name=UPLOADED_ASSETS_LIBRARY_NAME,
                    description=UPLOADED_ASSETS_LIBRARY_DESCRIPTION,
                    source=UPLOADED_ASSETS_LIBRARY_SOURCE,
                )
                session.add(library)

            item = session.exec(
                select(LibraryItem)
                .where(LibraryItem.library_id == UPLOADED_ASSETS_LIBRARY_ID)
                .where(LibraryItem.item_id == filename)
            ).first()

            if item is None:
                item = LibraryItem(
                    library_id=UPLOADED_ASSETS_LIBRARY_ID,
                    item_id=filename,
                    name=display_name,
                    description=description,
                    tags=tags,
                    elements=[],
                    embedding=embedding_bytes,
                )
                session.add(item)
            else:
                item.name = display_name
                item.description = description
                item.tags = tags
                item.embedding = embedding_bytes

            session.commit()

        self._sync_uploaded_assets_library_file()
        self._reload_index_if_ready()

    def remove_uploaded_asset(self, filename: str) -> bool:
        removed = False

        with Session(engine) as session:
            item = session.exec(
                select(LibraryItem)
                .where(LibraryItem.library_id == UPLOADED_ASSETS_LIBRARY_ID)
                .where(LibraryItem.item_id == filename)
            ).first()
            if item is None:
                return False

            session.delete(item)
            removed = True

            remaining = session.exec(
                select(LibraryItem)
                .where(LibraryItem.library_id == UPLOADED_ASSETS_LIBRARY_ID)
                .where(LibraryItem.item_id != filename)
            ).first()
            if remaining is None:
                library = session.get(Library, UPLOADED_ASSETS_LIBRARY_ID)
                if library is not None:
                    session.delete(library)

            session.commit()

        self._sync_uploaded_assets_library_file()
        self._reload_index_if_ready()
        return removed

    def get_local_libraries(self) -> List[Library]:
        with Session(engine) as session:
            return list(session.exec(select(Library)).all())

    def get_library_by_id(self, library_id: str) -> Optional[Library]:
        with Session(engine) as session:
            return session.get(Library, library_id)

    def get_library_items(self, library_id: str) -> List[LibraryItem]:
        with Session(engine) as session:
            return list(
                session.exec(
                    select(LibraryItem).where(LibraryItem.library_id == library_id)
                ).all()
            )

    def get_item_by_name(self, library_id: str, name: str) -> Optional[LibraryItem]:
        with Session(engine) as session:
            return session.exec(
                select(LibraryItem)
                .where(LibraryItem.library_id == library_id)
                .where(LibraryItem.name == name)
            ).first()

    async def _get_embedding(self, text: str) -> np.ndarray:
        assert self._client is not None
        response = await self._client.embeddings.create(
            model=self._model_name,
            input=text,
        )
        return np.array(response.data[0].embedding, dtype="float32")

    async def _build_embedding_bytes(self, text: str) -> Optional[bytes]:
        if not text.strip():
            return None
        if not self._init_embedding_client():
            return None

        try:
            embedding = await self._get_embedding(text)
            norm = float(np.linalg.norm(embedding))
            if not np.isfinite(norm) or norm <= 0:
                return None
            normalized = embedding / norm
            return normalized.tobytes()
        except Exception:
            return None

    async def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Tuple[LibraryItem, float]]:
        self.initialize()
        if not self._client or len(self._item_id_map) == 0:
            return []

        try:
            query_embedding = await self._get_embedding(query)
            query_embedding = query_embedding / np.linalg.norm(query_embedding)
            query_embedding = query_embedding.reshape(1, -1)
            k = min(top_k, len(self._item_id_map))
            distances, indices = self._index.search(query_embedding, k)  # type: ignore[union-attr]
            results: List[Tuple[LibraryItem, float]] = []
            with Session(engine) as session:
                for i, idx in enumerate(indices[0]):
                    if 0 <= idx < len(self._item_id_map):
                        item = session.get(LibraryItem, self._item_id_map[idx])
                        if item:
                            results.append((item, float(distances[0][i])))
            return results
        except Exception:
            return []

    def get_item_elements(
        self,
        item: LibraryItem,
        x: float,
        y: float,
    ) -> List[Dict[str, Any]]:
        if not item.elements:
            return []

        min_x = min_y = float("inf")
        for element in item.elements:
            min_x = min(min_x, element.get("x", 0))
            min_y = min(min_y, element.get("y", 0))

        offset_x = x - min_x if min_x != float("inf") else x
        offset_y = y - min_y if min_y != float("inf") else y
        result = []
        for element in item.elements:
            new_element = dict(element)
            new_element["x"] = element.get("x", 0) + offset_x
            new_element["y"] = element.get("y", 0) + offset_y
            new_element.setdefault("frameId", None)
            new_element.setdefault("angle", 0)
            if new_element.get("type") == "text":
                new_element.setdefault("lineHeight", 1.25)
            result.append(new_element)
        return result

    @property
    def item_count(self) -> int:
        return len(self._item_id_map)

    @property
    def embedding_available(self) -> bool:
        return self._init_embedding_client()

    def _save_library_to_file(
        self,
        library_id: str,
        name: str,
        description: str,
        items: List[Dict[str, Any]],
        auto_load: bool = False,
    ) -> None:
        """Persist a library export to the local filesystem."""

        _ = (name, description)
        try:
            library_data = {
                "type": "excalidrawlib",
                "version": 2,
                "source": "local",
                "libraryItems": items,
                "auto_load": auto_load,
            }
            filename = f"{library_id}.excalidrawlib"
            filepath = LIBRARY_DIR / filename
            with open(filepath, "w", encoding="utf-8") as file:
                json.dump(library_data, file, ensure_ascii=False, indent=2)
            logger.info("Library saved to file: %s", filepath)
        except Exception as exc:
            logger.error("Failed to save library to file: %s", exc)

    def _delete_library_file(self, library_id: str) -> None:
        filepath = LIBRARY_DIR / f"{library_id}.excalidrawlib"
        try:
            if filepath.exists():
                filepath.unlink()
        except Exception as exc:
            logger.error("Failed to delete library file %s: %s", filepath, exc)

    def _sync_uploaded_assets_library_file(self) -> None:
        with Session(engine) as session:
            items = list(
                session.exec(
                    select(LibraryItem)
                    .where(LibraryItem.library_id == UPLOADED_ASSETS_LIBRARY_ID)
                    .order_by(asc(LibraryItem.id))
                ).all()
            )

        if not items:
            self._delete_library_file(UPLOADED_ASSETS_LIBRARY_ID)
            return

        export_items = [self._build_uploaded_asset_export_item(item) for item in items]
        self._save_library_to_file(
            library_id=UPLOADED_ASSETS_LIBRARY_ID,
            name=UPLOADED_ASSETS_LIBRARY_NAME,
            description=UPLOADED_ASSETS_LIBRARY_DESCRIPTION,
            items=export_items,
            auto_load=False,
        )

    def _build_uploaded_asset_export_item(self, item: LibraryItem) -> Dict[str, Any]:
        return {
            "id": item.item_id,
            "status": "published",
            "name": item.name,
            "elements": [],
            "metadata": {
                "kind": "uploaded_asset",
                "filename": item.item_id,
                "url": f"/api/images/{item.item_id}",
                "relative_path": f"data/images/{item.item_id}",
                "description": item.description,
                "tags": list(item.tags or []),
            },
        }

    def _build_uploaded_asset_description(
        self,
        filename: str,
        original_name: str,
        content_type: str,
        size: int,
    ) -> str:
        description = (
            f"Uploaded image {original_name} stored as {filename} at /api/images/{filename}. "
            f"MIME type {content_type}. Size {size} bytes."
        )
        return self._truncate_text(description, 1000)

    def _build_uploaded_asset_tags(self, filename: str, content_type: str) -> List[str]:
        suffix = Path(filename).suffix.lstrip(".").lower()
        tags = ["uploaded", "image", content_type.lower()]
        if suffix:
            tags.append(suffix)
        return list(dict.fromkeys(tags))

    def _truncate_text(self, value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value
        return value[: max_length - 3] + "..."

    def _reload_index_if_ready(self) -> None:
        if not self._initialized:
            return
        try:
            self._load_faiss_index()
        except Exception as exc:
            logger.warning("Failed to refresh library index: %s", exc)

    def load_library_from_file(self, library_id: str) -> Optional[Dict[str, Any]]:
        """Load a previously exported library from disk."""

        try:
            filename = f"{library_id}.excalidrawlib"
            filepath = LIBRARY_DIR / filename
            if not filepath.exists():
                return None
            with open(filepath, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as exc:
            logger.error("Failed to load library from file: %s", exc)
            return None

    def get_auto_load_libraries(self) -> List[Dict[str, Any]]:
        """Return all exported libraries that are marked for auto-load."""

        auto_load_libraries: List[Dict[str, Any]] = []
        try:
            for filepath in LIBRARY_DIR.glob("*.excalidrawlib"):
                try:
                    with open(filepath, "r", encoding="utf-8") as file:
                        library_data = json.load(file)
                    if library_data.get("auto_load", False):
                        auto_load_libraries.append(
                            {
                                "id": filepath.stem,
                                "data": library_data,
                                "filepath": str(filepath),
                            }
                        )
                except Exception as exc:
                    logger.error("Failed to load library file %s: %s", filepath, exc)
        except Exception as exc:
            logger.error("Failed to scan library directory: %s", exc)
        return auto_load_libraries

    def set_library_auto_load(self, library_id: str, auto_load: bool) -> bool:
        """Update the auto-load flag on a local library export."""

        try:
            library_data = self.load_library_from_file(library_id)
            if library_data is None:
                return False
            library_data["auto_load"] = auto_load
            filename = f"{library_id}.excalidrawlib"
            filepath = LIBRARY_DIR / filename
            with open(filepath, "w", encoding="utf-8") as file:
                json.dump(library_data, file, ensure_ascii=False, indent=2)
            logger.info("Library %s auto_load set to %s", library_id, auto_load)
            return True
        except Exception as exc:
            logger.error("Failed to set auto_load for library %s: %s", library_id, exc)
            return False


library_service: LibraryService = LibraryService.get_instance()
