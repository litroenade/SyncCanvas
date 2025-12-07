"""模块名称: ai
主要功能: AI 生成形状并注入白板的 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from src.db.database import get_session
from src.logger import get_logger
from src.services.ai_service import ai_service
from src.services.agent_runs import AgentRunService

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
async def generate_shapes(request: GenerateRequest, session: Session = Depends(get_session)):
    """使用 AI 根据文本提示生成形状并注入到白板中。

    Args:
        request: AI 生成请求对象

    Returns:
        dict: 包含状态、工具调用结果的响应

    Raises:
        HTTPException: 生成或注入失败时抛出 500 错误
    """
    logger.info("收到 AI 生成请求", extra={"room": request.room_id})

    try:
        # Use the new AI Service
        response = await ai_service.process_request(
            user_input=request.prompt,
            session_id=request.room_id,
            db=session
        )
        
        return {
            "status": "success",
            "message": "AI processing completed",
            "response": response
        }

    except Exception as e:
        logger.error(f"AI 生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/{run_id}")
async def get_run_detail(run_id: int, session: Session = Depends(get_session)):
    """查询指定 agent 运行的详情与工具调用记录。"""

    service = AgentRunService(session)
    detail = service.get_run_detail(run_id)
    if not detail:
        raise HTTPException(status_code=404, detail="run_not_found")
    return {"status": "ok", "data": detail}
