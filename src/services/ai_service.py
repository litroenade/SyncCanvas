from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
import asyncio
import time
from sqlmodel import Session
from src.agent.core import CanvasAgent
from src.agent.core import AgentContext, RoomLockManager
from src.agent.core import LLMClient
from src.agent.core import registry
from src.agent.core.runs import AgentRunService
from src.logger import get_logger
from src.db.database import get_sync_session
from src.db.database import engine

logger = get_logger(__name__)


@dataclass
class ServiceStats:
    """服务统计信息"""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tool_calls: int = 0
    total_elements_created: int = 0
    avg_response_time_ms: float = 0.0
    _response_times: List[float] = field(default_factory=list)

    def record_request(
        self, success: bool, duration_ms: float, tool_calls: int, elements: int
    ):
        """记录请求"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        self.total_tool_calls += tool_calls
        self.total_elements_created += elements

        # 保留最近 100 个响应时间计算平均值
        self._response_times.append(duration_ms)
        if len(self._response_times) > 100:
            self._response_times.pop(0)

        if self._response_times:
            self.avg_response_time_ms = sum(self._response_times) / len(
                self._response_times
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round(
                self.successful_requests / max(1, self.total_requests) * 100, 1
            ),
            "total_tool_calls": self.total_tool_calls,
            "total_elements_created": self.total_elements_created,
            "avg_response_time_ms": round(self.avg_response_time_ms, 2),
        }


class AIService:
    """AI 服务

    高级 AI 功能服务，管理 Agent 生命周期并处理请求。

    Features:
    - 请求处理和路由
    - 运行历史查询
    - 服务状态监控
    - 工具管理
    """

    def __init__(self):
        """初始化 AI 服务"""
        self.llm_client = LLMClient()
        self._stats = ServiceStats()
        self._active_contexts: Dict[int, AgentContext] = {}  # run_id -> context
        logger.info("AI 服务已初始化")

    @property
    def stats(self) -> ServiceStats:
        """获取服务统计"""
        return self._stats

    async def _save_memory_safe(
        self,
        room_id: str,
        role: str,
        content: str,
    ) -> None:
        """安全保存消息到房间记忆

        带错误处理，失败不影响主流程。

        Args:
            room_id: 房间 ID
            role: 消息角色 (user | assistant)
            content: 消息内容
        """
        if not content or not content.strip():
            return  # 空内容不保存

        try:
            from src.agent.memory import memory_service

            # 截断过长内容
            safe_content = content[:4000] if len(content) > 4000 else content
            await memory_service.save_message(room_id, role, safe_content)
        except Exception as e:  # pylint: disable=broad-except
            logger.warning("保存记忆失败 (room=%s, role=%s): %s", room_id, role, e)

    async def process_request(
        self,
        user_input: str,
        session_id: str,
        db: Session,
        user_id: Optional[str] = None,
        theme: str = "light",
    ) -> Dict[str, Any]:
        """处理用户 AI 请求

        通过 Teacher Agent 处理用户请求，支持对话和绘图。

        Args:
            user_input: 用户输入文本
            session_id: 会话/房间 ID
            db: 数据库会话
            user_id: 用户 ID (可选)
            theme: 画布主题 ("light" | "dark")

        Returns:
            dict: 包含 response, run_id, status, metrics 的结果
        """

        start_time = time.time()

        run_service = AgentRunService(db)

        # 创建运行记录
        run = run_service.create_run(
            room_id=session_id,
            prompt=user_input,
            model=self.llm_client.current_config.model,
        )
        assert run.id is not None, "Run ID should be set after creation"

        # 初始化上下文
        context = AgentContext(
            run_id=run.id, session_id=session_id, user_id=user_id, theme=theme
        )

        # 追踪活跃上下文
        self._active_contexts[run.id] = context

        # 初始化 Planner Agent
        agent = CanvasAgent(self.llm_client, run_service)

        try:
            # 执行 Agent
            response = await agent.run(context, user_input)

            # 计算耗时
            duration_ms = (time.time() - start_time) * 1000

            # 更新运行状态
            run_service.complete_run(run.id, message=response)

            # 记录统计
            self._stats.record_request(
                success=True,
                duration_ms=duration_ms,
                tool_calls=len(context.tool_results),
                elements=len(context.created_element_ids),
            )

            logger.info(
                "AI 请求处理完成",
                extra={
                    "run_id": run.id,
                    "session_id": session_id,
                    "duration_ms": round(duration_ms, 2),
                    "tools_called": len(context.tool_results),
                    "elements_created": len(context.created_element_ids),
                },
            )

            return {
                "status": "success",
                "response": response,
                "run_id": run.id,
                "elements_created": context.created_element_ids,
                "tools_used": [r["tool"] for r in context.tool_results],
                "metrics": {
                    "duration_ms": round(duration_ms, 2),
                    "iterations": len(agent.steps),
                    **agent.metrics.to_dict(),
                },
            }

        except Exception as e:  # pylint: disable=broad-except
            error_msg = str(e)
            duration_ms = (time.time() - start_time) * 1000

            run_service.fail_run(run.id, error=error_msg)

            # 记录统计
            self._stats.record_request(
                success=False,
                duration_ms=duration_ms,
                tool_calls=len(context.tool_results),
                elements=len(context.created_element_ids),
            )

            logger.error(
                "AI 请求处理失败",
                extra={"run_id": run.id, "session_id": session_id, "error": error_msg},
            )

            return {
                "status": "error",
                "response": f"处理请求时发生错误: {error_msg}",
                "run_id": run.id,
                "elements_created": context.created_element_ids,
                "tools_used": [r["tool"] for r in context.tool_results],
                "metrics": {"duration_ms": round(duration_ms, 2)},
            }
        finally:
            # 清理上下文
            self._active_contexts.pop(run.id, None)

    async def cancel_request(self, run_id: int) -> Dict[str, Any]:
        """取消正在进行的请求

        Args:
            run_id: 运行记录 ID

        Returns:
            dict: 操作结果
        """
        context = self._active_contexts.get(run_id)
        if not context:
            return {"status": "error", "message": f"运行 {run_id} 不存在或已完成"}

        context.cancel()
        logger.info(f"取消请求: run_id={run_id}")

        return {"status": "success", "message": f"已发送取消信号给运行 {run_id}"}

    async def process_request_with_stream(
        self,
        user_input: str,
        session_id: str,
        step_callback: Optional[Callable] = None,
        user_id: Optional[str] = None,
        theme: str = "light",
        virtual_mode: bool = False,
    ) -> Dict[str, Any]:
        """处理用户 AI 请求 (支持流式步骤回调)

        与 process_request 类似，但支持每个步骤的实时回调。

        Args:
            user_input: 用户输入文本
            session_id: 会话/房间 ID
            step_callback: 步骤回调函数，接收 ReActStep 参数
            user_id: 用户 ID (可选)
            theme: 画布主题 ("light" | "dark")
            virtual_mode: 虚拟模式 - 工具调用不写入 Yjs，而是返回元素数据

        Returns:
            dict: 包含 response, run_id, status, metrics 的结果
                  虚拟模式下额外包含 virtual_elements
        """

        start_time = time.time()

        # 使用同步会话创建运行记录
        with get_sync_session() as db:
            run_service = AgentRunService(db)

            run = run_service.create_run(
                room_id=session_id,
                prompt=user_input,
                model=self.llm_client.current_config.model,
            )
            run_id = run.id
        assert run_id is not None, "Run ID should be set after creation"

        # 初始化上下文 - 支持虚拟模式
        context = AgentContext(
            run_id=run_id,
            session_id=session_id,
            user_id=user_id,
            theme=theme,
            virtual_mode=virtual_mode,
        )

        self._active_contexts[run_id] = context

        # 创建持久的 run_service 用于记录工具调用
        # 注：使用新的会话实例确保线程安全

        stream_session = Session(engine)
        stream_run_service = AgentRunService(stream_session)

        # 初始化 Canvas Agent (传递 run_service 以记录工具调用)
        agent = CanvasAgent(self.llm_client, stream_run_service)

        # 设置步骤回调
        if step_callback:

            async def async_callback(step):
                try:
                    result = step_callback(step)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:  # pylint: disable=broad-except
                    logger.warning(f"步骤回调失败: {e}")

            agent.set_step_callback(async_callback)  # type: ignore[arg-type]

        try:
            await self._save_memory_safe(session_id, "user", user_input)

            response = await agent.run(context, user_input)
            duration_ms = (time.time() - start_time) * 1000

            await self._save_memory_safe(session_id, "assistant", response)

            # 更新运行状态
            with get_sync_session() as db:
                run_service = AgentRunService(db)
                run_service.complete_run(run_id, message=response)

            self._stats.record_request(
                success=True,
                duration_ms=duration_ms,
                tool_calls=len(context.tool_results),
                elements=len(context.created_element_ids),
            )

            logger.info(
                "AI 流式请求处理完成",
                extra={
                    "run_id": run_id,
                    "session_id": session_id,
                    "duration_ms": round(duration_ms, 2),
                    "tools_called": len(context.tool_results),
                    "elements_created": len(context.created_element_ids),
                },
            )

            result = {
                "status": "success",
                "response": response,
                "run_id": run_id,
                "elements_created": context.created_element_ids,
                "tools_used": [r["tool"] for r in context.tool_results],
                "metrics": {
                    "duration_ms": round(duration_ms, 2),
                    "iterations": len(agent.steps),
                    **agent.metrics.to_dict(),
                },
            }
            # 虚拟模式：返回元素数据
            if virtual_mode:
                result["virtual_elements"] = context.virtual_elements
            return result

        except Exception as e:  # pylint: disable=broad-except
            error_msg = str(e)
            duration_ms = (time.time() - start_time) * 1000

            with get_sync_session() as db:
                run_service = AgentRunService(db)
                run_service.fail_run(run_id, error=error_msg)

            self._stats.record_request(
                success=False,
                duration_ms=duration_ms,
                tool_calls=len(context.tool_results),
                elements=len(context.created_element_ids),
            )

            logger.error(
                "AI 流式请求处理失败",
                extra={"run_id": run_id, "session_id": session_id, "error": error_msg},
            )

            return {
                "status": "error",
                "response": f"处理请求时发生错误: {error_msg}",
                "run_id": run_id,
                "elements_created": context.created_element_ids,
                "tools_used": [r["tool"] for r in context.tool_results],
                "metrics": {"duration_ms": round(duration_ms, 2)},
            }
        finally:
            # 关闭流式会话
            stream_session.close()
            self._active_contexts.pop(run_id, None)

    async def get_run_history(
        self, session_id: str, db: Session, limit: int = 20
    ) -> Dict[str, Any]:
        """获取会话的 AI 运行历史"""
        run_service = AgentRunService(db)
        runs = run_service.get_room_runs(session_id, limit)

        return {
            "status": "success",
            "runs": [
                {
                    "id": run.id,
                    "prompt": run.prompt[:100] + "..."
                    if len(run.prompt) > 100
                    else run.prompt,
                    "status": run.status,
                    "created_at": run.created_at,
                    "finished_at": run.finished_at,
                }
                for run in runs
            ],
        }

    async def get_run_detail(self, run_id: int, db: Session) -> Dict[str, Any]:
        """获取运行详情"""
        run_service = AgentRunService(db)
        detail = run_service.get_run_detail(run_id)

        if not detail:
            return {"status": "error", "message": f"运行记录 {run_id} 不存在"}

        return {"status": "success", "run": detail}

    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态

        Returns:
            dict: 服务状态信息
        """
        # 获取可用工具
        tools = registry.list_tools()

        return {
            "status": "healthy",
            "llm": {
                "provider": self.llm_client.current_config.provider,
                "model": self.llm_client.current_config.model,
            },
            "stats": self._stats.to_dict(),
            "active_requests": len(self._active_contexts),
            "busy_rooms": list(RoomLockManager._active_rooms),
            "tools": {
                "total": len(tools),
                "enabled": len([t for t in tools if t["enabled"]]),
                "by_category": self._count_tools_by_category(tools),
            },
        }

    def _count_tools_by_category(self, tools: List[Dict]) -> Dict[str, int]:
        """按分类统计工具数量"""
        counts: Dict[str, int] = {}
        for tool in tools:
            cat = tool.get("category", "general")
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有可用工具

        Returns:
            list: 工具列表
        """
        return registry.list_tools()

    def disable_tool(self, name: str) -> Dict[str, Any]:
        """禁用工具

        Args:
            name: 工具名称

        Returns:
            dict: 操作结果
        """
        if registry.get_tool(name) is None:
            return {"status": "error", "message": f"工具 {name} 不存在"}

        registry.disable_tool(name)
        return {"status": "success", "message": f"已禁用工具 {name}"}

    def enable_tool(self, name: str) -> Dict[str, Any]:
        """启用工具

        Args:
            name: 工具名称

        Returns:
            dict: 操作结果
        """
        registry.enable_tool(name)
        return {"status": "success", "message": f"已启用工具 {name}"}


# 全局实例
ai_service = AIService()
