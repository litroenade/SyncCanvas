"""模块名称: agent
主要功能: AI Engine 核心 Agent 基类

实现标准的 ReAct (Reasoning + Acting) 架构:
- Thought: Agent 推理当前情况和下一步计划
- Action: 选择并执行工具
- Observation: 获取工具执行结果并反馈给 Agent
- 循环直到任务完成

增强特性:
- 重试机制: LLM 调用和工具执行失败自动重试
- 超时控制: 防止任务无限期执行
- 并发锁: 防止同一房间同时多个 Agent 操作
- 执行指标: 详细的性能统计
"""

from __future__ import annotations

import asyncio
import json
import time
import traceback
from abc import ABC
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING

from pydantic import BaseModel, Field

from openai.types.chat import ChatCompletionMessageParam

from src.agent.core.llm import LLMClient, LLMResponse
from src.agent.core.json_parser import parse_tool_call_args
from src.logger import get_logger

if TYPE_CHECKING:
    from src.services.agent_runs import AgentRunService

logger = get_logger(__name__)


# ==================== 房间锁管理 ====================


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
            logger.debug(f"获取房间锁: {room_id}")

            yield

        except asyncio.TimeoutError:
            raise TimeoutError(f"获取房间 {room_id} 的锁超时")
        finally:
            if room_id in cls._active_rooms:
                cls._active_rooms.discard(room_id)
            if lock.locked():
                lock.release()
                logger.debug(f"释放房间锁: {room_id}")

    @classmethod
    def is_room_busy(cls, room_id: str) -> bool:
        """检查房间是否正忙"""
        return room_id in cls._active_rooms


# ==================== 状态和数据结构 ====================


class AgentStatus(Enum):
    """Agent 运行状态枚举"""

    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    COMPLETED = "completed"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class AgentMetrics:
    """Agent 执行指标

    用于性能监控和调试。
    """

    start_time: float = 0.0
    end_time: float = 0.0
    total_llm_calls: int = 0
    total_tool_calls: int = 0
    total_retries: int = 0
    llm_latency_ms: List[float] = field(default_factory=list)
    tool_latency_ms: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        """总执行时间 (毫秒)"""
        if self.end_time > 0:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    @property
    def avg_llm_latency_ms(self) -> float:
        """平均 LLM 延迟"""
        if self.llm_latency_ms:
            return sum(self.llm_latency_ms) / len(self.llm_latency_ms)
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "duration_ms": round(self.duration_ms, 2),
            "total_llm_calls": self.total_llm_calls,
            "total_tool_calls": self.total_tool_calls,
            "total_retries": self.total_retries,
            "avg_llm_latency_ms": round(self.avg_llm_latency_ms, 2),
            "errors": self.errors[-5:],  # 最近 5 个错误
        }


@dataclass
class AgentContext:
    """Agent 执行上下文

    封装 Agent 在执行任务时所需的所有上下文信息，提供画布操作便捷方法。

    Attributes:
        run_id: 运行记录 ID
        session_id: 房间/会话 ID
        user_id: 触发用户 ID (可选)
        shared_state: 共享状态字典，用于在工具调用间传递数据
        tool_results: 工具执行结果列表
        created_element_ids: 已创建的元素 ID 列表
    """

    run_id: int
    session_id: str
    user_id: Optional[str] = None
    shared_state: Dict[str, Any] = field(default_factory=dict)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    created_element_ids: List[str] = field(default_factory=list)
    _cancelled: bool = field(default=False, repr=False)
    _ydoc: Any = field(default=None, repr=False)  # 缓存的 ydoc 引用

    def cancel(self) -> None:
        """标记任务为已取消"""
        self._cancelled = True
        logger.info(f"[AgentContext] 任务已取消: run_id={self.run_id}")

    @property
    def is_cancelled(self) -> bool:
        """检查任务是否已取消"""
        return self._cancelled

    async def get_ydoc(self) -> Any:
        """获取房间的 Yjs 文档

        Returns:
            Doc: pycrdt 文档实例，不存在则返回 None
        """
        if self._ydoc is not None:
            return self._ydoc

        # 延迟导入避免循环依赖
        from src.ws.sync import websocket_server

        room = websocket_server.rooms.get(self.session_id)
        if room:
            self._ydoc = room.ydoc
            return self._ydoc
        return None

    async def get_canvas_elements(self) -> List[Dict[str, Any]]:
        """获取画布上的所有元素

        Returns:
            List[Dict]: 元素列表
        """
        ydoc = await self.get_ydoc()
        if not ydoc:
            logger.warning(f"[AgentContext] 无法获取房间文档: {self.session_id}")
            return []

        try:
            elements_array = ydoc.get("elements", type="Array")
            return list(elements_array)
        except Exception as e:
            logger.error(f"[AgentContext] 获取画布元素失败: {e}")
            return []

    async def get_canvas_bounds(self) -> Dict[str, Any]:
        """获取画布边界信息

        Returns:
            Dict: 包含 minX, minY, maxX, maxY, suggested_x, suggested_y 的字典
        """
        elements = await self.get_canvas_elements()

        if not elements:
            return {
                "minX": 0,
                "minY": 0,
                "maxX": 0,
                "maxY": 0,
                "suggested_x": 100,
                "suggested_y": 100,
                "elements_count": 0,
            }

        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")

        for elem in elements:
            x = elem.get("x", 0)
            y = elem.get("y", 0)
            width = elem.get("width", 100)
            height = elem.get("height", 100)
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x + width)
            max_y = max(max_y, y + height)

        return {
            "minX": min_x if min_x != float("inf") else 0,
            "minY": min_y if min_y != float("inf") else 0,
            "maxX": max_x if max_x != float("-inf") else 0,
            "maxY": max_y if max_y != float("-inf") else 0,
            "suggested_x": max_x + 50 if max_x != float("-inf") else 100,
            "suggested_y": min_y if min_y != float("inf") else 100,
            "elements_count": len(elements),
        }

    def record_tool_result(self, tool_name: str, args: Dict, result: Any) -> None:
        """记录工具执行结果"""
        self.tool_results.append(
            {
                "tool": tool_name,
                "arguments": args,
                "result": result,
            }
        )

    def get_shared(self, key: str, default: Any = None) -> Any:
        """获取共享状态值"""
        return self.shared_state.get(key, default)

    def set_shared(self, key: str, value: Any) -> None:
        """设置共享状态值"""
        self.shared_state[key] = value


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


