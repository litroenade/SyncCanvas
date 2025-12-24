"""元素编辑工具

提供元素的增量编辑功能：更新、删除、移动
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from src.agent.core.context import AgentContext
from src.agent.core.registry import registry, ToolCategory
from src.agent.lib.canvas.helpers import (
    require_room_id,
    find_element_by_id,
    update_element_in_array,
)
from src.logger import get_logger

logger = get_logger(__name__)


class UpdateElementArgs(BaseModel):
    """update_element 工具参数"""

    element_id: str = Field(..., description="要更新的元素 ID")
    updates: Dict[str, Any] = Field(
        ...,
        description="要更新的属性字典，如 {'strokeColor': '#ff0000', 'backgroundColor': '#ffcccc'}",
    )


class DeleteElementArgs(BaseModel):
    """delete_element 工具参数"""

    element_id: str = Field(..., description="要删除的元素 ID")


class MoveElementArgs(BaseModel):
    """move_element 工具参数"""

    element_id: str = Field(..., description="要移动的元素 ID")
    dx: float = Field(0, description="X 方向偏移量（正值向右，负值向左）")
    dy: float = Field(0, description="Y 方向偏移量（正值向下，负值向上）")


class UpdateTextArgs(BaseModel):
    """update_text 工具参数"""

    element_id: str = Field(..., description="文本元素或包含文本的容器元素 ID")
    new_text: str = Field(..., description="新的文本内容")


@registry.register(
    "update_element",
    "修改画布上元素的属性（颜色、样式等）",
    UpdateElementArgs,
    category=ToolCategory.CANVAS,
)
async def update_element(
    element_id: str,
    updates: Dict[str, Any],
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """更新元素属性

    可更新的常用属性：
    - strokeColor: 描边颜色
    - backgroundColor: 背景颜色
    - strokeWidth: 描边宽度
    - opacity: 不透明度 (0-100)
    - roughness: 粗糙度 (0-2)

    Args:
        element_id: 元素 ID
        updates: 要更新的属性字典
        context: Agent 上下文

    Returns:
        dict: 操作结果
    """
    if context is None:
        return {"status": "error", "message": "Context is required"}

    room_id = require_room_id(context)
    doc, elements_array = await context.get_room_and_doc()
    if doc is None or elements_array is None:
        return {"status": "error", "message": "Failed to get room doc"}

    # 查找元素
    idx, element = find_element_by_id(elements_array, element_id)
    if idx < 0:
        # 尝试从虚拟元素中查找
        if context.virtual_mode and context.virtual_elements:
            for i, el in enumerate(context.virtual_elements):
                if el.get("id") == element_id:
                    # 更新虚拟元素
                    context.virtual_elements[i].update(updates)
                    logger.info(
                        "[update_element] 虚拟模式: 更新元素 %s",
                        element_id,
                    )
                    return {
                        "status": "success",
                        "message": f"已更新元素 {element_id} 的属性",
                        "updated_keys": list(updates.keys()),
                    }
        return {
            "status": "error",
            "message": f"找不到元素: {element_id}",
        }

    # 过滤掉不应该修改的属性
    protected_keys = {"id", "type", "isDeleted", "version", "versionNonce"}
    safe_updates = {k: v for k, v in updates.items() if k not in protected_keys}

    if not safe_updates:
        return {
            "status": "error",
            "message": "没有可更新的属性（id, type 等不可修改）",
        }

    with doc.transaction(origin="ai-engine/update_element"):
        update_element_in_array(elements_array, element_id, safe_updates)

    logger.info(
        "更新元素: %s",
        element_id,
        extra={"room": room_id, "updates": list(safe_updates.keys())},
    )

    return {
        "status": "success",
        "message": f"已更新元素 {element_id} 的属性",
        "updated_keys": list(safe_updates.keys()),
    }


@registry.register(
    "delete_element",
    "删除画布上的元素",
    DeleteElementArgs,
    category=ToolCategory.CANVAS,
)
async def delete_element(
    element_id: str,
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """删除元素（标记为 isDeleted: true）

    Args:
        element_id: 要删除的元素 ID
        context: Agent 上下文

    Returns:
        dict: 操作结果
    """
    if context is None:
        return {"status": "error", "message": "Context is required"}

    room_id = require_room_id(context)
    doc, elements_array = await context.get_room_and_doc()
    if doc is None or elements_array is None:
        return {"status": "error", "message": "Failed to get room doc"}

    # 查找元素
    idx, element = find_element_by_id(elements_array, element_id)
    if idx < 0:
        # 尝试从虚拟元素中删除
        if context.virtual_mode and context.virtual_elements:
            for i, el in enumerate(context.virtual_elements):
                if el.get("id") == element_id:
                    context.virtual_elements.pop(i)
                    logger.info(
                        "[delete_element] 虚拟模式: 删除元素 %s",
                        element_id,
                    )
                    return {
                        "status": "success",
                        "message": f"已删除元素 {element_id}",
                    }
        return {
            "status": "error",
            "message": f"找不到元素: {element_id}",
        }

    with doc.transaction(origin="ai-engine/delete_element"):
        # Excalidraw 使用软删除
        update_element_in_array(elements_array, element_id, {"isDeleted": True})

        # 清理绑定关系
        bound_elements = element.get("boundElements") or []
        for bound in bound_elements:
            if isinstance(bound, dict):
                bound_id = bound.get("id")
                if bound_id:
                    # 也删除绑定的元素（如文本）
                    update_element_in_array(
                        elements_array, bound_id, {"isDeleted": True}
                    )

    logger.info(
        "删除元素: %s",
        element_id,
        extra={"room": room_id},
    )

    return {
        "status": "success",
        "message": f"已删除元素 {element_id}",
    }


@registry.register(
    "move_element",
    "移动画布上的元素到新位置",
    MoveElementArgs,
    category=ToolCategory.CANVAS,
)
async def move_element(
    element_id: str,
    dx: float = 0,
    dy: float = 0,
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """移动元素

    移动元素及其绑定的文本元素

    Args:
        element_id: 元素 ID
        dx: X 方向偏移
        dy: Y 方向偏移
        context: Agent 上下文

    Returns:
        dict: 操作结果
    """
    if context is None:
        return {"status": "error", "message": "Context is required"}

    if dx == 0 and dy == 0:
        return {"status": "success", "message": "无需移动（偏移为 0）"}

    room_id = require_room_id(context)
    doc, elements_array = await context.get_room_and_doc()
    if doc is None or elements_array is None:
        return {"status": "error", "message": "Failed to get room doc"}

    # 查找元素
    idx, element = find_element_by_id(elements_array, element_id)
    if idx < 0:
        # 尝试从虚拟元素中移动
        if context.virtual_mode and context.virtual_elements:
            for i, el in enumerate(context.virtual_elements):
                if el.get("id") == element_id:
                    el["x"] = el.get("x", 0) + dx
                    el["y"] = el.get("y", 0) + dy
                    logger.info(
                        "[move_element] 虚拟模式: 移动元素 %s by (%s, %s)",
                        element_id,
                        dx,
                        dy,
                    )
                    return {
                        "status": "success",
                        "message": f"已移动元素 {element_id}",
                        "new_position": {"x": el["x"], "y": el["y"]},
                    }
        return {
            "status": "error",
            "message": f"找不到元素: {element_id}",
        }

    new_x = element.get("x", 0) + dx
    new_y = element.get("y", 0) + dy

    with doc.transaction(origin="ai-engine/move_element"):
        update_element_in_array(elements_array, element_id, {"x": new_x, "y": new_y})

        # 移动绑定的文本元素
        bound_elements = element.get("boundElements") or []
        for bound in bound_elements:
            if isinstance(bound, dict) and bound.get("type") == "text":
                text_id = bound.get("id")
                if text_id:
                    _, text_el = find_element_by_id(elements_array, text_id)
                    if text_el:
                        text_new_x = text_el.get("x", 0) + dx
                        text_new_y = text_el.get("y", 0) + dy
                        update_element_in_array(
                            elements_array, text_id, {"x": text_new_x, "y": text_new_y}
                        )

    logger.info(
        "移动元素: %s",
        element_id,
        extra={"room": room_id, "dx": dx, "dy": dy},
    )

    return {
        "status": "success",
        "message": f"已移动元素 {element_id}",
        "new_position": {"x": new_x, "y": new_y},
    }


@registry.register(
    "update_text",
    "更新文本元素或容器内的文本内容",
    UpdateTextArgs,
    category=ToolCategory.CANVAS,
)
async def update_text(
    element_id: str,
    new_text: str,
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """更新文本内容

    如果 element_id 是容器元素，会更新其绑定的文本

    Args:
        element_id: 元素 ID
        new_text: 新文本内容
        context: Agent 上下文

    Returns:
        dict: 操作结果
    """
    if context is None:
        return {"status": "error", "message": "Context is required"}

    room_id = require_room_id(context)
    doc, elements_array = await context.get_room_and_doc()
    if doc is None or elements_array is None:
        return {"status": "error", "message": "Failed to get room doc"}

    idx, element = find_element_by_id(elements_array, element_id)
    if idx < 0:
        return {"status": "error", "message": f"找不到元素: {element_id}"}

    text_element_id = element_id
    element_type = element.get("type")

    # 如果是容器元素，找到绑定的文本
    if element_type in ("rectangle", "diamond", "ellipse"):
        bound_elements = element.get("boundElements") or []
        text_id = None
        for bound in bound_elements:
            if isinstance(bound, dict) and bound.get("type") == "text":
                text_id = bound.get("id")
                break
        if text_id:
            text_element_id = text_id
        else:
            return {"status": "error", "message": f"元素 {element_id} 没有绑定的文本"}

    with doc.transaction(origin="ai-engine/update_text"):
        update_element_in_array(
            elements_array,
            text_element_id,
            {
                "text": new_text,
                "originalText": new_text,
            },
        )

    logger.info(
        "更新文本: %s",
        text_element_id,
        extra={"room": room_id, "new_text": new_text[:20]},
    )

    return {
        "status": "success",
        "message": f"已更新文本为: {new_text}",
        "text_element_id": text_element_id,
    }
