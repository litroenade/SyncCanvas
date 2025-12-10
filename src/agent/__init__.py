"""包名称: agent
功能说明: AI Agent 核心模块

提供 ReAct 架构的 AI Agent 实现,包括:
- PlannerAgent: 主协调 Agent,处理用户请求
- CanvaserAgent: 专业绘图 Agent,负责流程图等绘制
- BaseAgent: Agent 基类,实现 ReAct 循环
- 工具注册和执行系统
- Prompt 模板管理

Example:
    from src.agent import PlannerAgent, AgentContext

    agent = PlannerAgent(llm_client)
    context = AgentContext(run_id=1, session_id="room_123")
    result = await agent.run(context, "画一个流程图")
"""

from src.agent.agents.planner import PlannerAgent
from src.agent.agents.canvaser import CanvaserAgent
from src.agent.core.agent import BaseAgent, AgentContext, AgentConfig
from src.agent.core.errors import (
    AIEngineError,
    LLMError,
    ToolError,
    RoomError,
    AgentError,
    ValidationError,
    ErrorCode,
)
from src.agent.core.llm import LLMClient
from src.agent.core.tools import registry, ToolCategory

__all__ = [
    # Agents
    "PlannerAgent",
    "CanvaserAgent",
    "BaseAgent",
    # Context & Config
    "AgentContext",
    "AgentConfig",
    # Errors
    "AIEngineError",
    "LLMError",
    "ToolError",
    "RoomError",
    "AgentError",
    "ValidationError",
    "ErrorCode",
    # LLM
    "LLMClient",
    # Tools
    "registry",
    "ToolCategory",
]