# ==================== Agent 配置 ====================


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


# ==================== Agent 基类 ====================


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

    @property
    def status(self) -> AgentStatus:
        return self._status

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
        logger.debug(f"Agent {self.name} 注册工具: {name}")

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
            except Exception as e:
                logger.warning(f"记录工具调用失败: {e}")

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
            except Exception as e:
                last_error = e
                self._metrics.errors.append(f"LLM 错误: {str(e)[:100]}")

            if attempt < self.config.max_retries - 1:
                self._metrics.total_retries += 1
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                logger.warning(
                    f"LLM 调用重试 ({attempt + 2}/{self.config.max_retries})"
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
            except Exception as e:
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
        # 初始化
        self._status = AgentStatus.THINKING
        self._steps = []
        self._metrics = AgentMetrics(start_time=time.time())

        logger.info(
            f"Agent {self.name} 开始执行",
            extra={"run_id": context.run_id, "session_id": context.session_id},
        )

        try:
            # 如果启用房间锁，获取锁
            if self.config.enable_room_lock and context.session_id:
                async with RoomLockManager.acquire(context.session_id, timeout=30.0):
                    return await self._run_react_loop(context, user_input, temperature)
            else:
                return await self._run_react_loop(context, user_input, temperature)

        except TimeoutError as e:
            self._status = AgentStatus.TIMEOUT
            self._metrics.errors.append(str(e))
            logger.error(f"Agent {self.name} 执行超时: {e}")
            return f"执行超时: {str(e)}"

        except asyncio.CancelledError:
            self._status = AgentStatus.CANCELLED
            logger.warning(f"Agent {self.name} 被取消")
            return "任务已取消"

        except Exception as e:
            self._status = AgentStatus.ERROR
            self._metrics.errors.append(str(e))
            logger.error(f"Agent {self.name} 执行失败: {e}\n{traceback.format_exc()}")
            return f"执行失败: {str(e)}"

        finally:
            self._metrics.end_time = time.time()
            logger.info(
                f"Agent {self.name} 执行结束",
                extra={
                    "run_id": context.run_id,
                    "status": self._status.value,
                    "metrics": self._metrics.to_dict(),
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

                # ========== THINK: 调用 LLM ==========
                self._status = AgentStatus.THINKING
                try:
                    response = await self._call_llm_with_retry(
                        messages, tool_definitions, temperature
                    )
                except Exception as e:
                    self._status = AgentStatus.ERROR
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
                messages.append(assistant_message)

                # ========== ACT: 执行工具 ==========
                if response.tool_calls:
                    self._status = AgentStatus.ACTING

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
                                f"Agent {self.name} 执行工具: {func_name}",
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
                        except Exception as e:
                            logger.error(f"工具 {func_name} 执行失败: {e}")
                            result_str = json.dumps(
                                {"status": "error", "message": f"执行失败: {str(e)}"},
                                ensure_ascii=False,
                            )
                            current_step.success = False

                        # ========== OBSERVE ==========
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
                        self._on_step_callback(current_step)
                    continue

                # ========== COMPLETE ==========
                current_step.latency_ms = (time.time() - step_start) * 1000
                self._steps.append(current_step)
                if self._on_step_callback:
                    self._on_step_callback(current_step)

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

        import inspect

        sig = inspect.signature(func)
        if "context" in sig.parameters:
            return await func(**args, context=context)
        return await func(**args)

    def _build_system_prompt(self) -> str:
        """构建完整的系统提示词"""
        return self.system_prompt


# ==================== PlanningAgent ====================


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
