"""
素材库服务
"""

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Any
import numpy as np

from sqlmodel import Session, select
from openai import AsyncOpenAI
import aiohttp

from src.config import config
from src.db.database import engine
from src.agent.lib.library.models import Library, LibraryItem
from src.logger import get_logger

if TYPE_CHECKING:
    import faiss

logger = get_logger(__name__)

LIBRARIES_INDEX_URL: str = "https://libraries.excalidraw.com/libraries.json"
LIBRARY_BASE_URL: str = "https://libraries.excalidraw.com"
HTTP_TIMEOUT_SECONDS: int = 30
EMBEDDING_DIMENSION: int = 1536

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
        self._model_name: str = ""
        self._index: Optional["faiss.IndexFlatIP"] = None
        self._item_id_map: List[int] = []
        self._initialized: bool = False

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
                if item.embedding:
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
    ) -> Library:
        with Session(engine) as session:
            library = Library(
                id=library_id, name=name, description=description, source=source
            )
            session.add(library)
            session.commit()
            for item_data in items:
                item_id = item_data.get("id", "")
                item_name = item_data.get("name", "Unnamed")
                elements = item_data.get("elements", [])
                embedding_bytes = None
                if self._client:
                    try:
                        embedding = await self._get_embedding(f"{item_name} {name}")
                        embedding = embedding / np.linalg.norm(embedding)
                        embedding_bytes = embedding.tobytes()
                    except Exception:
                        pass
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
            self._load_faiss_index()
            return library

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
            model=self._model_name, input=text
        )
        return np.array(response.data[0].embedding, dtype="float32")

    async def search(
        self, query: str, top_k: int = 5
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
            results = []
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
        self, item: LibraryItem, x: float, y: float
    ) -> List[Dict[str, Any]]:
        if not item.elements:
            return []
        min_x = min_y = float("inf")
        for el in item.elements:
            min_x = min(min_x, el.get("x", 0))
            min_y = min(min_y, el.get("y", 0))
        offset_x = x - min_x if min_x != float("inf") else x
        offset_y = y - min_y if min_y != float("inf") else y
        result = []
        for el in item.elements:
            new_el = dict(el)
            new_el["x"] = el.get("x", 0) + offset_x
            new_el["y"] = el.get("y", 0) + offset_y
            new_el.setdefault("frameId", None)
            new_el.setdefault("angle", 0)
            if new_el.get("type") == "text":
                new_el.setdefault("lineHeight", 1.25)
            result.append(new_el)
        return result

    @property
    def item_count(self) -> int:
        return len(self._item_id_map)

    @property
    def embedding_available(self) -> bool:
        return self._init_embedding_client()


library_service: LibraryService = LibraryService.get_instance()
