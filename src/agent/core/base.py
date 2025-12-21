from __future__ import annotations

import inspect
import asyncio
import json
import time
import traceback
from abc import ABC
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING, TypeVar
from pydantic import BaseModel, Field
from openai.types.chat import ChatCompletionMessageParam
from src.agent.prompts.reflection import SelfReflection
from src.agent.core.llm import LLMClient, LLMResponse
from src.agent.core.errors import parse_tool_call_args
from src.logger import get_logger
from src.agent.core.state import AgentState, AgentStateMachine
from src.agent.core.retry import RetryPolicy, ErrorRecoveryManager
from src.agent.core.context import AgentContext, AgentMetrics, AgentStatus

if TYPE_CHECKING:
    from src.services.agent_runs import AgentRunService

logger = get_logger(__name__)

T = TypeVar("T")


class RoomLockManager:
    """房间级别的并发锁管理器

    防止同一房间同时有多个 Agent 操作，避免元素冲突。
    """

    _locks: Dict[str, asyncio.Lock] = {}
    _active_rooms: Set[str] = set()

    @classmethod
    def get_lock(cls, room_id: str) -> asyncio.Lock:
        """获取房间锁"""
        if room_id not in cls._locks:
            cls._locks[room_id] = asyncio.Lock()
        return cls._locks[room_id]

    @classmethod
    @asynccontextmanager
    async def acquire(cls, room_id: str, timeout: float = 30.0):
        """获取房间锁的上下文管理器

        Args:
            room_id: 房间 ID
            timeout: 获取锁的超时时间

        Raises:
            TimeoutError: 获取锁超时
            RuntimeError: 房间正忙
        """
        lock = cls.get_lock(room_id)

        try:
            acquired = await asyncio.wait_for(lock.acquire(), timeout=timeout)
            if not acquired:
                raise RuntimeError(f"房间 {room_id} 正忙，请稍后再试")

            cls._active_rooms.add(room_id)
            logger.debug("获取房间锁: %s", room_id)

            yield

        except asyncio.TimeoutError as exc:
            raise TimeoutError(f"获取房间 {room_id} 的锁超时") from exc
        finally:
            if room_id in cls._active_rooms:
                cls._active_rooms.discard(room_id)
            if lock.locked():
                lock.release()
                logger.debug("释放房间锁: %s", room_id)

    @classmethod
    def is_room_busy(cls, room_id: str) -> bool:
        """检查房间是否正忙"""
        return room_id in cls._active_rooms

    @classmethod
    def get_active_rooms(cls) -> list:
        """获取所有活跃房间列表"""
        return list(cls._active_rooms)


@dataclass
class ToolDefinition:
    """工具定义"""

    name: str
    description: str
    func: Callable
    schema: Dict[str, Any]
    timeout: float = 30.0  # 工具执行超时
    retries: int = 2  # 重试次数


@dataclass
class ReActStep:
    """ReAct 单步记录"""

    step_number: int
    thought: str = ""
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    success: bool = True
    latency_ms: float = 0.0


class AgentConfig(BaseModel):
    """Agent 配置

    集中管理 Agent 的各项配置参数。
    使用 pydantic BaseModel 以支持 UI 渲染元数据。
    """

    max_iterations: int = Field(
        default=15, title="最大迭代次数", description="ReAct 循环最大迭代次数"
    )
    max_retries: int = Field(
        default=3, title="重试次数", description="LLM/工具调用失败重试次数"
    )
    llm_timeout: float = Field(
        default=60.0, title="LLM 超时 (秒)", description="单次 LLM 调用超时时间"
    )
    tool_timeout: float = Field(
        default=30.0, title="工具超时 (秒)", description="单个工具执行超时时间"
    )
    total_timeout: float = Field(
        default=300.0, title="总超时 (秒)", description="Agent 任务总执行超时 (5分钟)"
    )
    retry_delay: float = Field(
        default=1.0, title="重试间隔 (秒)", description="失败后重试等待时间"
    )
    enable_room_lock: bool = Field(
        default=True, title="启用房间锁", description="防止同一房间同时多个 Agent 操作"
    )
    enable_self_reflection: bool = Field(
        default=True, title="启用自反思", description="每轮迭代后进行自我评估"
    )
    reflection_interval: int = Field(
        default=2,
        ge=1,
        title="反思间隔",
        description="每隔多少轮进行一次自反思 (1=每轮, 2=第2/4/6轮)",
    )


