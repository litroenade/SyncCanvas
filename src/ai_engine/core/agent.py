"""模块名称: agent
主要功能: AI Engine 核心 Agent 基类

实现标准的 ReAct (Reasoning + Acting) 架构:
- Thought: Agent 推理当前情况和下一步计划
- Action: 选择并执行工具
- Observation: 获取工具执行结果并反馈给 Agent
- 循环直到任务完成
"""

from __future__ import annotations

import json
import traceback
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from openai.types.chat import ChatCompletionMessageParam

from src.ai_engine.core.llm import LLMClient, LLMResponse
from src.logger import get_logger

if TYPE_CHECKING:
    from src.services.agent_runs import AgentRunService

logger = get_logger(__name__)


class AgentStatus(Enum):
    """Agent 运行状态枚举

    Attributes:
        IDLE: 空闲状态
        THINKING: 推理中
        ACTING: 执行工具中
        OBSERVING: 观察结果中
        COMPLETED: 已完成
        ERROR: 发生错误
    """
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentContext:
    """Agent 执行上下文

    在 Agent 执行过程中传递的上下文对象，包含运行 ID、会话 ID 等信息。

    Attributes:
        run_id: 运行记录 ID
        session_id: 会话/房间 ID
        user_id: 用户 ID (可选)
        shared_state: 共享状态字典，用于在工具间传递数据
        tool_results: 本次运行的工具调用结果历史
        created_element_ids: 本次运行创建的元素 ID 列表
    """
    run_id: int
    session_id: str
    user_id: Optional[str] = None
    shared_state: Dict[str, Any] = field(default_factory=dict)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    created_element_ids: List[str] = field(default_factory=list)


@dataclass
class ToolDefinition:
    """工具定义

    Attributes:
        name: 工具名称
        description: 工具描述
        func: 工具函数
        schema: OpenAI Function Calling 格式的 JSON Schema
    """
    name: str
    description: str
    func: Callable
    schema: Dict[str, Any]


@dataclass
class ReActStep:
    """ReAct 单步记录

    Attributes:
        step_number: 步骤编号
        thought: 思考内容
        action: 执行的动作 (工具名称)
        action_input: 动作输入参数
        observation: 观察结果
        success: 是否执行成功
    """
    step_number: int
    thought: str = ""
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    success: bool = True


