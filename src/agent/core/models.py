from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from pydantic import BaseModel, Field


@dataclass
class ToolDefinition:
    """工具定义

    描述一个可被 Agent 调用的工具。

    Attributes:
        name: 工具名称
        description: 工具描述
        func: 工具函数
        schema: OpenAI Function Calling Schema
        timeout: 工具执行超时时间（秒）
        retries: 失败重试次数
    """

    name: str
    description: str
    func: Callable
    schema: Dict[str, Any]
    timeout: float = 30.0
    retries: int = 2


@dataclass
class ReActStep:
    """ReAct 单步记录

    记录 Agent 思考-行动-观察循环中的一步。

    Attributes:
        step_number: 步骤编号
        thought: 思考内容
        action: 执行的动作（工具名称）
        action_input: 动作输入参数
        observation: 观察结果
        success: 是否成功
        latency_ms: 延迟（毫秒）
    """

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
