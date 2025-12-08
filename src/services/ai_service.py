"""模块名称: ai_service
主要功能: AI 服务层

提供高级 AI 功能接口，初始化 Agent 并路由请求。
"""

from typing import Optional, Dict, Any

from sqlmodel import Session

from src.ai_engine.agents.teacher import TeacherAgent
from src.ai_engine.core.agent import AgentContext
from src.ai_engine.core.llm import LLMClient
from src.services.agent_runs import AgentRunService
from src.logger import get_logger

logger = get_logger(__name__)


class AIService:
    """AI 服务

    高级 AI 功能服务，管理 Agent 生命周期并处理请求。

    Attributes:
        llm_client: LLM 客户端实例
    """

    def __init__(self):
        """初始化 AI 服务"""
        self.llm_client = LLMClient()
        logger.info("AI 服务已初始化")

    async def process_request(
        self,
        user_input: str,
        session_id: str,
        db: Session,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """处理用户 AI 请求

        通过 Teacher Agent 处理用户请求，支持对话和绘图。

        Args:
            user_input: 用户输入文本
            session_id: 会话/房间 ID
            db: 数据库会话
            user_id: 用户 ID (可选)

        Returns:
            dict: 包含 response, run_id, status 的结果
        """
        run_service = AgentRunService(db)

        # 创建运行记录
        run = run_service.create_run(
            room_id=session_id,
            prompt=user_input,
            model=self.llm_client._primary_config.model
        )

        # 初始化上下文
        context = AgentContext(
            run_id=run.id,
            session_id=session_id,
            user_id=user_id
        )

        # 初始化 Teacher Agent
        teacher = TeacherAgent(self.llm_client, run_service)

        try:
            # 执行 Agent
            response = await teacher.run(context, user_input)

            # 更新运行状态
            run_service.complete_run(run.id, message=response)

            logger.info("AI 请求处理完成", extra={
                "run_id": run.id,
                "session_id": session_id,
                "tools_called": len(context.tool_results),
                "elements_created": len(context.created_element_ids)
            })

            return {
                "status": "success",
                "response": response,
                "run_id": run.id,
                "elements_created": context.created_element_ids,
                "tools_used": [r["tool"] for r in context.tool_results]
            }

        except Exception as e:
            error_msg = str(e)
            run_service.fail_run(run.id, error=error_msg)

            logger.error("AI 请求处理失败", extra={
                "run_id": run.id,
                "session_id": session_id,
                "error": error_msg
            })

            return {
                "status": "error",
                "response": f"处理请求时发生错误: {error_msg}",
                "run_id": run.id,
                "elements_created": [],
                "tools_used": []
            }

    async def get_run_history(
        self,
        session_id: str,
        db: Session,
        limit: int = 20
    ) -> Dict[str, Any]:
        """获取会话的 AI 运行历史

        Args:
            session_id: 会话/房间 ID
            db: 数据库会话
            limit: 返回数量限制

        Returns:
            dict: 包含运行历史列表
        """
        run_service = AgentRunService(db)
        runs = run_service.get_room_runs(session_id, limit)

        return {
            "status": "success",
            "runs": [
                {
                    "id": run.id,
                    "prompt": run.prompt[:100] + "..." if len(run.prompt) > 100 else run.prompt,
                    "status": run.status,
                    "created_at": run.created_at,
                    "finished_at": run.finished_at,
                }
                for run in runs
            ]
        }

    async def get_run_detail(
        self,
        run_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """获取运行详情

        Args:
            run_id: 运行记录 ID
            db: 数据库会话

        Returns:
            dict: 运行详情
        """
        run_service = AgentRunService(db)
        detail = run_service.get_run_detail(run_id)

        if not detail:
            return {
                "status": "error",
                "message": f"运行记录 {run_id} 不存在"
            }

        return {
            "status": "success",
            "run": detail
        }


# 全局实例
ai_service = AIService()