class BaseAgent(ABC):
    """ReAct Agent 抽象基类

    实现标准的 ReAct 循环: Think -> Act -> Observe -> Repeat

    Attributes:
        name: Agent 名称
        role: Agent 角色描述
        llm: LLM 客户端
        system_prompt: 系统提示词
        max_iterations: 最大迭代次数
        tools: 已注册的工具字典
        run_service: Agent 运行记录服务 (可选)
    """

    # 类级别常量
    DEFAULT_MAX_ITERATIONS: int = 15
    DEFAULT_TEMPERATURE: float = 0.3

    def __init__(
        self,
        name: str,
        role: str,
        llm_client: LLMClient,
        system_prompt: str,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        run_service: Optional["AgentRunService"] = None,
    ):
        """初始化 Agent

        Args:
            name: Agent 名称
            role: Agent 角色
            llm_client: LLM 客户端实例
            system_prompt: 系统提示词
            max_iterations: 最大迭代次数
            run_service: Agent 运行记录服务 (可选)
        """
        self.name = name
        self.role = role
        self.llm = llm_client
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.run_service = run_service
        self.tools: Dict[str, ToolDefinition] = {}
        self._status = AgentStatus.IDLE
        self._steps: List[ReActStep] = []
        self._on_step_callback: Optional[Callable[[ReActStep], None]] = None

    @property
    def status(self) -> AgentStatus:
        """获取当前状态"""
        return self._status

    @property
    def steps(self) -> List[ReActStep]:
        """获取执行步骤历史"""
        return self._steps.copy()

    def register_tool(
        self,
        name: str,
        func: Callable,
        schema: Dict[str, Any],
        description: str = ""
    ) -> None:
        """注册工具

        Args:
            name: 工具名称
            func: 工具函数 (必须是 async 函数)
            schema: OpenAI Function Calling 格式的 schema
            description: 工具描述
        """
        self.tools[name] = ToolDefinition(
            name=name,
            description=description or schema.get("function", {}).get("description", ""),
            func=func,
            schema=schema
        )
        logger.debug(f"Agent {self.name} 注册工具: {name}")

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """获取所有工具的 OpenAI Function Calling 定义"""
        return [tool.schema for tool in self.tools.values()]

    def set_step_callback(self, callback: Callable[[ReActStep], None]) -> None:
        """设置步骤回调，用于实时监控 Agent 执行"""
        self._on_step_callback = callback

    async def _log_action(
        self,
        context: AgentContext,
        tool_name: str,
        args: Dict[str, Any],
        result: Any
    ) -> None:
        """记录工具调用到数据库

        Args:
            context: Agent 上下文
            tool_name: 工具名称
            args: 工具参数
            result: 执行结果
        """
        if self.run_service:
            try:
                await self.run_service.log_action(
                    run_id=context.run_id,
                    tool=tool_name,
                    arguments=args,
                    result=result if isinstance(result, dict) else {"output": str(result)[:500]}
                )
            except Exception as e:
                logger.warning(f"记录工具调用失败: {e}")

    async def run(
        self,
        context: AgentContext,
        user_input: str,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> str:
        """执行 ReAct 循环

        Args:
            context: Agent 上下文
            user_input: 用户输入
            temperature: LLM 温度参数

        Returns:
            str: Agent 最终响应
        """
        logger.info(f"Agent {self.name} 开始执行", extra={
            "run_id": context.run_id,
            "session_id": context.session_id
        })

        self._status = AgentStatus.THINKING
        self._steps = []

        # 初始化消息历史
        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": user_input}
        ]

        tool_definitions = self.get_tool_definitions() if self.tools else None
        final_response = ""
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            current_step = ReActStep(step_number=iteration)

            # ========== THINK: 调用 LLM 进行推理 ==========
            self._status = AgentStatus.THINKING
            try:
                response = await self.llm.chat_completion(
                    messages=messages,
                    tools=tool_definitions,
                    tool_choice="auto" if tool_definitions else "none",
                    temperature=temperature,
                )
            except Exception as e:
                logger.error(f"Agent {self.name} LLM 调用失败: {e}")
                self._status = AgentStatus.ERROR
                current_step.success = False
                return f"处理请求时发生错误: {str(e)}"

            current_step.thought = response.content or ""

            # 记录 assistant 消息
            assistant_message: Dict[str, Any] = {
                "role": "assistant",
                "content": response.content,
            }
            if response.tool_calls:
                assistant_message["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": tc["function"]
                    }
                    for tc in response.tool_calls
                ]
            messages.append(assistant_message)

            # ========== ACT: 执行工具调用 ==========
            if response.tool_calls:
                self._status = AgentStatus.ACTING

                for tool_call in response.tool_calls:
                    func_name = tool_call["function"]["name"]
                    func_args_str = tool_call["function"]["arguments"]
                    call_id = tool_call["id"]

                    current_step.action = func_name

                    try:
                        func_args = json.loads(func_args_str)
                        current_step.action_input = func_args

                        logger.info(f"Agent {self.name} 执行工具: {func_name}", extra={
                            "args": func_args,
                            "run_id": context.run_id
                        })

                        # 执行工具
                        if func_name in self.tools:
                            result = await self._execute_tool(
                                func_name, func_args, context
                            )
                            result_str = json.dumps(result, ensure_ascii=False)

                            # 提取创建的元素 ID
                            if isinstance(result, dict):
                                if result.get("element_id"):
                                    context.created_element_ids.append(result["element_id"])
                                if result.get("arrow_id"):
                                    context.created_element_ids.append(result["arrow_id"])
                        else:
                            result = {"status": "error", "message": f"工具 {func_name} 不存在"}
                            result_str = json.dumps(result, ensure_ascii=False)

                        # 记录工具调用
                        await self._log_action(context, func_name, func_args, result)

                        # 记录到上下文
                        context.tool_results.append({
                            "tool": func_name,
                            "args": func_args,
                            "result": result_str[:1000]  # 限制长度
                        })

                    except json.JSONDecodeError as e:
                        result_str = json.dumps({
                            "status": "error",
                            "message": f"参数解析失败: {str(e)}"
                        }, ensure_ascii=False)
                        current_step.success = False
                    except Exception as e:
                        logger.error(f"工具 {func_name} 执行失败: {e}\n{traceback.format_exc()}")
                        result_str = json.dumps({
                            "status": "error",
                            "message": f"执行失败: {str(e)}"
                        }, ensure_ascii=False)
                        current_step.success = False

                    # ========== OBSERVE: 记录观察结果 ==========
                    self._status = AgentStatus.OBSERVING
                    current_step.observation = result_str

                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": result_str
                    })

                # 记录步骤并继续循环
                self._steps.append(current_step)
                if self._on_step_callback:
                    self._on_step_callback(current_step)
                continue

            # ========== COMPLETE: 无工具调用，任务完成 ==========
            self._steps.append(current_step)
            if self._on_step_callback:
                self._on_step_callback(current_step)

            final_response = response.content or ""
            break

        self._status = AgentStatus.COMPLETED
        logger.info(f"Agent {self.name} 执行完成", extra={
            "run_id": context.run_id,
            "iterations": iteration,
            "tools_called": len(context.tool_results),
            "elements_created": len(context.created_element_ids)
        })

        return final_response

    async def _execute_tool(
        self,
        name: str,
        args: Dict[str, Any],
        context: AgentContext
    ) -> Any:
        """执行已注册的工具

        Args:
            name: 工具名称
            args: 工具参数
            context: Agent 上下文

        Returns:
            工具执行结果
        """
        tool = self.tools[name]
        func = tool.func

        # 检查函数是否接受 context 参数
        import inspect
        sig = inspect.signature(func)
        if "context" in sig.parameters:
            return await func(**args, context=context)
        return await func(**args)

    def _build_system_prompt(self) -> str:
        """构建完整的系统提示词

        子类可以重写此方法来定制提示词。
        """
        return self.system_prompt


class PlanningAgent(BaseAgent):
    """支持规划的 Agent 基类

    在执行前先进行任务规划，将复杂任务分解为子任务。

    Attributes:
        enable_planning: 是否启用规划功能
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
        max_iterations: int = BaseAgent.DEFAULT_MAX_ITERATIONS,
        run_service: Optional["AgentRunService"] = None,
        enable_planning: bool = True,
    ):
        """初始化规划型 Agent

        Args:
            name: Agent 名称
            role: Agent 角色
            llm_client: LLM 客户端
            system_prompt: 系统提示词
            max_iterations: 最大迭代次数
            run_service: 运行记录服务
            enable_planning: 是否启用规划
        """
        super().__init__(name, role, llm_client, system_prompt, max_iterations, run_service)
        self.enable_planning = enable_planning

    def _build_system_prompt(self) -> str:
        """构建包含规划指导的系统提示词"""
        base_prompt = super()._build_system_prompt()
        if self.enable_planning:
            return f"{base_prompt}\n\n{self.PLANNING_PROMPT_TEMPLATE}"
        return base_prompt
