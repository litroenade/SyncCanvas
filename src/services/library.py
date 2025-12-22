"""
模块名称: library
主要功能: 素材库统一服务
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from sqlmodel import Session, select
from openai import AsyncOpenAI
import aiohttp

from src.config import config
from src.db.database import engine
from src.db.models import Library, LibraryItem
from src.logger import get_logger

logger = get_logger(__name__)

LIBRARIES_INDEX_URL: str = "https://libraries.excalidraw.com/libraries.json"
"""Excalidraw 公共素材库索引 URL"""

LIBRARY_BASE_URL: str = "https://libraries.excalidraw.com"
"""素材库文件基础 URL"""

HTTP_TIMEOUT_SECONDS: int = 30
"""HTTP 请求超时时间 (秒)"""

EMBEDDING_DIMENSION: int = 1536
"""向量维度 (OpenAI text-embedding-ada-002 标准维度)"""

_faiss_module = None


def _get_faiss():
    """延迟加载 FAISS 模块

    FAISS 是重量级依赖，延迟加载可优化启动时间。

    Returns:
        faiss 模块
    """
    global _faiss_module
    if _faiss_module is None:
        import faiss

        _faiss_module = faiss
    return _faiss_module


class LibraryService:
    """素材库统一服务

    整合远程获取、本地 SQLite 存储和 FAISS 向量搜索的统一服务类。
    采用单例模式确保全局唯一实例。

    Attributes:
        _client (AsyncOpenAI): OpenAI API 客户端，用于生成 embedding
        _model_name (str): Embedding 模型名称
        _index: FAISS 向量索引实例
        _item_id_map (List[int]): FAISS 索引位置到数据库 ID 的映射
        _initialized (bool): 服务是否已初始化
    """

    # 类级属性: 单例实例
    _instance: Optional["LibraryService"] = None

    def __init__(self) -> None:
        """初始化素材库服务

        注意: 请使用 get_instance() 获取单例实例，不要直接实例化。
        """
        self._client: Optional[AsyncOpenAI] = None
        self._model_name: str = ""
        self._index = None
        self._item_id_map: List[int] = []
        self._initialized: bool = False

    @classmethod
    def get_instance(cls) -> "LibraryService":
        """获取服务单例实例

        Returns:
            LibraryService: 全局唯一的服务实例
        """
        if cls._instance is None:
            cls._instance = LibraryService()
        return cls._instance

    def _init_embedding_client(self) -> bool:
        """初始化 OpenAI Embedding 客户端

        从配置中读取 embedding 模型设置并创建客户端。
        如果未配置 embedding 模型，向量搜索功能将不可用。

        Returns:
            bool: 是否成功初始化
        """
        if self._client is not None:
            return True

        ai_config = config.ai
        current_group = ai_config.model_groups.get(ai_config.current_model_group)

        if not current_group or not current_group.embedding_model:
            logger.warning("未配置 embedding 模型，向量搜索功能不可用")
            return False

        embedding_config = current_group.embedding_model
        self._client = AsyncOpenAI(
            base_url=embedding_config.base_url,
            api_key=embedding_config.api_key,
        )
        self._model_name = embedding_config.model
        logger.info("Embedding 客户端已初始化: model=%s", self._model_name)
        return True

    def initialize(self, force_reload: bool = False) -> bool:
        """初始化服务

        执行以下初始化操作:
        1. 初始化 embedding 客户端
        2. 从数据库加载向量数据构建 FAISS 索引

        Args:
            force_reload: 是否强制重新初始化

        Returns:
            bool: 是否成功初始化
        """
        if self._initialized and not force_reload:
            return True

        self._init_embedding_client()
        self._load_faiss_index()
        self._initialized = True
        return True

    def _load_faiss_index(self) -> None:
        """从数据库加载向量数据构建 FAISS 内存索引

        遍历数据库中所有包含 embedding 的素材项，
        将向量加载到 FAISS IndexFlatIP (内积相似度) 索引中。
        """
        faiss = _get_faiss()
        self._index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
        self._item_id_map = []

        with Session(engine) as session:
            # 查询所有有 embedding 的素材项
            items = session.exec(
                select(LibraryItem).where(LibraryItem.embedding != None)  # noqa: E711
            ).all()

            if not items:
                logger.info("数据库中无向量数据，创建空 FAISS 索引")
                return

            # 反序列化向量并添加到索引
            embeddings_list: List[np.ndarray] = []
            for item in items:
                if item.embedding:
                    embedding = np.frombuffer(item.embedding, dtype=np.float32)
                    embeddings_list.append(embedding)
                    if item.id is not None:
                        self._item_id_map.append(item.id)

            if embeddings_list:
                embeddings_matrix = np.vstack(embeddings_list)
                self._index.add(embeddings_matrix)  # type: ignore[arg-type]
                logger.info("FAISS 索引已加载: %d 个向量", len(embeddings_list))

    async def fetch_remote_index(self) -> List[Dict[str, Any]]:
        """从远程获取 Excalidraw 公共素材库索引

        访问 libraries.excalidraw.com 获取所有公开素材库的元信息列表。

        Returns:
            List[Dict]: 素材库元信息列表，每个字典包含:
                - id: 素材库唯一标识
                - name: 素材库名称
                - description: 描述
                - source: 素材库文件相对路径
                - authors: 作者信息列表

        Raises:
            网络错误时返回空列表，不抛出异常
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    LIBRARIES_INDEX_URL,
                    timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS),
                ) as response:
                    response.raise_for_status()
                    data: List[Dict[str, Any]] = await response.json()

            logger.info("获取远程素材库索引: %d 个库", len(data))
            return data

        except aiohttp.ClientError as e:
            logger.error("获取远程素材库索引失败 (网络错误): %s", e)
            return []
        except Exception as e:  # pylint: disable=broad-except
            logger.error("获取远程素材库索引失败: %s", e)
            return []

    async def fetch_remote_library(self, source: str) -> Optional[Dict[str, Any]]:
        """从远程加载素材库完整内容

        根据 source 路径从 Excalidraw 服务器下载素材库 JSON 文件。

        Args:
            source: 素材库文件相对路径 (如 "youritjang/software-architecture.excalidrawlib")

        Returns:
            Optional[Dict]: 素材库完整数据，包含:
                - type: "excalidrawlib"
                - version: 版本号
                - libraryItems: 素材项数组
            加载失败返回 None
        """
        library_url: str = f"{LIBRARY_BASE_URL}/{source}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    library_url,
                    timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS),
                ) as response:
                    response.raise_for_status()
                    data: Dict[str, Any] = await response.json()

            logger.info("加载远程素材库成功: %s", source)
            return data

        except aiohttp.ClientError as e:
            logger.error("加载远程素材库失败 [%s] (网络错误): %s", source, e)
            return None
        except Exception as e:  # pylint: disable=broad-except
            logger.error("加载远程素材库失败 [%s]: %s", source, e)
            return None

    async def import_library(
        self,
        library_id: str,
        name: str,
        description: str,
        source: str,
        items: List[Dict[str, Any]],
    ) -> Library:
        """导入素材库到本地数据库

        将远程获取的素材库数据持久化到 SQLite，并为每个素材项生成 embedding。

        Args:
            library_id: 素材库唯一标识
            name: 素材库名称
            description: 素材库描述
            source: 来源路径
            items: 素材项列表，每项包含 id, name, elements

        Returns:
            Library: 创建的素材库 ORM 对象
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

            for item_data in items:
                item_id: str = item_data.get("id", "")
                item_name: str = item_data.get("name", "Unnamed")
                elements: List[Dict] = item_data.get("elements", [])

                embedding_bytes: Optional[bytes] = None
                if self._client:
                    try:
                        # 使用素材名称和库名作为语义文本
                        semantic_text: str = f"{item_name} {name}"
                        embedding = await self._get_embedding(semantic_text)
                        # L2 归一化用于内积相似度
                        embedding = embedding / np.linalg.norm(embedding)
                        embedding_bytes = embedding.tobytes()
                    except Exception as e:  # pylint: disable=broad-except
                        logger.warning("生成 embedding 失败 [%s]: %s", item_name, e)

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
            logger.info("素材库导入完成: %s (%d 项)", name, len(items))

            # 5. 重建 FAISS 索引以包含新数据
            self._load_faiss_index()

            return library

    def get_local_libraries(self) -> List[Library]:
        """获取所有本地已导入的素材库

        Returns:
            List[Library]: 素材库 ORM 对象列表
        """
        with Session(engine) as session:
            return list(session.exec(select(Library)).all())

    def get_library_by_id(self, library_id: str) -> Optional[Library]:
        """根据 ID 获取素材库

        Args:
            library_id: 素材库唯一标识

        Returns:
            Optional[Library]: 素材库对象，不存在返回 None
        """
        with Session(engine) as session:
            return session.get(Library, library_id)

    def get_library_items(self, library_id: str) -> List[LibraryItem]:
        """获取指定素材库的所有素材项

        Args:
            library_id: 素材库 ID

        Returns:
            List[LibraryItem]: 素材项 ORM 对象列表
        """
        with Session(engine) as session:
            return list(
                session.exec(
                    select(LibraryItem).where(LibraryItem.library_id == library_id)
                ).all()
            )

    def get_item_by_name(self, library_id: str, name: str) -> Optional[LibraryItem]:
        """根据名称获取素材项

        Args:
            library_id: 素材库 ID
            name: 素材项名称

        Returns:
            Optional[LibraryItem]: 素材项对象，不存在返回 None
        """
        with Session(engine) as session:
            return session.exec(
                select(LibraryItem)
                .where(LibraryItem.library_id == library_id)
                .where(LibraryItem.name == name)
            ).first()

    async def _get_embedding(self, text: str) -> np.ndarray:
        """调用 OpenAI API 获取文本的 embedding 向量

        Args:
            text: 输入文本

        Returns:
            np.ndarray: shape=(EMBEDDING_DIMENSION,) 的 float32 向量
        """
        assert self._client is not None, "Embedding client not initialized"
        response = await self._client.embeddings.create(
            model=self._model_name,
            input=text,
        )
        embedding_list = response.data[0].embedding
        return np.array(embedding_list, dtype="float32")

    async def search(
        self, query: str, top_k: int = 5
    ) -> List[Tuple[LibraryItem, float]]:
        """语义搜索素材项

        使用 FAISS 索引进行基于向量相似度的语义搜索。

        Args:
            query: 搜索查询文本
            top_k: 返回结果数量上限

        Returns:
            List[Tuple[LibraryItem, float]]: (素材项, 相似度分数) 元组列表，
            按相似度降序排列
        """
        self.initialize()

        if not self._client:
            logger.warning("embedding 客户端未初始化，无法执行语义搜索")
            return []

        if len(self._item_id_map) == 0:
            logger.debug("FAISS 索引为空，无搜索结果")
            return []

        try:
            # 1. 生成查询向量
            query_embedding = await self._get_embedding(query)
            # L2 归一化
            query_embedding = query_embedding / np.linalg.norm(query_embedding)
            query_embedding = query_embedding.reshape(1, -1)

            # 2. FAISS 最近邻搜索
            assert self._index is not None, "FAISS index not initialized"
            k: int = min(top_k, len(self._item_id_map))
            distances, indices = self._index.search(query_embedding, k)  # type: ignore[arg-type]

            # 3. 从数据库获取完整素材项
            results: List[Tuple[LibraryItem, float]] = []
            with Session(engine) as session:
                for i, idx in enumerate(indices[0]):
                    if 0 <= idx < len(self._item_id_map):
                        db_id: int = self._item_id_map[idx]
                        item = session.get(LibraryItem, db_id)
                        if item:
                            similarity_score: float = float(distances[0][i])
                            results.append((item, similarity_score))

            logger.debug("语义搜索 '%s': 返回 %d 结果", query, len(results))
            return results

        except Exception as e:  # pylint: disable=broad-except
            logger.error("语义搜索失败: %s", e)
            return []

    def get_item_elements(
        self, item: LibraryItem, x: float, y: float
    ) -> List[Dict[str, Any]]:
        """获取素材项的元素并偏移到目标位置

        将素材项中的 Excalidraw 元素坐标偏移到指定位置，
        用于在画布上插入素材。

        Args:
            item: 素材项 ORM 对象
            x: 目标 X 坐标
            y: 目标 Y 坐标

        Returns:
            List[Dict]: 偏移后的元素列表 (深拷贝)
        """
        if not item.elements:
            return []

        # 1. 计算边界框
        min_x: float = float("inf")
        min_y: float = float("inf")

        for element in item.elements:
            elem_x: float = element.get("x", 0)
            elem_y: float = element.get("y", 0)
            min_x = min(min_x, elem_x)
            min_y = min(min_y, elem_y)

        # 2. 计算偏移量
        offset_x: float = x - min_x if min_x != float("inf") else x
        offset_y: float = y - min_y if min_y != float("inf") else y

        # 3. 应用偏移并规范化字段 (深拷贝避免修改原数据)
        result: List[Dict[str, Any]] = []
        for element in item.elements:
            new_element: Dict[str, Any] = dict(element)
            new_element["x"] = element.get("x", 0) + offset_x
            new_element["y"] = element.get("y", 0) + offset_y

            # 确保必需字段存在 (Excalidraw 兼容性)
            if "frameId" not in new_element:
                new_element["frameId"] = None
            if "angle" not in new_element:
                new_element["angle"] = 0

            # 文本元素需要 lineHeight
            if new_element.get("type") == "text":
                if "lineHeight" not in new_element:
                    new_element["lineHeight"] = 1.25

            result.append(new_element)

        return result

    @property
    def item_count(self) -> int:
        """获取 FAISS 索引中的素材项数量

        Returns:
            int: 已索引的素材项数量
        """
        return len(self._item_id_map)

    @property
    def embedding_available(self) -> bool:
        """检查 embedding 服务是否可用

        Returns:
            bool: 是否可以执行向量搜索
        """
        return self._init_embedding_client()


library_service: LibraryService = LibraryService.get_instance()
"""全局素材库服务实例"""