class BaseAgent(ABC):
    """ReAct Agent 抽象基类

    实现标准的 ReAct 循环: Think -> Act -> Observe -> Repeat

    增强特性:
    - 自动重试失败的 LLM 调用和工具执行
    - 超时控制，防止无限期执行
    - 并发锁，防止同房间冲突
    - 详细的执行指标
    """

    DEFAULT_CONFIG = AgentConfig()

    def __init__(
        self,
        name: str,
        role: str,
        llm_client: LLMClient,
        system_prompt: str,
        config: Optional[AgentConfig] = None,
        run_service: Optional["AgentRunService"] = None,
        # 兼容旧参数
        max_iterations: Optional[int] = None,
    ):
        self.name = name
        self.role = role
        self.llm = llm_client
        self.system_prompt = system_prompt
        self.run_service = run_service

        # 配置
        self.config = config or AgentConfig()
        if max_iterations is not None:
            self.config.max_iterations = max_iterations

        # 兼容旧属性
        self.max_iterations = self.config.max_iterations

        # 运行时状态
        self.tools: Dict[str, ToolDefinition] = {}
        self._status = AgentStatus.IDLE
        self._steps: List[ReActStep] = []
        self._metrics = AgentMetrics()
        self._on_step_callback: Optional[Callable[[ReActStep], None]] = None

        # 状态机和错误恢复
        self._state_machine = AgentStateMachine()
        self._recovery_manager = ErrorRecoveryManager(
            default_policy=RetryPolicy(
                max_retries=self.config.max_retries,
                base_delay=self.config.retry_delay,
            )
        )

    @property
    def status(self) -> AgentStatus:
        return self._status

    @property
    def state_machine(self) -> AgentStateMachine:
        """获取状态机"""
        return self._state_machine

    @property
    def steps(self) -> List[ReActStep]:
        return self._steps.copy()

    @property
    def metrics(self) -> AgentMetrics:
        return self._metrics

    def register_tool(
        self,
        name: str,
        func: Callable,
        schema: Dict[str, Any],
        description: str = "",
        timeout: float = 30.0,
        retries: int = 2,
    ) -> None:
        """注册工具"""
        self.tools[name] = ToolDefinition(
            name=name,
            description=description
            or schema.get("function", {}).get("description", ""),
            func=func,
            schema=schema,
            timeout=timeout,
            retries=retries,
        )
        logger.debug("Agent %s 注册工具: %s", self.name, name)

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """获取所有工具的 OpenAI Function Calling 定义"""
        return [tool.schema for tool in self.tools.values()]

    def set_step_callback(self, callback: Callable[[ReActStep], None]) -> None:
        """设置步骤回调"""
        self._on_step_callback = callback

    async def _log_action(
        self, context: AgentContext, tool_name: str, args: Dict[str, Any], result: Any
    ) -> None:
        """记录工具调用到数据库"""
        if self.run_service:
            try:
                await self.run_service.log_action_async(
                    run_id=context.run_id,
                    tool=tool_name,
                    arguments=args,
                    result=result
                    if isinstance(result, dict)
                    else {"output": str(result)[:500]},
                )
            except Exception as e:  # pylint: disable=broad-except
                logger.warning("记录工具调用失败: %s", e)

    async def _call_llm_with_retry(
        self,
        messages: List[ChatCompletionMessageParam],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float,
    ) -> LLMResponse:
        """带重试的 LLM 调用

        Returns:
            LLMResponse: LLM 响应

        Raises:
            Exception: 所有重试都失败后抛出最后一个异常
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries):
            try:
                start_time = time.time()

                response = await asyncio.wait_for(
                    self.llm.chat_completion(
                        messages=messages,
                        tools=tools,
                        tool_choice="auto" if tools else "none",
                        temperature=temperature,
                    ),
                    timeout=self.config.llm_timeout,
                )

                # 记录延迟
                latency = (time.time() - start_time) * 1000
                self._metrics.llm_latency_ms.append(latency)
                self._metrics.total_llm_calls += 1

                return response

            except asyncio.TimeoutError:
                last_error = TimeoutError(f"LLM 调用超时 ({self.config.llm_timeout}s)")
                self._metrics.errors.append(f"LLM 超时 (尝试 {attempt + 1})")
            except Exception as e:  # pylint: disable=broad-except
                last_error = e
                self._metrics.errors.append(f"LLM 错误: {str(e)[:100]}")

            if attempt < self.config.max_retries - 1:
                self._metrics.total_retries += 1
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                logger.warning(
                    "LLM 调用重试 (%s/%s)", attempt + 2, self.config.max_retries
                )

        raise last_error or Exception("未知错误")

    async def _execute_tool_with_retry(
        self,
        name: str,
        args: Dict[str, Any],
        context: AgentContext,
    ) -> Dict[str, Any]:
        """带重试和超时的工具执行

        Returns:
            dict: 工具执行结果
        """
        tool = self.tools[name]
        last_error: Optional[Exception] = None

        for attempt in range(tool.retries):
            try:
                start_time = time.time()

                # 使用工具专属超时
                result = await asyncio.wait_for(
                    self._execute_tool(name, args, context), timeout=tool.timeout
                )

                # 记录延迟
                latency = (time.time() - start_time) * 1000
                self._metrics.tool_latency_ms.append(latency)
                self._metrics.total_tool_calls += 1

                return result

            except asyncio.TimeoutError:
                last_error = TimeoutError(f"工具 {name} 执行超时 ({tool.timeout}s)")
                self._metrics.errors.append(f"工具 {name} 超时")
                logger.error(
                    "工具 %s 执行超时 (timeout=%ss, attempt=%d)",
                    name,
                    tool.timeout,
                    attempt + 1,
                )
            except Exception as e:  # pylint: disable=broad-except
                last_error = e
                self._metrics.errors.append(f"工具 {name} 错误: {str(e)[:100]}")
                # 打印完整堆栈信息
                logger.error(
                    "工具 %s 执行失败 [%s]: %s",
                    name,
                    type(e).__name__,
                    str(e)[:200],
                    exc_info=True,
                )

            if attempt < tool.retries - 1:
                self._metrics.total_retries += 1
                await asyncio.sleep(self.config.retry_delay)
                logger.warning(
                    "工具 %s 重试 (%d/%d) - 上次错误: %s",
                    name,
                    attempt + 2,
                    tool.retries,
                    str(last_error)[:100],
                )

        # 返回错误结果而不是抛出异常
        return {
            "status": "error",
            "message": str(last_error) if last_error else "未知错误",
            "retries": tool.retries,
        }

    async def run(
        self,
        context: AgentContext,
        user_input: str,
        temperature: float = 0.3,
    ) -> str:
        """执行 ReAct 循环

        Args:
            context: Agent 上下文
            user_input: 用户输入
            temperature: LLM 温度参数

        Returns:
            str: Agent 最终响应
        """
        # 初始化状态机和指标
        self._state_machine.reset()
        self._state_machine.transition(AgentState.INITIALIZING, reason="开始任务")
        self._status = AgentStatus.THINKING
        self._steps = []
        self._metrics = AgentMetrics(start_time=time.time())

        logger.info(
            "Agent %s 开始执行",
            self.name,
            extra={"run_id": context.run_id, "session_id": context.session_id},
        )

        try:
            # 转换到思考状态
            self._state_machine.transition(
                AgentState.THINKING, reason="开始处理用户请求"
            )

            # 如果启用房间锁，获取锁
            if self.config.enable_room_lock and context.session_id:
                async with RoomLockManager.acquire(context.session_id, timeout=30.0):
                    result = await self._run_react_loop(
                        context, user_input, temperature
                    )
            else:
                result = await self._run_react_loop(context, user_input, temperature)

            # 成功完成
            self._state_machine.transition(AgentState.COMPLETED, reason="任务完成")
            self._status = AgentStatus.COMPLETED
            return result

        except TimeoutError as e:
            self._state_machine.transition(
                AgentState.FAILED, reason="超时: %s", force=True
            )
            self._status = AgentStatus.TIMEOUT
            self._metrics.errors.append(str(e))
            logger.error("Agent %s 执行超时: %s", self.name, e)
            return f"执行超时: {str(e)}"

        except asyncio.CancelledError:
            self._state_machine.transition(
                AgentState.CANCELLED, reason="用户取消", force=True
            )
            self._status = AgentStatus.CANCELLED
            logger.warning("Agent %s 被取消", self.name)
            return "任务已取消"

        except Exception as e:  # pylint: disable=broad-except
            self._state_machine.transition(
                AgentState.FAILED, reason=f"错误: {e}", force=True
            )
            self._status = AgentStatus.ERROR
            self._metrics.errors.append(str(e))
            logger.error(
                "Agent %s 执行失败: %s\n%s", self.name, e, traceback.format_exc()
            )
            return f"执行失败: {str(e)}"

        finally:
            self._metrics.end_time = time.time()
            logger.info(
                "Agent %s 执行结束",
                self.name,
                extra={
                    "run_id": context.run_id,
                    "status": self._status.value,
                    "metrics": self._metrics.to_dict(),
                    "state_machine": self._state_machine.get_summary(),
                },
            )

    async def _run_react_loop(
        self,
        context: AgentContext,
        user_input: str,
        temperature: float,
    ) -> str:
        """ReAct 主循环

        使用总超时控制整个执行过程。
        """
        # 初始化消息历史
        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": user_input},
        ]

        tool_definitions = self.get_tool_definitions() if self.tools else None
        final_response = ""
        iteration = 0

        # 总超时控制
        async with asyncio.timeout(self.config.total_timeout):
            while iteration < self.config.max_iterations:
                # 检查是否被取消
                if context.is_cancelled:
                    self._status = AgentStatus.CANCELLED
                    return "任务已取消"

                iteration += 1
                step_start = time.time()
                current_step = ReActStep(step_number=iteration)

                self._status = AgentStatus.THINKING
                self._state_machine.transition(
                    AgentState.THINKING, reason=f"迭代 {iteration}"
                )
                try:
                    response = await self._call_llm_with_retry(
                        messages, tool_definitions, temperature
                    )
                except Exception as e:  # pylint: disable=broad-except
                    self._status = AgentStatus.ERROR
                    self._state_machine.transition(
                        AgentState.RECOVERING, reason=f"LLM 错误: {e}"
                    )
                    current_step.success = False
                    current_step.observation = str(e)
                    self._steps.append(current_step)
                    return f"处理请求时发生错误: {str(e)}"

                current_step.thought = response.content or ""

                # 构建 assistant 消息
                assistant_message: Dict[str, Any] = {
                    "role": "assistant",
                    "content": response.content,
                }
                if response.tool_calls:
                    assistant_message["tool_calls"] = [
                        {"id": tc["id"], "type": "function", "function": tc["function"]}
                        for tc in response.tool_calls
                    ]
                messages.append(assistant_message)  # type: ignore[arg-type]

                if response.tool_calls:
                    self._status = AgentStatus.ACTING
                    self._state_machine.transition(
                        AgentState.ACTING,
                        reason=f"执行 {len(response.tool_calls)} 个工具",
                    )

                    for tool_call in response.tool_calls:
                        func_name = tool_call["function"]["name"]
                        func_args_str = tool_call["function"]["arguments"]
                        call_id = tool_call["id"]

                        current_step.action = func_name

                        try:
                            # 使用 json_repair 容错解析
                            func_args = parse_tool_call_args(func_args_str)
                            current_step.action_input = func_args

                            logger.info(
                                "Agent %s 执行工具: %s",
                                self.name,
                                func_name,
                                extra={"run_id": context.run_id},
                            )

                            # 执行工具 (带重试)
                            if func_name in self.tools:
                                result = await self._execute_tool_with_retry(
                                    func_name, func_args, context
                                )
                                result_str = json.dumps(result, ensure_ascii=False)

                                # 提取创建的元素 ID
                                if isinstance(result, dict):
                                    if result.get("element_id"):
                                        context.created_element_ids.append(
                                            result["element_id"]
                                        )
                                    if result.get("arrow_id"):
                                        context.created_element_ids.append(
                                            result["arrow_id"]
                                        )
                            else:
                                result = {
                                    "status": "error",
                                    "message": f"工具 {func_name} 不存在",
                                }
                                result_str = json.dumps(result, ensure_ascii=False)

                            # 记录工具调用
                            await self._log_action(
                                context, func_name, func_args, result
                            )

                            # 记录到上下文
                            context.tool_results.append(
                                {
                                    "tool": func_name,
                                    "args": func_args,
                                    "result": result_str[:1000],
                                }
                            )

                        except json.JSONDecodeError as e:
                            result_str = json.dumps(
                                {
                                    "status": "error",
                                    "message": f"参数解析失败: {str(e)}",
                                },
                                ensure_ascii=False,
                            )
                            current_step.success = False
                        except Exception as e:  # pylint: disable=broad-except
                            logger.error("工具 %s 执行失败: %s", func_name, e)
                            result_str = json.dumps(
                                {"status": "error", "message": f"执行失败: {str(e)}"},
                                ensure_ascii=False,
                            )
                            current_step.success = False

                        self._status = AgentStatus.OBSERVING
                        current_step.observation = result_str

                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": call_id,
                                "content": result_str,
                            }
                        )

                    # 记录步骤
                    current_step.latency_ms = (time.time() - step_start) * 1000
                    self._steps.append(current_step)
                    if self._on_step_callback:
                        callback_result = self._on_step_callback(current_step)
                        if asyncio.iscoroutine(callback_result):
                            await callback_result  # type: ignore[misc]

                    # 按间隔进行自反思，帮助 Agent 评估进度
                    if (
                        self.config.enable_self_reflection
                        and iteration % self.config.reflection_interval == 0
                    ):
                        reflection_prompt = self._build_reflection_prompt(
                            iteration, context
                        )
                        messages.append(  # type: ignore[arg-type]
                            {"role": "user", "content": reflection_prompt}
                        )
                        logger.debug("Self-reflection at iteration %d", iteration)

                    continue

                current_step.latency_ms = (time.time() - step_start) * 1000
                self._steps.append(current_step)
                if self._on_step_callback:
                    callback_result = self._on_step_callback(current_step)
                    if asyncio.iscoroutine(callback_result):
                        await callback_result  # type: ignore[misc]

                final_response = response.content or ""
                break

        self._status = AgentStatus.COMPLETED
        return final_response

    async def _execute_tool(
        self, name: str, args: Dict[str, Any], context: AgentContext
    ) -> Any:
        """执行已注册的工具"""
        tool = self.tools[name]
        func = tool.func

        sig = inspect.signature(func)
        if "context" in sig.parameters:
            return await func(**args, context=context)
        return await func(**args)

    def _build_system_prompt(self) -> str:
        """构建完整的系统提示词"""
        return self.system_prompt

    def _build_reflection_prompt(self, iteration: int, context: AgentContext) -> str:
        """构建自反思提示

        使用 Jinja2 模板系统渲染，遵循项目的模板规范。

        Args:
            iteration: 当前迭代轮数
            context: Agent 上下文

        Returns:
            str: 自反思提示词
        """

        return SelfReflection(
            current_iteration=iteration,
            max_iterations=self.config.max_iterations,
            tool_results=context.tool_results,
            created_element_ids=context.created_element_ids,
        ).render()


class PlanningAgent(BaseAgent):
    """支持规划的 Agent

    在执行前先进行任务规划，将复杂任务分解为子任务。
    """

    PLANNING_PROMPT_TEMPLATE: str = """
