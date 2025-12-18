"""包名称: agent
功能说明: SyncCanvas AI Agent 模块

目录结构:
- base.py: Agent 基类和上下文
- llm.py: LLM 客户端
- errors.py: 异常定义
- registry.py: 工具注册表
- canvas_agent.py: CanvasAgent (主 Agent)
- canvas/: 画布模型和控制命令
- tools/: 工具集
- prompts/: Prompt 模板
"""

# 基础组件
from src.agent.base import BaseAgent, PlanningAgent, AgentContext, AgentConfig
from src.agent.llm import LLMClient, LLMResponse
from src.agent.registry import registry, ToolRegistry, ToolCategory
from src.agent.errors import AIEngineError, LLMError, ToolError, AgentError

# Canvas
from src.agent.canvas import (
    CanvasModel,
    CanvasElement,
    Command,
    CommandExecutor,
)

# Agent
from src.agent.canvas_agent import CanvasAgent

__all__ = [
    # Base
    "BaseAgent",
    "PlanningAgent",
    "AgentContext",
    "AgentConfig",
    "LLMClient",
    "LLMResponse",
    "registry",
    "ToolRegistry",
    "ToolCategory",
    # Errors
    "AIEngineError",
    "LLMError",
    "ToolError",
    "AgentError",
    # Canvas
    "CanvasModel",
    "CanvasElement",
    "Command",
    "CommandExecutor",
    # Agent
    "CanvasAgent",
]
