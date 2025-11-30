"""模块名称: ai
主要功能: AI 生成形状并注入白板的 API 路由
"""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pycrdt import Map

from src.ai.agent import ai_agent
from src.ws.sync import websocket_server
from src.logger import get_logger

router = APIRouter(prefix="/ai", tags=["AI"])
logger = get_logger(__name__)


class GenerateRequest(BaseModel):
    """AI 生成请求模型

    Attributes:
        prompt (str): 用户输入的提示词
        room_id (str): 目标房间 ID
    """

    prompt: str
    room_id: str


@router.post("/generate")
async def generate_shapes(request: GenerateRequest):
    """使用 AI 根据文本提示生成形状并注入到白板中。

    Args:
        request: AI 生成请求对象

    Returns:
        dict: 包含状态和生成形状数量的响应

    Raises:
        HTTPException: 生成或注入失败时抛出 500 错误
    """
    logger.info(
        "收到 AI 生成请求: %s 房间: %s", request.prompt, request.room_id
    )

    shapes = await ai_agent.generate_shapes(request.prompt)

    if not shapes:
        raise HTTPException(status_code=500, detail="生成形状失败")

    # 将形状注入到 CRDT 文档
    try:
        # 从 websocket_server 获取房间 (注意: get_room 是异步方法)
        room = await websocket_server.get_room(request.room_id)
        doc = room.ydoc
        shapes_map = doc.get("shapes", type=Map)

        with doc.transaction(origin="ai"):
            for shape in shapes:
                shape_id = str(uuid.uuid4())
                shapes_map[shape_id] = shape

    except Exception as e:
        logger.error("注入形状失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {"status": "success", "count": len(shapes)}