## 执行策略
在开始执行之前，请先分析用户的请求并制定执行计划。

请按以下思考步骤执行:
1. **分析需求**: 理解用户想要什么
2. **规划步骤**: 列出需要创建的元素和连接
3. **计算坐标**: 确定每个元素的位置
4. **逐步执行**: 按照规划依次创建元素

重要: 每次工具调用后检查结果，记住返回的 element_id，用于后续连接。
"""

    def __init__(
        self,
        name: str,
        role: str,
        llm_client: LLMClient,
        system_prompt: str,
        config: Optional[AgentConfig] = None,
        run_service: Optional["AgentRunService"] = None,
        enable_planning: bool = True,
        # 兼容旧参数
        max_iterations: Optional[int] = None,
    ):
        super().__init__(
            name, role, llm_client, system_prompt, config, run_service, max_iterations
        )
        self.enable_planning = enable_planning

    def _build_system_prompt(self) -> str:
        """构建包含规划指导的系统提示词"""
        base_prompt = super()._build_system_prompt()
        if self.enable_planning:
            return f"{base_prompt}\n\n{self.PLANNING_PROMPT_TEMPLATE}"
        return base_prompt


class CanvasAgent(BaseAgent):
    """SyncCanvas AI Agent

    统一的画布操作 Agent，基于 ReAct 循环实现。
    支持绘图、修改、删除等操作。

    通过切换提示词模板实现不同的思考模式:
    - 常规对话: system.jinja2
    - 绘图任务: canvaser.jinja2
    - 控制操作: controller.jinja2
    """

    DEFAULT_CONFIG = AgentConfig(
        max_iterations=15,
        llm_timeout=60.0,
        tool_timeout=30.0,
        total_timeout=300.0,
        enable_room_lock=True,
        enable_self_reflection=True,
        reflection_interval=3,
    )

    def __init__(
        self,
        llm_client: LLMClient,
        run_service: Optional["AgentRunService"] = None,
        config: Optional[AgentConfig] = None,
    ):
        """初始化 CanvasAgent

        Args:
            llm_client: LLM 客户端实例
            run_service: Agent 运行记录服务 (可选)
            config: 自定义配置 (可选)
        """
        # 延迟导入避免循环依赖
        from src.agent.prompts import prompt_manager
        from src.agent.core.registry import registry
        import src.agent.tools  # noqa: F401  # 确保工具被注册

        self._prompt_manager = prompt_manager
        self._registry = registry

        system_prompt = self._build_prompt_from_template()

        super().__init__(
            name="CanvasAgent",
            role="SyncCanvas AI Assistant",
            llm_client=llm_client,
            system_prompt=system_prompt,
            config=config or self.DEFAULT_CONFIG,
            run_service=run_service,
        )

        self._register_default_tools()

    def _build_prompt_from_template(self) -> str:
        """从 Jinja2 模板构建系统提示词"""
        try:
            return self._prompt_manager.render(
                "canvaser.jinja2",
                tools=[
                    {
                        "name": "auto_layout_create",
                        "description": "一次性创建图表 (推荐，无需计算坐标)",
                    },
                    {"name": "create_flowchart_node", "description": "创建单个节点"},
                    {"name": "connect_nodes", "description": "连接两个节点"},
                    {"name": "list_elements", "description": "查看画布元素"},
                    {"name": "update_element", "description": "更新元素属性"},
                    {"name": "delete_elements", "description": "删除元素"},
                ],
                layout={},  # 新 prompt 不需要 layout 参数
                guidelines=[
                    "创建新图表时优先使用 auto_layout_create",
                    "颜色会自动适配当前主题，无需指定",
                ],
                enable_cot=True,
            )
        except Exception as e:
            logger.error("Jinja2 模板渲染失败: %s, 使用默认提示词", e)
            return self._get_fallback_prompt()

    def _get_fallback_prompt(self) -> str:
        """备用提示词"""
        return """你是 SyncCanvas AI 助手，负责在 Excalidraw 画布上绘制图表。

可用工具:
- get_canvas_bounds: 获取画布边界
- create_flowchart_node: 创建节点
- connect_nodes: 连接节点
- batch_create_elements: 批量创建
- list_elements: 查看元素
- update_element: 更新元素
- delete_elements: 删除元素

规则:
1. 先调用 get_canvas_bounds 获取画布状态
2. 记住每个创建的 element_id
3. 保持布局整齐
"""

    def _register_default_tools(self) -> None:
        """注册默认工具"""
        for name, func in self._registry.get_all_tools().items():
            schema = self._registry.get_schema(name)
            meta = self._registry.get_metadata(name)

            if not schema:
                continue

            # 跳过危险工具
            if meta and meta.dangerous:
                continue

            timeout = meta.timeout if meta else 30.0
            retries = meta.retries if meta else 2

            self.register_tool(
                name,
                func,
                schema,
                timeout=timeout,
                retries=retries,
            )

        logger.info("CanvasAgent 已注册 %d 个工具", len(self.tools))
