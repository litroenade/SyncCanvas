"""模块名称: sequence
主要功能: 时序图工具

提供时序图创建功能:
- create_sequence_participant: 创建参与者
- create_sequence_message: 创建消息
- create_sequence_diagram: 一键生成完整时序图
"""

import random
from typing import Dict, Any, List

from pydantic import BaseModel, Field

from src.agent.core.agent import AgentContext
from src.agent.core.tools import registry, ToolCategory
from src.agent.tools.helpers import (
    require_room_id,
    generate_element_id,
    get_room_and_doc,
    element_to_ymap,
)
from src.logger import get_logger

logger = get_logger(__name__)


# 时序图布局常量
PARTICIPANT_WIDTH: int = 120
PARTICIPANT_HEIGHT: int = 40
PARTICIPANT_GAP: int = 180  # 参与者之间的水平间距
LIFELINE_LENGTH: int = 400  # 生命线长度
MESSAGE_GAP: int = 60  # 消息之间的垂直间距


class CreateParticipantArgs(BaseModel):
    """创建参与者参数"""

    name: str = Field(..., description="参与者名称")
    x: float = Field(100, description="X 坐标")
    y: float = Field(50, description="Y 坐标")


class CreateSequenceMessageArgs(BaseModel):
    """创建消息参数"""

    from_participant_id: str = Field(..., description="发送方参与者 ID")
    to_participant_id: str = Field(..., description="接收方参与者 ID")
    message: str = Field(..., description="消息内容")
    y_offset: float = Field(100, description="消息在生命线上的Y偏移量")
    is_return: bool = Field(False, description="是否为返回消息(虚线)")


class CreateSequenceDiagramArgs(BaseModel):
    """创建时序图参数"""

    participants: List[str] = Field(..., description="参与者名称列表")
    messages: List[Dict[str, Any]] = Field(
        ...,
        description="消息列表，每项包含 from_index, to_index, message, is_return"
    )
    start_x: float = Field(100, description="起始 X 坐标")
    start_y: float = Field(50, description="起始 Y 坐标")


def _create_participant_elements(
    name: str,
    x: float,
    y: float,
) -> List[Dict[str, Any]]:
    """创建参与者元素 (矩形 + 文本 + 生命线)

    Args:
        name: 参与者名称
        x: X 坐标
        y: Y 坐标

    Returns:
        元素列表
    """
    elements = []

    # 参与者矩形
    rect_id = generate_element_id("rect")
    rect = {
        "id": rect_id,
        "type": "rectangle",
        "x": x,
        "y": y,
        "width": PARTICIPANT_WIDTH,
        "height": PARTICIPANT_HEIGHT,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "#e3f2fd",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "seed": random.randint(1, 100000),
        "version": 1,
        "versionNonce": random.randint(1, 1000000000),
        "isDeleted": False,
        "boundElements": [],
        "updated": 1,
        "link": None,
        "locked": False,
        "roundness": {"type": 3},
    }
    elements.append(rect)

    # 参与者文本
    text_id = generate_element_id("text")
    text = {
        "id": text_id,
        "type": "text",
        "x": x + PARTICIPANT_WIDTH / 2,
        "y": y + PARTICIPANT_HEIGHT / 2,
        "width": PARTICIPANT_WIDTH - 10,
        "height": 20,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "seed": random.randint(1, 100000),
        "version": 1,
        "versionNonce": random.randint(1, 1000000000),
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "text": name,
        "fontSize": 16,
        "fontFamily": 1,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": rect_id,
        "originalText": name,
        "autoResize": True,
    }
    rect["boundElements"].append({"id": text_id, "type": "text"})
    elements.append(text)

    # 生命线 (虚线)
    line_id = generate_element_id("line")
    line_start_y = y + PARTICIPANT_HEIGHT
    line = {
        "id": line_id,
        "type": "line",
        "x": x + PARTICIPANT_WIDTH / 2,
        "y": line_start_y,
        "width": 0,
        "height": LIFELINE_LENGTH,
        "strokeColor": "#868e96",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "dashed",
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "seed": random.randint(1, 100000),
        "version": 1,
        "versionNonce": random.randint(1, 1000000000),
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "points": [[0, 0], [0, LIFELINE_LENGTH]],
        "lastCommittedPoint": None,
        "startBinding": None,
        "endBinding": None,
        "startArrowhead": None,
        "endArrowhead": None,
    }
    elements.append(line)

    return elements, rect_id, line_id


