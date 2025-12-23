"""包名称: agent
功能说明: SyncCanvas AI Agent 模块
"""

from src.agent.core import (
    BaseAgent,
    PlanningAgent,
    AgentConfig,
    ReActStep,
    RoomLockManager,
    ToolDefinition,
    AgentContext,
    AgentMetrics,
    AgentStatus,
    LLMClient,
    LLMResponse,
    registry,
    ToolCategory,
    ToolMetadata,
    AIEngineError,
    LLMError,
    ToolError,
    AgentError,
    CanvasAgent,
    AgentStateMachine,
    AgentState,
    TransactionError,
    parse_tool_call_args,
    RetryPolicy,
    ErrorRecoveryManager,
)


def __getattr__(name: str):
    """延迟导入以避免循环依赖"""
    if name == "LibraryService":
        from src.agent.lib.library import LibraryService
        return LibraryService
    elif name == "library_service":
        from src.agent.lib.library import library_service
        return library_service
    elif name == "IGitService":
        from src.agent.lib.version_control import IGitService
        return IGitService
    elif name == "MemoryService":
        from src.agent.memory import MemoryService
        return MemoryService
    elif name == "memory_service":
        from src.agent.memory import memory_service
        return memory_service
    elif name == "CanvasStateProvider":
        from src.agent.memory import CanvasStateProvider
        return CanvasStateProvider
    elif name == "canvas_state_provider":
        from src.agent.memory import canvas_state_provider
        return canvas_state_provider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseAgent",
    "PlanningAgent",
    "AgentConfig",
    "ReActStep",
    "RoomLockManager",
    "ToolDefinition",
    "AgentContext",
    "AgentMetrics",
    "AgentStatus",
    "LLMClient",
    "LLMResponse",
    "registry",
    "ToolCategory",
    "ToolMetadata",
    "AIEngineError",
    "LLMError",
    "ToolError",
    "AgentError",
    "CanvasAgent",
    "AgentStateMachine",
    "AgentState",
    "TransactionError",
    "parse_tool_call_args",
    "RetryPolicy",
    "ErrorRecoveryManager",
]

# 延迟加载的组件，不在 __all__ 中声明以避免 linter 警告
# 可通过 __getattr__ 访问: LibraryService, library_service, IGitService
# MemoryService, memory_service, CanvasStateProvider, canvas_state_provider
