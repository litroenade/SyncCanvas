"""模块名称: library_embedding
主要功能: 素材库向量搜索服务

使用 SQLite 存储元数据和向量，FAISS 内存索引进行相似度搜索。
"""

from typing import List, Optional, Tuple
import numpy as np

from sqlmodel import Session, select
from openai import AsyncOpenAI

from src.config import config
from src.db.database import engine
from src.db.models import Library, LibraryItem
from src.logger import get_logger

logger = get_logger(__name__)

# 配置常量
EMBEDDING_DIMENSION: int = 1536  # OpenAI text-embedding-ada-002 默认维度

# 延迟导入 FAISS
_faiss = None


def _get_faiss():
    """延迟加载 FAISS"""
    global _faiss
    if _faiss is None:
        import faiss
        _faiss = faiss
    return _faiss


class LibraryEmbeddingService:
    """素材库向量搜索服务

    使用 SQLite 存储素材库数据，FAISS 内存索引进行语义搜索。

    Features:
    - 调用配置中的 embedding 模型 API
    - SQLite 持久化存储
    - FAISS 内存索引支持高效相似度搜索

    Attributes:
        _client: OpenAI 客户端
        _index: FAISS 内存索引
        _item_id_map: 索引位置到数据库 ID 的映射
        _initialized: 是否已初始化
    """

    _instance: Optional["LibraryEmbeddingService"] = None

    def __init__(self) -> None:
        """初始化向量搜索服务"""
        self._client: Optional[AsyncOpenAI] = None
        self._model_name: str = ""
        self._dimension: int = EMBEDDING_DIMENSION
        self._index = None
        self._item_id_map: List[int] = []  # FAISS 索引位置 -> LibraryItem.id
        self._initialized: bool = False

    @classmethod
    def get_instance(cls) -> "LibraryEmbeddingService":
        """获取服务单例"""
        if cls._instance is None:
            cls._instance = LibraryEmbeddingService()
        return cls._instance

    def _init_client(self) -> bool:
        """初始化 OpenAI 客户端"""
        if self._client is not None:
            return True

        ai_config = config.ai
        current_group = ai_config.model_groups.get(ai_config.current_model_group)

        if not current_group or not current_group.embedding_model:
            logger.warning("未配置 embedding 模型，向量搜索不可用")
            return False

        embedding_config = current_group.embedding_model
        self._client = AsyncOpenAI(
            base_url=embedding_config.base_url,
            api_key=embedding_config.api_key,
        )
        self._model_name = embedding_config.model
        logger.info("Embedding 客户端已初始化: %s", self._model_name)
        return True

    def initialize(self, force_reload: bool = False) -> bool:
        """初始化服务

        Args:
            force_reload: 是否强制重新加载

        Returns:
            bool: 是否成功初始化
        """
        if self._initialized and not force_reload:
            return True

        if not self._init_client():
            return False

        self._load_index_from_db()
        self._initialized = True
        return True

    def _load_index_from_db(self) -> None:
        """从数据库加载向量构建 FAISS 索引"""
        faiss = _get_faiss()
        self._index = faiss.IndexFlatIP(self._dimension)
        self._item_id_map = []

        with Session(engine) as session:
            items = session.exec(
                select(LibraryItem).where(LibraryItem.embedding != None)  # noqa: E711
            ).all()

            if not items:
                logger.info("数据库中无向量数据，创建空索引")
                return

            embeddings: List[np.ndarray] = []
            for item in items: 
                if item.embedding:
                    embedding = np.frombuffer(item.embedding, dtype=np.float32)
                    embeddings.append(embedding)
                    if item.id is not None:
                        self._item_id_map.append(item.id)

            if embeddings:
                embeddings_matrix = np.vstack(embeddings)
                self._index.add(embeddings_matrix)  # type: ignore[arg-type]
                logger.info("从数据库加载索引: %d 项", len(embeddings))

    async def _get_embedding(self, text: str) -> np.ndarray:
        """调用 API 获取 embedding"""
        assert self._client is not None, "Embedding client not initialized"
        response = await self._client.embeddings.create(
            model=self._model_name,
            input=text,
        )
        embedding = response.data[0].embedding
        return np.array(embedding, dtype="float32")

    async def _get_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        """批量获取 embedding"""
        assert self._client is not None, "Embedding client not initialized"
        response = await self._client.embeddings.create(
            model=self._model_name,
            input=texts,
        )
        embeddings = [item.embedding for item in response.data]
        return np.array(embeddings, dtype="float32")

    async def add_library(
        self,
        library_id: str,
        name: str,
        description: str = "",
        source: str = "local",
    ) -> Library:
        """添加素材库

        Args:
            library_id: 素材库 ID
            name: 素材库名称
            description: 描述
            source: 来源

        Returns:
            Library: 创建的素材库对象
        """
        with Session(engine) as session:
            library = Library(
                id=library_id,
                name=name,
                description=description,
                source=source,
            )
            session.add(library)
            session.commit()
            session.refresh(library)
            logger.info("添加素材库: %s (%s)", name, library_id)
            return library

    async def add_item(
        self,
        library_id: str,
        item_id: str,
        name: str,
        elements: list,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> Optional[LibraryItem]:
        """添加素材项到数据库和索引

        Args:
            library_id: 所属素材库 ID
            item_id: 素材项 ID
            name: 素材项名称
            elements: Excalidraw 元素列表
            description: 素材描述
            tags: 标签列表

        Returns:
            Optional[LibraryItem]: 创建的素材项
        """
        if not self.initialize():
            return None

        # 构建用于 embedding 的文本
        text_parts: List[str] = [name]
        if description:
            text_parts.append(description)
        if tags:
            text_parts.extend(tags)
        text: str = " ".join(text_parts)

        try:
            # 生成 embedding
            embedding = await self._get_embedding(text)
            embedding = embedding / np.linalg.norm(embedding)
            embedding_bytes = embedding.tobytes()

            # 存入数据库
            with Session(engine) as session:
                db_item = LibraryItem(
                    library_id=library_id,
                    item_id=item_id,
                    name=name,
                    description=description,
                    tags=tags or [],
                    elements=elements,
                    embedding=embedding_bytes,
                )
                session.add(db_item)
                session.commit()
                session.refresh(db_item)

                # 更新内存索引
                assert self._index is not None, "FAISS index not initialized"
                self._index.add(embedding.reshape(1, -1))  # type: ignore[arg-type]
                if db_item.id is not None:
                    self._item_id_map.append(db_item.id)

                logger.info("添加素材项: %s", name)
                return db_item

        except Exception as e:  # pylint: disable=broad-except
            logger.error("添加素材项失败: %s", e)
            return None

    async def search(
        self, query: str, top_k: int = 5
    ) -> List[Tuple[LibraryItem, float]]:
        """语义搜索素材项

        Args:
            query: 搜索查询
            top_k: 返回数量

        Returns:
            List[Tuple[LibraryItem, float]]: 匹配结果及相似度分数
        """
        if not self.initialize():
            return []

        if len(self._item_id_map) == 0:
            return []

        try:
            # 生成查询 embedding
            query_embedding = await self._get_embedding(query)
            query_embedding = query_embedding / np.linalg.norm(query_embedding)
            query_embedding = query_embedding.reshape(1, -1)

            # FAISS 搜索
            assert self._index is not None, "FAISS index not initialized"
            k: int = min(top_k, len(self._item_id_map))
            distances, indices = self._index.search(query_embedding, k)  # type: ignore[arg-type]

            # 从数据库获取完整数据
            results: List[Tuple[LibraryItem, float]] = []
            with Session(engine) as session:
                for i, idx in enumerate(indices[0]):
                    if 0 <= idx < len(self._item_id_map):
                        db_id = self._item_id_map[idx]
                        item = session.get(LibraryItem, db_id)
                        if item:
                            results.append((item, float(distances[0][i])))

            return results

        except Exception as e:  # pylint: disable=broad-except
            logger.error("搜索失败: %s", e)
            return []

    def get_libraries(self) -> List[Library]:
        """获取所有素材库"""
        with Session(engine) as session:
            return list(session.exec(select(Library)).all())

    def get_library_items(self, library_id: str) -> List[LibraryItem]:
        """获取指定素材库的所有素材项"""
        with Session(engine) as session:
            return list(
                session.exec(
                    select(LibraryItem).where(LibraryItem.library_id == library_id)
                ).all()
            )

    def get_item_by_name(self, library_id: str, name: str) -> Optional[LibraryItem]:
        """根据名称获取素材项"""
        with Session(engine) as session:
            return session.exec(
                select(LibraryItem)
                .where(LibraryItem.library_id == library_id)
                .where(LibraryItem.name == name)
            ).first()

    @property
    def item_count(self) -> int:
        """获取索引中的素材项数量"""
        return len(self._item_id_map)

    @property
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._init_client()


# 全局实例
library_embedding_service: LibraryEmbeddingService = LibraryEmbeddingService.get_instance()
