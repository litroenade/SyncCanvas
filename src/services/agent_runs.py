"""模块名称: agent_runs
主要功能: Agent 运行生命周期管理与持久化

提供 Agent 运行记录的创建、更新、查询功能。
支持同步和异步调用方式。
"""

import time
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from src.db.models import AgentRun, AgentAction
from src.logger import get_logger

logger = get_logger(__name__)


class AgentRunService:
    """Agent 运行服务

    管理 Agent 运行的生命周期，包括创建、记录工具调用、完成/失败状态更新。
    提供同步方法，支持通过异步包装调用。

    Attributes:
        session: 数据库会话
    """

    def __init__(self, session: Session):
        """初始化服务

        Args:
            session: SQLModel 数据库会话
        """
        self.session = session

    def create_run(
        self,
        room_id: str,
        prompt: str,
        model: str = "",
        user_id: Optional[int] = None
    ) -> AgentRun:
        """创建新的 Agent 运行记录

        Args:
            room_id: 房间/会话 ID
            prompt: 用户输入的提示词
            model: 使用的模型名称
            user_id: 用户 ID (可选)

        Returns:
            AgentRun: 创建的运行记录
        """
        run = AgentRun(
            room_id=room_id,
            prompt=prompt,
            model=model,
            status="running",
            created_at=int(time.time() * 1000)
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)

        logger.info("Agent 运行已创建", extra={
            "run_id": run.id,
            "room_id": room_id,
            "model": model
        })
        return run

    async def create_run_async(
        self,
        room_id: str,
        prompt: str,
        model: str = "",
        user_id: Optional[int] = None
    ) -> AgentRun:
        """异步创建新的 Agent 运行记录

        Args:
            room_id: 房间/会话 ID
            prompt: 用户输入的提示词
            model: 使用的模型名称
            user_id: 用户 ID (可选)

        Returns:
            AgentRun: 创建的运行记录
        """
        return self.create_run(room_id, prompt, model, user_id)

    def log_action(
        self,
        run_id: int,
        tool: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any]
    ) -> AgentAction:
        """记录工具调用

        Args:
            run_id: 运行记录 ID
            tool: 工具名称
            arguments: 调用参数
            result: 执行结果

        Returns:
            AgentAction: 创建的动作记录
        """
        action = AgentAction(
            run_id=run_id,
            tool=tool,
            arguments=arguments or {},
            result=result or {},
            created_at=int(time.time() * 1000)
        )
        self.session.add(action)
        self.session.commit()
        self.session.refresh(action)

        logger.debug("Agent 动作已记录", extra={
            "run_id": run_id,
            "tool": tool
        })
        return action

    async def log_action_async(
        self,
        run_id: int,
        tool: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any]
    ) -> AgentAction:
        """异步记录工具调用

        Args:
            run_id: 运行记录 ID
            tool: 工具名称
            arguments: 调用参数
            result: 执行结果

        Returns:
            AgentAction: 创建的动作记录
        """
        return self.log_action(run_id, tool, arguments, result)

    def complete_run(
        self,
        run_id: int,
        message: str = "",
        output: Optional[str] = None
    ) -> AgentRun:
        """标记运行为完成状态

        Args:
            run_id: 运行记录 ID
            message: 完成消息
            output: 输出内容

        Returns:
            AgentRun: 更新后的运行记录
        """
        run = self.session.get(AgentRun, run_id)
        if not run:
            raise ValueError(f"运行记录 {run_id} 不存在")

        run.status = "completed"
        run.message = message or output or ""
        run.finished_at = int(time.time() * 1000)

        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)

        logger.info("Agent 运行已完成", extra={
            "run_id": run_id,
            "status": "completed"
        })
        return run

    async def complete_run_async(
        self,
        run_id: int,
        message: str = "",
        output: Optional[str] = None
    ) -> AgentRun:
        """异步标记运行为完成状态

        Args:
            run_id: 运行记录 ID
            message: 完成消息
            output: 输出内容

        Returns:
            AgentRun: 更新后的运行记录
        """
        return self.complete_run(run_id, message, output)

    def fail_run(
        self,
        run_id: int,
        error: str = ""
    ) -> AgentRun:
        """标记运行为失败状态

        Args:
            run_id: 运行记录 ID
            error: 错误信息

        Returns:
            AgentRun: 更新后的运行记录
        """
        run = self.session.get(AgentRun, run_id)
        if not run:
            raise ValueError(f"运行记录 {run_id} 不存在")

        run.status = "failed"
        run.message = error
        run.finished_at = int(time.time() * 1000)

        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)

        logger.error("Agent 运行失败", extra={
            "run_id": run_id,
            "error": error
        })
        return run

    async def fail_run_async(
        self,
        run_id: int,
        error: str = ""
    ) -> AgentRun:
        """异步标记运行为失败状态

        Args:
            run_id: 运行记录 ID
            error: 错误信息

        Returns:
            AgentRun: 更新后的运行记录
        """
        return self.fail_run(run_id, error)

    def get_run(self, run_id: int) -> Optional[AgentRun]:
        """获取运行记录

        Args:
            run_id: 运行记录 ID

        Returns:
            AgentRun: 运行记录，不存在则返回 None
        """
        return self.session.get(AgentRun, run_id)

    def get_run_actions(self, run_id: int) -> List[AgentAction]:
        """获取运行的所有动作记录

        Args:
            run_id: 运行记录 ID

        Returns:
            List[AgentAction]: 动作记录列表
        """
        statement = (
            select(AgentAction)
            .where(AgentAction.run_id == run_id)
            .order_by(AgentAction.created_at)
        )
        return list(self.session.exec(statement).all())

    def get_run_detail(self, run_id: int) -> Optional[Dict[str, Any]]:
        """获取运行详情，包含所有动作

        Args:
            run_id: 运行记录 ID

        Returns:
            dict: 运行详情字典，不存在则返回 None
        """
        run = self.get_run(run_id)
        if not run:
            return None

        actions = self.get_run_actions(run_id)

        return {
            "id": run.id,
            "room_id": run.room_id,
            "prompt": run.prompt,
            "model": run.model,
            "status": run.status,
            "message": run.message,
            "created_at": run.created_at,
            "finished_at": run.finished_at,
            "actions": [
                {
                    "id": action.id,
                    "tool": action.tool,
                    "arguments": action.arguments,
                    "result": action.result,
                    "created_at": action.created_at,
                }
                for action in actions
            ],
        }

    def get_room_runs(
        self,
        room_id: str,
        limit: int = 20
    ) -> List[AgentRun]:
        """获取房间的运行历史

        Args:
            room_id: 房间 ID
            limit: 返回数量限制

        Returns:
            List[AgentRun]: 运行记录列表
        """
        statement = (
            select(AgentRun)
            .where(AgentRun.room_id == room_id)
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
        )
        return list(self.session.exec(statement).all())
