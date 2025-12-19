"""模块名称: executor
主要功能: Agent Pipeline 执行器
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from src.agent.pipeline.cognition import GraphCognition, CanvasState, get_cognition
from src.agent.canvas import CanvasModel
from src.agent.pipeline.router import LLMRouter, Task, get_router
from src.agent.pipeline.reasoning import (
    CanvasReasoner,
    LogicalOp,
    ReasoningResult,
    ReasoningMode,
)
from src.agent.canvas.commands import Command, CommandExecutor, CommandResult
from src.agent.pipeline.layout import LayoutEngine, PositionedOp, get_layout_engine
from src.agent.pipeline.transaction import (
    SemanticTransaction,
    TransactionResult,
    get_transaction,
)

from src.logger import get_logger


if TYPE_CHECKING:
    from src.agent.base import AgentContext
    from src.agent.llm import LLMClient

logger = get_logger(__name__)

@dataclass
class PipelineMetrics:
    """Pipeline 执行指标"""

    start_time: float = 0.0
    end_time: float = 0.0

    # 各阶段耗时 (ms)
    hydration_ms: float = 0.0
    routing_ms: float = 0.0
    reasoning_ms: float = 0.0
    execution_ms: float = 0.0
    layout_ms: float = 0.0
    transaction_ms: float = 0.0

    # 统计
    commands_count: int = 0
    logical_ops_count: int = 0
    positioned_ops_count: int = 0
    created_elements: int = 0
    def total_ms(self) -> float:
        if self.end_time > 0:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_ms": round(self.total_ms, 2),
            "phases": {
                "hydration_ms": round(self.hydration_ms, 2),
                "routing_ms": round(self.routing_ms, 2),
                "reasoning_ms": round(self.reasoning_ms, 2),
                "execution_ms": round(self.execution_ms, 2),
                "layout_ms": round(self.layout_ms, 2),
                "transaction_ms": round(self.transaction_ms, 2),
            },
            "stats": {
                "commands": self.commands_count,
                "logical_ops": self.logical_ops_count,
                "positioned_ops": self.positioned_ops_count,
                "created_elements": self.created_elements,
            },
        }


@dataclass
class PipelineResult:
    """Pipeline 执行结果"""

    success: bool
    message: str = ""
    thought: str = ""  # LLM 的思考过程
    mode: ReasoningMode = ReasoningMode.HYBRID

    # 各阶段结果
    canvas_state: Optional[CanvasState] = None
    canvas_model: Optional[CanvasModel] = None
    task: Optional[Task] = None

    # 命令和操作
    commands: List[Command] = field(default_factory=list)
    command_results: List[CommandResult] = field(default_factory=list)
    logical_ops: List[LogicalOp] = field(default_factory=list)
    positioned_ops: List[PositionedOp] = field(default_factory=list)
    transaction_result: Optional[TransactionResult] = None
    # (修正) 此处误插入的 llm_client 字段已移除
    # 指标
    metrics: PipelineMetrics = field(default_factory=PipelineMetrics)

    # 创建的元素
    created_ids: List[str] = field(default_factory=list)

class AgentPipeline:
    """Agent Pipeline

    支持控制和创建两种模式的执行管道。

    执行流程:
    1. Phase 1: Cognition.hydrate() - 读取画布状态
    2. Phase 2: Router.classify_and_select() - 动态模型选择
    3. Phase 3: Reasoner.reason() - 输出命令或操作
    4. Phase 4: 执行命令 / 布局求解
    5. Phase 5: Transaction.commit() - CRDT 提交

    使用示例:
        pipeline = AgentPipeline(llm_client)
        result = await pipeline.execute(context, "把登录按钮移到右边")
    """

    def __init__(
        self,
        llm_client: 'LLMClient',
        cognition: Optional[GraphCognition] = None,
        router: Optional[LLMRouter] = None,
        layout: Optional[LayoutEngine] = None,
        transaction: Optional[SemanticTransaction] = None,
        step_callback: Optional[Callable] = None,
    ):
        self.llm = llm_client
        self.cognition = cognition or get_cognition()
        self.router = router or get_router()
        self.reasoner = CanvasReasoner(llm_client)
        self.layout = layout or get_layout_engine()
        self.transaction = transaction or get_transaction()
        self._step_callback = step_callback

    def set_step_callback(self, callback: Callable) -> None:
        """设置步骤回调

        Args:
            callback: 回调函数，接收 (phase: str, data: dict) 参数
        """
        self._step_callback = callback

    async def _emit_step(self, phase: str, data: Dict[str, Any]) -> None:
        """发送步骤事件"""
        if not self._step_callback:
            return
        try:
            result = self._step_callback(phase, data)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:  # pylint: disable=broad-except
            logger.warning("[Pipeline] 步骤回调失败: %s", e)


    async def execute(
        self,
        context: "AgentContext",
        user_input: str,
        temperature: float = 0.2,
        mode: ReasoningMode = ReasoningMode.HYBRID,
    ) -> PipelineResult:
        """执行 Pipeline

        Args:
            context: Agent 执行上下文
            user_input: 用户输入
            temperature: LLM 温度
            mode: 推理模式

        Returns:
            PipelineResult: 执行结果
        """
        metrics = PipelineMetrics(start_time=time.time())

        logger.info(
            "[Pipeline] 开始执行: session=%s, input=%s",
            context.session_id,
            user_input[:50],
        )

        try:
            await self._emit_step("hydration", {"status": "started"})
            phase_start = time.time()

            # 读取画布状态摘要
            canvas_state = await self.cognition.hydrate(context)

            # 构建画布模型
            ydoc = await context.get_ydoc()
            canvas_model = CanvasModel.from_yjs(ydoc) if ydoc else CanvasModel()

            metrics.hydration_ms = (time.time() - phase_start) * 1000

            await self._emit_step("hydration", {
                "status": "completed",
                "element_count": canvas_model.element_count,
                "duration_ms": round(metrics.hydration_ms, 2),
            })

            logger.debug(
                "[Pipeline] Phase 1 完成: %d 元素",
                canvas_model.element_count,
            )

            await self._emit_step("routing", {"status": "started"})
            phase_start = time.time()
            task, model_config = self.router.classify_and_select(
                user_input, canvas_state
            )
            metrics.routing_ms = (time.time() - phase_start) * 1000

            await self._emit_step("routing", {
                "status": "completed",
                "tier": task.tier.value,
                "intent": task.intent.value,
                "complexity": round(task.complexity, 2),
                "model": model_config.model,
            })

            logger.info(
                "[Pipeline] Phase 2 完成: tier=%s, complexity=%.2f",
                task.tier.value,
                task.complexity,
            )

            phase_start = time.time()

            reasoning_result = await self.reasoner.reason(
                user_input=user_input,
                canvas_state=canvas_state,
                canvas_model=canvas_model,
                temperature=temperature,
                mode=mode,
            )

            metrics.reasoning_ms = (time.time() - phase_start) * 1000
            metrics.commands_count = len(reasoning_result.commands)
            metrics.logical_ops_count = len(reasoning_result.operations)

            self.router.record_call(
                model_config.model, metrics.reasoning_ms, reasoning_result.success
            )

            if not reasoning_result.success:
                return PipelineResult(
                    success=False,
                    message=f"推理失败: {reasoning_result.error}",
                    metrics=metrics,
                )

            logger.info(
                "[Pipeline] Phase 3 完成: %d 命令, %d 操作",
                len(reasoning_result.commands),
                len(reasoning_result.operations),
            )

            phase_start = time.time()

            command_results: List[CommandResult] = []
            positioned_ops: List[PositionedOp] = []

            # 执行控制命令
            if reasoning_result.commands:
                executor = CommandExecutor(canvas_model)
                command_results = executor.execute_batch(reasoning_result.commands)
                metrics.execution_ms = (time.time() - phase_start) * 1000

            # 对需要布局的操作进行几何求解
            if reasoning_result.operations:
                phase_start = time.time()
                positioned_ops = await self.layout.solve(
                    reasoning_result.operations, canvas_state
                )
                metrics.layout_ms = (time.time() - phase_start) * 1000
                metrics.positioned_ops_count = len(positioned_ops)

            logger.debug(
                "[Pipeline] Phase 4 完成: %d 命令结果, %d 有坐标操作",
                len(command_results),
                len(positioned_ops),
            )

            phase_start = time.time()

            created_ids: List[str] = []
            tx_result: Optional[TransactionResult] = None

            # 提交创建操作
            if positioned_ops:
                tx_result = await self.transaction.commit(positioned_ops, context)
                if tx_result.success:
                    created_ids.extend(tx_result.created_ids)
                    metrics.created_elements = len(tx_result.created_ids)

            # 提交控制命令的变更
            if command_results:
                await self._commit_command_results(
                    command_results, canvas_model, context
                )

            metrics.transaction_ms = (time.time() - phase_start) * 1000

            metrics.end_time = time.time()

            message = self._build_response_message(
                reasoning_result, command_results, tx_result
            )

            logger.info(
                "[Pipeline] 执行完成: total=%.1fms, commands=%d, created=%d",
                metrics.total_ms,
                len(command_results),
                len(created_ids),
            )

            return PipelineResult(
                success=True,
                message=message,
                thought=reasoning_result.thought,
                mode=reasoning_result.mode,
                canvas_state=canvas_state,
                canvas_model=canvas_model,
                task=task,
                commands=reasoning_result.commands,
                command_results=command_results,
                logical_ops=reasoning_result.operations,
                positioned_ops=positioned_ops,
                transaction_result=tx_result,
                created_ids=created_ids,
                metrics=metrics,
            )

        except Exception as e: # pylint: disable=broad-except
            logger.error("[Pipeline] 执行失败: %s", e, exc_info=True)
            metrics.end_time = time.time()

            return PipelineResult(
                success=False,
                message=f"Pipeline 执行失败: {str(e)}",
                metrics=metrics,
            )

    async def _commit_command_results(
        self,
        results: List[CommandResult],
        model: CanvasModel,
        context: "AgentContext",
    ) -> None:
        """提交命令结果到 CRDT"""
        ydoc = await context.get_ydoc()
        if not ydoc:
            return

        try:
            elements_array = ydoc.get("elements", type="Array")

            with ydoc.transaction(origin="ai-agent/commands"):
                for result in results:
                    if not result.success:
                        continue

                    # 处理移动等变更
                    for eid in result.affected_ids:
                        elem = model.get_element(eid)
                        if elem:
                            # 更新 Yjs 中对应元素
                            for yelem in elements_array:  # 修复: 移除错误的 enumerate
                                elem_id = yelem.get("id") if hasattr(yelem, "get") else None
                                if elem_id == eid:
                                    yelem["x"] = elem.geometry.x
                                    yelem["y"] = elem.geometry.y
                                    yelem["width"] = elem.geometry.width
                                    yelem["height"] = elem.geometry.height
                                    if elem.value:
                                        yelem["text"] = elem.value
                                    break

        except Exception as e:
            logger.error("[Pipeline] 提交命令结果失败: %s", e)
            raise  # 不再静默吞掉错误

    def _build_response_message(
        self,
        reasoning: ReasoningResult,
        cmd_results: List[CommandResult],
        tx_result: Optional[TransactionResult],
    ) -> str:
        """构建响应消息"""
        parts = []

        # 思考过程
        if reasoning.thought:
            parts.append(reasoning.thought)

        # 命令执行摘要
        if cmd_results:
            success_count = sum(1 for r in cmd_results if r.success)
            parts.append(f"\n[执行完成] 执行了 {success_count} 个命令。")

        # 创建摘要
        if tx_result and tx_result.created_ids:
            parts.append(f"创建了 {len(tx_result.created_ids)} 个新元素。")

        # 冲突信息
        if tx_result and tx_result.conflicts:
            auto_fixed = sum(1 for c in tx_result.conflicts if c.auto_fixable)
            if auto_fixed > 0:
                parts.append(f"自动解决了 {auto_fixed} 个冲突。")

        return "\n".join(parts) if parts else "操作完成"


def create_pipeline(llm_client: 'LLMClient') -> 'AgentPipeline':
    """创建 Pipeline 实例
    llm_client: LLMClient 实例
    """
    # 延迟导入，避免循环依赖
    from src.agent.llm import LLMClient
    return AgentPipeline(llm_client)