def _create_message_elements(
    from_x: float,
    to_x: float,
    y: float,
    message: str,
    is_return: bool = False,
) -> List[Dict[str, Any]]:
    """创建消息元素 (箭头 + 文本)

    Args:
        from_x: 起始 X 坐标
        to_x: 结束 X 坐标
        y: Y 坐标
        message: 消息内容
        is_return: 是否为返回消息

    Returns:
        元素列表
    """
    elements = []

    # 消息箭头
    arrow_id = generate_element_id("arrow")
    arrow = {
        "id": arrow_id,
        "type": "arrow",
        "x": from_x,
        "y": y,
        "width": abs(to_x - from_x),
        "height": 0,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "dashed" if is_return else "solid",
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "seed": random.randint(1, 100000),
        "version": 1,
        "versionNonce": random.randint(1, 1000000000),
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "points": [[0, 0], [to_x - from_x, 0]],
        "lastCommittedPoint": None,
        "startBinding": None,
        "endBinding": None,
        "startArrowhead": None,
        "endArrowhead": "arrow",
    }
    elements.append(arrow)

    # 消息文本
    text_id = generate_element_id("text")
    mid_x = (from_x + to_x) / 2
    text = {
        "id": text_id,
        "type": "text",
        "x": mid_x - 40,
        "y": y - 20,
        "width": 80,
        "height": 16,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "seed": random.randint(1, 100000),
        "version": 1,
        "versionNonce": random.randint(1, 1000000000),
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "text": message,
        "fontSize": 14,
        "fontFamily": 1,
        "textAlign": "center",
        "verticalAlign": "middle",
        "originalText": message,
    }
    elements.append(text)

    return elements


@registry.register(
    "create_sequence_participant",
    "创建时序图参与者 (包含矩形、名称文本和生命线)",
    CreateParticipantArgs,
    category=ToolCategory.CANVAS,
)
async def create_sequence_participant(
    name: str,
    x: float = 100,
    y: float = 50,
    context: AgentContext = None,
) -> Dict[str, Any]:
    """创建时序图参与者

    Args:
        name: 参与者名称
        x: X 坐标
        y: Y 坐标
        context: Agent 上下文

    Returns:
        dict: 包含 status, participant_id, lifeline_id 的结果
    """
    room_id = require_room_id(context)
    _, doc, elements_array = await get_room_and_doc(room_id)

    elements, rect_id, line_id = _create_participant_elements(name, x, y)

    with doc.transaction(origin="ai-engine/create_sequence_participant"):
        for el in elements:
            elements_array.append(element_to_ymap(el))

    logger.info("创建时序图参与者: %s", name, extra={"room": room_id})

    return {
        "status": "success",
        "message": f"已创建参与者: {name}",
        "participant_id": rect_id,
        "lifeline_id": line_id,
        "center_x": x + PARTICIPANT_WIDTH / 2,
    }


@registry.register(
    "create_sequence_diagram",
    "一键创建完整时序图，包含参与者和消息",
    CreateSequenceDiagramArgs,
    category=ToolCategory.CANVAS,
)
async def create_sequence_diagram(
    participants: List[str],
    messages: List[Dict[str, Any]],
    start_x: float = 100,
    start_y: float = 50,
    context: AgentContext = None,
) -> Dict[str, Any]:
    """一键创建完整时序图

    Args:
        participants: 参与者名称列表
        messages: 消息列表，每项包含 from_index, to_index, message, is_return
        start_x: 起始 X 坐标
        start_y: 起始 Y 坐标
        context: Agent 上下文

    Returns:
        dict: 包含 status, participant_count, message_count 的结果
    """
    room_id = require_room_id(context)
    _, doc, elements_array = await get_room_and_doc(room_id)

    all_elements: List[Dict] = []
    participant_centers: List[float] = []

    # 创建参与者
    for i, name in enumerate(participants):
        x = start_x + i * PARTICIPANT_GAP
        elements, _, _ = _create_participant_elements(name, x, start_y)
        all_elements.extend(elements)
        participant_centers.append(x + PARTICIPANT_WIDTH / 2)

    # 创建消息
    message_y = start_y + PARTICIPANT_HEIGHT + MESSAGE_GAP
    for msg in messages:
        from_idx = msg.get("from_index", 0)
        to_idx = msg.get("to_index", 1)
        text = msg.get("message", "")
        is_return = msg.get("is_return", False)

        if from_idx < len(participant_centers) and to_idx < len(participant_centers):
            from_x = participant_centers[from_idx]
            to_x = participant_centers[to_idx]
            msg_elements = _create_message_elements(from_x, to_x, message_y, text, is_return)
            all_elements.extend(msg_elements)
            message_y += MESSAGE_GAP

    # 写入画布
    with doc.transaction(origin="ai-engine/create_sequence_diagram"):
        for el in all_elements:
            elements_array.append(element_to_ymap(el))

    logger.info(
        "创建时序图: %d 个参与者, %d 条消息",
        len(participants),
        len(messages),
        extra={"room": room_id},
    )

    return {
        "status": "success",
        "message": f"已创建时序图: {len(participants)} 个参与者, {len(messages)} 条消息",
        "participant_count": len(participants),
        "message_count": len(messages),
        "element_count": len(all_elements),
    }
