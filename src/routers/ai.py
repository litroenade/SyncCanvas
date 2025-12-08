"""模块名称: ai
主要功能: AI Agent API 路由

提供 AI Agent 的 HTTP API 接口，包括:
- 生成/绘图请求
- 运行历史查询
- 运行详情查询
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from src.db.database import get_session
from src.logger import get_logger
from src.services.ai_service import ai_service
from src.services.agent_runs import AgentRunService

router = APIRouter(prefix="/ai", tags=["AI"])
logger = get_logger(__name__)


# ==================== 请求/响应模型 ====================

class GenerateRequest(BaseModel):
    """AI 生成请求模型

    Attributes:
        prompt: 用户输入的提示词
        room_id: 目标房间 ID
    """
    prompt: str = Field(..., description="用户输入的提示词", min_length=1, max_length=2000)
    room_id: str = Field(..., description="目标房间 ID")


class GenerateResponse(BaseModel):
    """AI 生成响应模型

    Attributes:
        status: 请求状态 (success/error)
        response: AI 响应文本
        run_id: 运行记录 ID
        elements_created: 创建的元素 ID 列表
        tools_used: 使用的工具列表
    """
    status: str
    response: str
    run_id: int
    elements_created: list = []
    tools_used: list = []


class RunHistoryRequest(BaseModel):
    """运行历史查询请求

    Attributes:
        room_id: 房间 ID
        limit: 返回数量限制
    """
    room_id: str = Field(..., description="房间 ID")
    limit: int = Field(20, description="返回数量限制", ge=1, le=100)


# ==================== API 路由 ====================

@router.post("/generate", response_model=GenerateResponse)
async def generate_shapes(
    request: GenerateRequest,
    session: Session = Depends(get_session)
):
    """使用 AI Agent 根据用户描述在白板上绘制图形

    支持:
    - 流程图绘制
    - 数据流图绘制
    - 架构图绘制
    - 一般的图形创建

    Args:
        request: AI 生成请求对象
        session: 数据库会话

    Returns:
        GenerateResponse: AI 处理结果

    Raises:
        HTTPException: 处理失败时抛出 500 错误
    """
    logger.info("收到 AI 生成请求", extra={
        "room_id": request.room_id,
        "prompt_length": len(request.prompt)
    })

    try:
        result = await ai_service.process_request(
            user_input=request.prompt,
            session_id=request.room_id,
            db=session
        )

        return GenerateResponse(
            status=result.get("status", "success"),
            response=result.get("response", ""),
            run_id=result.get("run_id", 0),
            elements_created=result.get("elements_created", []),
            tools_used=result.get("tools_used", [])
        )

    except Exception as e:
        logger.error(f"AI 生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/{room_id}")
async def get_room_runs(
    room_id: str,
    limit: int = 20,
    session: Session = Depends(get_session)
):
    """获取房间的 AI 运行历史

    Args:
        room_id: 房间 ID
        limit: 返回数量限制
        session: 数据库会话

    Returns:
        dict: 运行历史列表
    """
    result = await ai_service.get_run_history(
        session_id=room_id,
        db=session,
        limit=limit
    )
    return result


@router.get("/run/{run_id}")
async def get_run_detail(
    run_id: int,
    session: Session = Depends(get_session)
):
    """获取指定运行的详情

    包含运行的所有工具调用记录。

    Args:
        run_id: 运行记录 ID
        session: 数据库会话

    Returns:
        dict: 运行详情

    Raises:
        HTTPException: 运行记录不存在时抛出 404 错误
    """
    result = await ai_service.get_run_detail(run_id, session)

    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message", "run_not_found"))

    return result
