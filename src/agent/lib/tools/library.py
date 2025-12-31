"""模块名称: library
主要功能: AI 素材库操作工具
"""

from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field

from src.agent.core.context import AgentContext
from src.agent.core.registry import registry, ToolCategory
from src.agent.lib.canvas.helpers import (
    require_room_id,
    append_element_as_ymap,
    generate_element_id,
)
from src.agent.lib.library import library_service
from src.logger import get_logger

logger = get_logger(__name__)


class ListLibrariesArgs(BaseModel):
    """列出素材库的参数"""

    keyword: Optional[str] = Field(None, description="可选的过滤关键词")
    limit: int = Field(20, description="返回数量上限")


class SearchLibraryItemsArgs(BaseModel):
    """搜索素材库项的参数"""

    query: str = Field(..., description="搜索关键词")
    limit: int = Field(10, description="返回数量上限")


class InsertLibraryItemArgs(BaseModel):
    """插入素材库项的参数"""

    library_id: str = Field(..., description="素材库 ID")
    item_name: str = Field(..., description="素材项名称")
    x: float = Field(100.0, description="目标 X 坐标")
    y: float = Field(100.0, description="目标 Y 坐标")


class ImportRemoteLibraryArgs(BaseModel):
    """导入远程素材库的参数"""

    library_id: str = Field(..., description="素材库 ID (从 list_libraries 获取)")
    auto_load: bool = Field(False, description="是否设置为常加载（自动加载）")


class SetLibraryAutoLoadArgs(BaseModel):
    """设置素材库常加载的参数"""

    library_id: str = Field(..., description="素材库 ID")
    auto_load: bool = Field(..., description="是否设置为常加载")


class GetAutoLoadLibrariesArgs(BaseModel):
    """获取常加载素材库的参数（无需参数）"""

    pass


