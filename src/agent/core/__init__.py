"""包名称: core
功能说明: Agent 核心组件

包含 Agent 系统的核心实现:
- agent: BaseAgent 基类和 ReAct 循环
- llm: LLM 客户端
- tools: 工具注册表
- errors: 异常定义
- json_parser: JSON 解析和修复
"""

from src.agent.core.agent import BaseAgent, PlanningAgent, AgentContext, AgentConfig
from src.agent.core.llm import LLMClient, LLMResponse
from src.agent.core.tools import registry, ToolRegistry, ToolCategory
from src.agent.core.errors import (
    AIEngineError,
    LLMError,
    ToolError,
    RoomError,
    AgentError,
    ValidationError,
    ErrorCode,
    RetryConfig,
    handle_agent_errors,
    error_context,
)
from src.agent.core.json_parser import (
    parse_json_safe,
    parse_llm_response,
    parse_tool_call_args,
    extract_json_from_text,
)

__all__ = [
    # Agent
    "BaseAgent",
    "PlanningAgent",
    "AgentContext",
    "AgentConfig",
    # LLM
    "LLMClient",
    "LLMResponse",
    # Tools
    "registry",
    "ToolRegistry",
    "ToolCategory",
    # Errors
    "AIEngineError",
    "LLMError",
    "ToolError",
    "RoomError",
    "AgentError",
    "ValidationError",
    "ErrorCode",
    "RetryConfig",
    "handle_agent_errors",
    "error_context",
    # JSON
    "parse_json_safe",
    "parse_llm_response",
    "parse_tool_call_args",
    "extract_json_from_text",
]
