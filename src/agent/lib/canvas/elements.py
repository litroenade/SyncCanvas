import random
from typing import Optional, List, Dict, Any

from pycrdt import Map

from src.agent.core.context import AgentContext
from src.agent.core.registry import registry, ToolCategory
from src.agent.lib.canvas.schemas import (
    CreateExcalidrawElementArgs,
    ListElementsArgs,
    GetElementByIdArgs,
    UpdateElementArgs,
    DeleteElementsArgs,
    ClearCanvasArgs,
    BatchCreateElementsArgs,
    AutoLayoutCreateArgs,
    GroupElementsArgs,
    UngroupElementsArgs,
)
from src.agent.lib.canvas.helpers import (
    require_room_id,
    base_excalidraw_element,
    find_element_by_id,
    append_element_as_ymap,
    get_theme_colors,
    generate_element_id,
)
from .batch_helpers import create_shape_and_text, create_arrow_between_nodes
from src.agent.lib.canvas.layout import calculate_layout
from src.logger import get_logger

logger = get_logger(__name__)


@registry.register(
    "create_element",
    "在画布上创建基础 Excalidraw 元素",
    CreateExcalidrawElementArgs,
    category=ToolCategory.CANVAS,
)
async def create_element(
    element_type: str,
    x: float,
    y: float,
    width: float = 100,
    height: float = 100,
    text: str = "",
    stroke_color: str = "",
    bg_color: str = "",
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """创建单个 Excalidraw 元素

    Args:
        element_type: 元素类型
        x: X 坐标
        y: Y 坐标
        width: 宽度
        height: 高度
        text: 文本内容 (仅 text 类型需要)
        stroke_color: 描边颜色 (空=使用主题默认)
        bg_color: 背景颜色 (空=使用主题默认)
        context: Agent 上下文

    Returns:
        dict: 包含 status, element_id 的结果
    """
    if context is None:
        return {"status": "error", "message": "Context is required"}
    room_id = require_room_id(context)

    logger.debug("[create_element] 获取房间文档: room_id=%s", room_id)
    doc, elements_array = await context.get_room_and_doc()

    if doc is None or elements_array is None:
        logger.error(
            "[create_element] 获取房间文档失败: doc=%s, array=%s", doc, elements_array
        )
        return {"status": "error", "message": "Failed to get room doc"}

    logger.debug("[create_element] 文档已获取: array_len=%d", len(elements_array))

    # 获取主题颜色
    theme_colors = get_theme_colors(context.theme)
    stroke_color = stroke_color or theme_colors["stroke"]
    bg_color = bg_color or theme_colors["background"]

    element = base_excalidraw_element(
        element_type, x, y, width, height, stroke_color, bg_color
    )

    if element_type == "text":
        element.update(
            {
                "text": text or "文本",
                "fontSize": 20,
                "fontFamily": 1,  # 1=Virgil(手写), 2=Helvetica, 3=Cascadia
                "textAlign": "left",
                "verticalAlign": "top",
                "originalText": text or "文本",
                "autoResize": True,  # Excalidraw 必需: 自动调整宽度
                "lineHeight": 1.25,  # Excalidraw 必需: 行高 (unitless)
                "containerId": None,  # 如果绑定到容器则设置容器 ID
            }
        )
        # 文本元素不需要背景色和圆角
        element["backgroundColor"] = "transparent"
        element["roundness"] = None
    if context.virtual_mode:
        context.virtual_elements.append(element)
        context.created_element_ids.append(element["id"])
        logger.info(
            "[create_element] 虚拟模式: 元素已添加到 virtual_elements, count=%d",
            len(context.virtual_elements),
        )
        return {
            "status": "success",
            "message": f"已创建 {element_type} (虚拟模式)",
            "element_id": element["id"],
            "element": element,  # 虚拟模式返回完整元素数据
        }

    with doc.transaction(origin="ai-engine/create_element"):
        append_element_as_ymap(elements_array, element)

    logger.info(
        "[create_element]   事务完成, array_len=%d, element_id=%s",
        len(elements_array),
        element["id"],
    )
    # 验证元素是否真的在数组中
    found = False
    for i, el in enumerate(elements_array):
        el_id = el.get("id") if hasattr(el, "get") else None
        if el_id == element["id"]:
            logger.info("[create_element]   元素确认存在于 Y.Array[%d]", i)
            found = True
            break
    if not found:
        logger.error("[create_element]   元素未找到! 可能写入失败")

    context.created_element_ids.append(element["id"])
    logger.info(
        "创建元素: %s", element["id"], extra={"room": room_id, "type": element_type}
    )

    return {
        "status": "success",
        "message": f"已创建 {element_type}",
        "element_id": element["id"],
    }


@registry.register(
    "list_elements",
    "列出画布上的元素摘要信息",
    ListElementsArgs,
    category=ToolCategory.CANVAS,
)
async def list_elements(
    limit: int = 30,
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """获取画布上的元素列表摘要

    Args:
        limit: 返回的元素数量上限
        context: Agent 上下文

    Returns:
        dict: 包含 status, total, elements 的结果
    """
    if context is None:
        return {"status": "error", "message": "Context is required"}
    require_room_id(context)  # 验证
    _, elements_array = await context.get_room_and_doc()
    if elements_array is None:
        return {"status": "error", "message": "Failed to get elements array"}

    elements = []
    for i in range(min(len(elements_array), limit)):
        el = elements_array[i]
        if isinstance(el, Map):
            el = dict(el)

        if el.get("isDeleted"):
            continue

        elements.append(
            {
                "id": el.get("id"),
                "type": el.get("type"),
                "x": round(el.get("x", 0), 1),
                "y": round(el.get("y", 0), 1),
                "width": round(el.get("width", 0), 1),
                "height": round(el.get("height", 0), 1),
                "text": el.get("text", "")[:50] if el.get("text") else None,
            }
        )

    return {
        "status": "success",
        "total": len(elements_array),
        "shown": len(elements),
        "elements": elements,
    }


@registry.register(
    "get_element",
    "获取指定元素的详细信息",
    GetElementByIdArgs,
    category=ToolCategory.CANVAS,
)
async def get_element(
    element_id: str,
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """获取指定元素的详细信息

    Args:
        element_id: 元素 ID
        context: Agent 上下文

    Returns:
        dict: 包含元素详细信息的结果
    """
    if context is None:
        return {"status": "error", "message": "Context is required"}
    require_room_id(context)  # 验证
    _, elements_array = await context.get_room_and_doc()
    if elements_array is None:
        return {"status": "error", "message": "Failed to get elements array"}

    _, element = find_element_by_id(elements_array, element_id)

    if not element:
        return {"status": "error", "message": f"元素不存在: {element_id}"}

    return {
        "status": "success",
        "element": {
            "id": element.get("id"),
            "type": element.get("type"),
            "x": element.get("x"),
            "y": element.get("y"),
            "width": element.get("width"),
            "height": element.get("height"),
            "text": element.get("text"),
            "strokeColor": element.get("strokeColor"),
            "backgroundColor": element.get("backgroundColor"),
            "boundElements": element.get("boundElements"),
        },
    }


@registry.register(
    "update_element",
    "更新元素的属性 (位置、尺寸、颜色等)",
    UpdateElementArgs,
    category=ToolCategory.CANVAS,
)
async def update_element(
    element_id: str,
    x: Optional[float] = None,
    y: Optional[float] = None,
    width: Optional[float] = None,
    height: Optional[float] = None,
    text: Optional[str] = None,
    stroke_color: Optional[str] = None,
    bg_color: Optional[str] = None,
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """更新已存在元素的属性

    Args:
        element_id: 元素 ID
        x: 新的 X 坐标
        y: 新的 Y 坐标
        width: 新的宽度
        height: 新的高度
        text: 新的文本内容
        stroke_color: 新的描边颜色
        bg_color: 新的背景颜色
        context: Agent 上下文

    Returns:
        dict: 包含 status, updated_fields 的结果
    """
    if context is None:
        return {"status": "error", "message": "Context is required"}
    room_id = require_room_id(context)
    doc, elements_array = await context.get_room_and_doc()
    if doc is None or elements_array is None:
        return {"status": "error", "message": "Failed to get room doc"}

    index, current = find_element_by_id(elements_array, element_id)
    if index < 0:
        return {"status": "error", "message": f"元素不存在: {element_id}"}

    updated_fields = []
    y_map = elements_array[index]

    with doc.transaction(origin="ai-engine/update_element"):
        if x is not None:
            y_map["x"] = x
            updated_fields.append("x")
        if y is not None:
            y_map["y"] = y
            updated_fields.append("y")
        if width is not None:
            y_map["width"] = width
            updated_fields.append("width")
        if height is not None:
            y_map["height"] = height
            updated_fields.append("height")
        if text is not None:
            y_map["text"] = text
            y_map["originalText"] = text
            updated_fields.append("text")
        if stroke_color is not None:
            y_map["strokeColor"] = stroke_color
            updated_fields.append("strokeColor")
        if bg_color is not None:
            y_map["backgroundColor"] = bg_color
            updated_fields.append("backgroundColor")

        y_map["version"] = current.get("version", 0) + 1
        y_map["versionNonce"] = random.randint(1, 1000000000)

    if not updated_fields:
        return {"status": "noop", "message": "没有需要更新的字段"}

    logger.info(
        "更新元素: %s", element_id, extra={"room": room_id, "fields": updated_fields}
    )

    return {
        "status": "success",
        "message": f"已更新元素 {element_id}",
        "element_id": element_id,
        "updated_fields": updated_fields,
    }


@registry.register(
    "delete_elements",
    "删除指定的元素",
    DeleteElementsArgs,
    category=ToolCategory.CANVAS,
)
async def delete_elements(
    element_ids: List[str],
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """删除指定 ID 的元素

    Args:
        element_ids: 要删除的元素 ID 列表
        context: Agent 上下文

    Returns:
        dict: 包含 status, removed 的结果
    """
    if context is None:
        return {"status": "error", "message": "Context is required"}
    room_id = require_room_id(context)
    doc, elements_array = await context.get_room_and_doc()
    if doc is None or elements_array is None:
        return {"status": "error", "message": "Failed to get room doc"}

    removed = []
    id_set = set(element_ids)

    with doc.transaction(origin="ai-engine/delete_elements"):
        for i in range(len(elements_array) - 1, -1, -1):
            el = elements_array[i]
            el_id = el.get("id") if isinstance(el, Map) else el.get("id")
            if el_id in id_set:
                elements_array.delete(i, 1)  # type: ignore[attr-defined]
                removed.append(el_id)

    logger.info("删除元素: %d 个", len(removed), extra={"room": room_id})

    return {
        "status": "success",
        "message": f"已删除 {len(removed)} 个元素",
        "removed": removed,
    }


@registry.register(
    "clear_canvas",
    "清空画布上的所有元素",
    ClearCanvasArgs,
    category=ToolCategory.CANVAS,
    dangerous=True,
)
async def clear_canvas(
    confirm: bool = True,
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """清空画布上的所有元素

    Args:
        confirm: 确认标志
        context: Agent 上下文

    Returns:
        dict: 包含 status, message 的结果
    """
    if not confirm:
        return {"status": "cancelled", "message": "操作已取消"}

    if context is None:
        return {"status": "error", "message": "Context is required"}
    room_id = require_room_id(context)
    doc, elements_array = await context.get_room_and_doc()
    if doc is None or elements_array is None:
        return {"status": "error", "message": "Failed to get room doc"}

    count = len(elements_array)

    with doc.transaction(origin="ai-engine/clear_canvas"):
        elements_array.delete(0, count)  # type: ignore[attr-defined]

    logger.info("清空画布: 删除了 %d 个元素", count, extra={"room": room_id})

    return {"status": "success", "message": f"已清空画布 (删除了 {count} 个元素)"}


@registry.register(
    "batch_create_elements",
    "批量创建流程图元素和连接线 (支持 JSON 规划)",
    BatchCreateElementsArgs,
    category=ToolCategory.CANVAS,
)
async def batch_create_elements(
    elements: list,
    edges: Optional[list] = None,
    direction: str = "TB",
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """批量创建元素和连接线

    接收 LLM 输出的 JSON 规划，一次性创建所有元素和连接。

    Args:
        elements: 元素规格列表，每项包含 {id, type, label, x, y, width, height, ...}
        edges: 边规格列表，每项包含 {from_id, to_id, label}
        direction: 布局方向 (TB/BT/LR/RL)
        context: Agent 上下文

    Returns:
        dict: 包含 status, created_elements, created_edges 的结果
    """
    if context is None:
        return {"status": "error", "message": "Context is required"}
    room_id = require_room_id(context)

    logger.debug("[batch_create] 获取房间文档: room_id=%s", room_id)
    doc, elements_array = await context.get_room_and_doc()
    if doc is None or elements_array is None:
        logger.error(
            "[batch_create] 获取房间文档失败: doc=%s, array=%s", doc, elements_array
        )
        return {"status": "error", "message": "Failed to get room doc"}

    logger.info(
        "[batch_create] 开始批量创建: elements=%d, edges=%d, array_len=%d",
        len(elements),
        len(edges) if edges else 0,
        len(elements_array),
    )

    edges = edges or []
    theme_colors: Dict[str, str] = get_theme_colors(context.theme)

    # 临时 ID 到真实 ID 的映射
    id_mapping: Dict[str, str] = {}
    created_elements: List[Dict[str, Any]] = []
    created_edges: List[Dict[str, Any]] = []
    all_elements: List[Dict[str, Any]] = []  # 收集所有创建的元素

    # 1. 创建所有形状和文本元素
    for spec in elements:
        shape, text_element, created_info = create_shape_and_text(
            spec, theme_colors, id_mapping
        )
        all_elements.append(shape)
        all_elements.append(text_element)
        created_elements.append(created_info)
        context.created_element_ids.append(created_info["element_id"])

    # 2. 创建所有连接线
    for edge in edges:
        result = create_arrow_between_nodes(
            edge, id_mapping, all_elements, theme_colors, direction
        )
        if result:
            arrow, edge_info = result
            all_elements.append(arrow)
            created_edges.append(edge_info)

    # 3. 根据模式决定存储位置
    if context.virtual_mode:
        # 虚拟模式：存入 virtual_elements
        context.virtual_elements.extend(all_elements)
        logger.info(
            "[batch_create] 虚拟模式: 已添加 %d 个元素到 virtual_elements",
            len(all_elements),
        )
        return {
            "status": "success",
            "message": f"已创建 {len(created_elements)} 个元素和 {len(created_edges)} 条连接 (虚拟模式)",
            "created_elements": created_elements,
            "created_edges": created_edges,
            "elements": all_elements,
        }

    # 非虚拟模式：写入画布
    with doc.transaction(origin="ai-engine/batch_create_elements"):
        for el in all_elements:
            append_element_as_ymap(elements_array, el)

    logger.info(
        "[batch_create] 事务完成, array_len=%d, created=%d elements + %d edges",
        len(elements_array),
        len(created_elements),
        len(created_edges),
    )

    return {
        "status": "success",
        "message": f"已创建 {len(created_elements)} 个元素和 {len(created_edges)} 条连接线",
        "created_elements": created_elements,
        "created_edges": created_edges,
        "id_mapping": id_mapping,
    }


@registry.register(
    "auto_layout_create",
    "自动布局创建图表 (无需指定坐标，自动计算最佳位置)",
    AutoLayoutCreateArgs,
    category=ToolCategory.CANVAS,
)
async def auto_layout_create(
    nodes: list,
    edges: Optional[list] = None,
    direction: str = "TB",
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """自动布局创建图表

    只需提供节点信息 (id, type, label) 和边信息，
    坐标由布局引擎自动计算。

    Args:
        nodes: 节点列表，每项包含 {id, type, label}
        edges: 边列表，每项包含 {from_id, to_id, label}
        direction: 布局方向 (TB/LR/BT/RL)
        context: Agent 上下文

    Returns:
        dict: 包含创建结果
    """
    if context is None:
        return {"status": "error", "message": "Context is required"}

    edges = edges or []

    structure = {
        "nodes": [
            {
                "id": n.get("id"),
                "type": n.get("type", "rectangle"),
                "label": n.get("label", ""),
            }
            for n in nodes
        ],
        "edges": [
            {
                "from_id": e.get("from_id"),
                "to_id": e.get("to_id"),
                "label": e.get("label", ""),
            }
            for e in edges
        ],
        "direction": direction,
    }

    layout_result = calculate_layout(structure, theme=context.theme)

    positioned_elements = [
        {
            "id": n["id"],
            "type": n["type"],
            "label": n["label"],
            "x": n["x"],
            "y": n["y"],
            "width": n["width"],
            "height": n["height"],
            "stroke_color": n.get("stroke_color"),
            "bg_color": n.get("bg_color"),
        }
        for n in layout_result.nodes
    ]

    positioned_edges = [
        {"from_id": e["from_id"], "to_id": e["to_id"], "label": e.get("label", "")}
        for e in layout_result.edges
    ]

    return await batch_create_elements(
        elements=positioned_elements,
        edges=positioned_edges,
        direction=direction,
        context=context,
    )


@registry.register(
    "group_elements",
    "将多个元素组合成一个组 (选中后一起移动)",
    GroupElementsArgs,
    category=ToolCategory.CANVAS,
)
async def group_elements(
    element_ids: List[str],
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """将多个元素组合成一个组

    组合后的元素在前端选中时会一起被选中、移动、缩放。

    Args:
        element_ids: 要组合的元素 ID 列表
        context: Agent 上下文

    Returns:
        Dict: 包含 group_id 和操作结果
    """
    if context is None:
        return {"status": "error", "message": "Context is required"}

    if len(element_ids) < 2:
        return {"status": "error", "message": "至少需要 2 个元素才能组合"}

    room_id: str = require_room_id(context)
    doc, elements_array = await context.get_room_and_doc()

    if doc is None or elements_array is None:
        return {"status": "error", "message": "Failed to get room doc"}

    # 生成新的组 ID
    group_id: str = generate_element_id("group")
    updated_count: int = 0

    with doc.transaction(origin="ai-engine/group_elements"):
        for i, el in enumerate(elements_array):
            if isinstance(el, Map):
                el_id = el.get("id")
                if el_id in element_ids:
                    # 获取现有的 groupIds 并添加新组 ID
                    current_groups = list(el.get("groupIds", []))
                    current_groups.append(group_id)
                    el["groupIds"] = current_groups
                    updated_count += 1

    if updated_count == 0:
        return {"status": "error", "message": "未找到指定的元素"}

    logger.info(
        "组合元素: group_id=%s, count=%d",
        group_id,
        updated_count,
        extra={"room": room_id},
    )

    return {
        "status": "success",
        "message": f"已将 {updated_count} 个元素组合",
        "group_id": group_id,
        "element_ids": element_ids,
    }


@registry.register(
    "ungroup_elements",
    "解除元素的组合 (取消组合后可以单独移动)",
    UngroupElementsArgs,
    category=ToolCategory.CANVAS,
)
async def ungroup_elements(
    element_ids: List[str],
    context: Optional[AgentContext] = None,
) -> Dict[str, Any]:
    """解除元素的组合

    清空指定元素的 groupIds，使其不再属于任何组。

    Args:
        element_ids: 要解除组合的元素 ID 列表
        context: Agent 上下文

    Returns:
        Dict: 操作结果
    """
    if context is None:
        return {"status": "error", "message": "Context is required"}

    room_id: str = require_room_id(context)
    doc, elements_array = await context.get_room_and_doc()

    if doc is None or elements_array is None:
        return {"status": "error", "message": "Failed to get room doc"}

    updated_count: int = 0

    with doc.transaction(origin="ai-engine/ungroup_elements"):
        for i, el in enumerate(elements_array):
            if isinstance(el, Map):
                el_id = el.get("id")
                if el_id in element_ids:
                    # 清空 groupIds
                    el["groupIds"] = []
                    updated_count += 1

    if updated_count == 0:
        return {"status": "error", "message": "未找到指定的元素"}

    logger.info(
        "解除组合: count=%d",
        updated_count,
        extra={"room": room_id},
    )

    return {
        "status": "success",
        "message": f"已解除 {updated_count} 个元素的组合",
        "element_ids": element_ids,
    }