@registry.register(
    "list_libraries",
    "列出可用的素材库 (本地 + 远程)",
    ListLibrariesArgs,
    category=ToolCategory.CANVAS,
)
async def list_libraries(
    keyword: Optional[str] = None,
    limit: int = 20,
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """列出可用的素材库

    先返回本地已导入的素材库，然后返回远程可用的。
    """
    try:
        # 本地素材库
        local_libs = library_service.get_local_libraries()
        local_result: List[Dict[str, Any]] = []
        for lib in local_libs:
            if keyword:
                if keyword.lower() not in lib.name.lower():
                    continue
            local_result.append(
                {
                    "id": lib.id,
                    "name": lib.name,
                    "description": lib.description,
                    "source": "local",
                }
            )

        # 远程素材库
        remote_index = await library_service.fetch_remote_index()
        remote_result: List[Dict[str, Any]] = []
        local_ids = {lib.id for lib in local_libs}

        for lib_info in remote_index:
            lib_id = lib_info.get("id", "")
            if lib_id in local_ids:
                continue  # 已导入的跳过
            if keyword:
                if keyword.lower() not in lib_info.get("name", "").lower():
                    continue
            remote_result.append(
                {
                    "id": lib_id,
                    "name": lib_info.get("name", ""),
                    "description": lib_info.get("description", ""),
                    "source": lib_info.get("source", ""),
                    "is_remote": True,
                }
            )
            if len(remote_result) >= limit:
                break

        return {
            "status": "success",
            "message": f"找到 {len(local_result)} 个本地库, {len(remote_result)} 个远程库",
            "local_libraries": local_result,
            "remote_libraries": remote_result[:limit],
        }

    except Exception as e:  # pylint: disable=broad-except
        logger.error("列出素材库失败: %s", e)
        return {"status": "error", "message": str(e)}


@registry.register(
    "search_library_items",
    "语义搜索素材库中的元素",
    SearchLibraryItemsArgs,
    category=ToolCategory.CANVAS,
)
async def search_library_items(
    query: str,
    limit: int = 10,
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """语义搜索素材库中的元素 (使用 FAISS 向量搜索)"""
    try:
        results = await library_service.search(query, limit)

        result_list: List[Dict[str, Any]] = []
        for item, score in results:
            result_list.append(
                {
                    "library_id": item.library_id,
                    "item_id": item.item_id,
                    "name": item.name,
                    "score": score,
                }
            )

        logger.info("搜索素材项 '%s': %d 结果", query, len(result_list))
        return {
            "status": "success",
            "message": f"搜索 '{query}' 找到 {len(result_list)} 个结果",
            "results": result_list,
        }

    except Exception as e:  # pylint: disable=broad-except
        logger.error("搜索素材项失败: %s", e)
        return {"status": "error", "message": str(e)}


@registry.register(
    "import_remote_library",
    "导入远程素材库到本地",
    ImportRemoteLibraryArgs,
    category=ToolCategory.CANVAS,
)
async def import_remote_library(
    library_id: str,
    auto_load: bool = False,
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """导入远程素材库到本地数据库"""
    try:
        # 获取远程索引
        remote_index = await library_service.fetch_remote_index()
        lib_info: Optional[Dict[str, Any]] = None
        for item in remote_index:
            if item.get("id") == library_id:
                lib_info = item
                break

        if lib_info is None:
            return {"status": "error", "message": f"素材库 {library_id} 不存在"}

        # 加载素材库内容
        source = lib_info.get("source", "")
        library_data = await library_service.fetch_remote_library(source)
        if library_data is None:
            return {"status": "error", "message": "加载素材库失败"}

        # 导入到本地
        items = library_data.get("libraryItems", [])
        library = await library_service.import_library(
            library_id=library_id,
            name=lib_info.get("name", ""),
            description=lib_info.get("description", ""),
            source=source,
            items=items,
            auto_load=auto_load,
        )

        return {
            "status": "success",
            "message": f"已导入素材库 '{library.name}' ({len(items)} 项){' [常加载]' if auto_load else ''}",
            "library_id": library.id,
            "item_count": len(items),
            "auto_load": auto_load,
        }

    except Exception as e:  # pylint: disable=broad-except
        logger.error("导入素材库失败: %s", e)
        return {"status": "error", "message": str(e)}


@registry.register(
    "insert_library_item",
    "将素材库中的元素插入画布",
    InsertLibraryItemArgs,
    category=ToolCategory.CANVAS,
)
async def insert_library_item(
    library_id: str,
    item_name: str,
    x: float = 100.0,
    y: float = 100.0,
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """将素材库中的元素插入画布"""
    if context is None:
        return {"status": "error", "message": "Context is required"}

    room_id: str = require_room_id(context)
    doc, elements_array = await context.get_room_and_doc()

    if doc is None or elements_array is None:
        return {"status": "error", "message": "Failed to get room doc"}

    try:
        # 查找素材项
        item = library_service.get_item_by_name(library_id, item_name)
        if item is None:
            return {
                "status": "error",
                "message": f"素材项 '{item_name}' 在库 {library_id} 中不存在",
            }

        # 获取偏移后的元素
        elements = library_service.get_item_elements(item, x, y)
        if not elements:
            return {"status": "error", "message": "素材项没有元素"}

        # 插入元素到画布
        inserted_ids: List[str] = []
        with doc.transaction(origin="ai-engine/insert_library_item"):
            for element in elements:
                new_id: str = generate_element_id(element.get("type", "element"))
                element["id"] = new_id
                append_element_as_ymap(elements_array, element)
                inserted_ids.append(new_id)

        logger.info(
            "插入素材项: library=%s, item=%s, count=%d",
            library_id,
            item_name,
            len(inserted_ids),
            extra={"room": room_id},
        )

        return {
            "status": "success",
            "message": f"已插入素材 '{item_name}' ({len(inserted_ids)} 个元素)",
            "element_ids": inserted_ids,
            "position": {"x": x, "y": y},
        }

    except Exception as e:  # pylint: disable=broad-except
        logger.error("插入素材项失败: %s", e)
        return {"status": "error", "message": str(e)}


@registry.register(
    "set_library_auto_load",
    "设置素材库的常加载状态",
    SetLibraryAutoLoadArgs,
    category=ToolCategory.CANVAS,
)
async def set_library_auto_load(
    library_id: str,
    auto_load: bool,
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """设置素材库是否为常加载（自动加载）"""
    try:
        success = library_service.set_library_auto_load(library_id, auto_load)
        if success:
            return {
                "status": "success",
                "message": f"已{'启用' if auto_load else '禁用'}素材库 {library_id} 的常加载",
                "library_id": library_id,
                "auto_load": auto_load,
            }
        else:
            return {
                "status": "error",
                "message": f"素材库 {library_id} 不存在或设置失败",
            }
    except Exception as e:  # pylint: disable=broad-except
        logger.error("设置素材库常加载失败: %s", e)
        return {"status": "error", "message": str(e)}


@registry.register(
    "get_auto_load_libraries",
    "获取所有常加载的素材库",
    GetAutoLoadLibrariesArgs,
    category=ToolCategory.CANVAS,
)
async def get_auto_load_libraries(
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """获取所有设置为常加载的素材库"""
    try:
        auto_load_libs = library_service.get_auto_load_libraries()
        result_list = []
        for lib in auto_load_libs:
            result_list.append({
                "id": lib["id"],
                "filepath": lib["filepath"],
                "item_count": len(lib["data"].get("libraryItems", [])),
            })
        return {
            "status": "success",
            "message": f"找到 {len(result_list)} 个常加载素材库",
            "libraries": result_list,
        }
    except Exception as e:  # pylint: disable=broad-except
        logger.error("获取常加载素材库失败: %s", e)
        return {"status": "error", "message": str(e)}
