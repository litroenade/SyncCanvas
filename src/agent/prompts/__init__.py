"""模块名称: prompts
主要功能: Jinja2 模板管理系统

参照 nekro-agent 风格:
- base.py: 核心 PromptTemplate 基类
- system.py: 系统提示模板
- history.py: 历史上下文模板
- reflection.py: 自反思模板
- manager.py: 模板管理器
"""

from src.agent.prompts.base import PromptTemplate, register_template, env
from src.agent.prompts.manager import PromptManager, prompt_manager

# 系统提示模板
from src.agent.prompts.system import (
    SystemPrompt,
    ResponseFormat,
    ThinkingChain,
    ToolDescription,
)

# 历史上下文模板
from src.agent.prompts.history import (
    HistoryContext,
    FormatMessages,
    DebugPrompt,
    ContinuationPrompt,
    ElementSummary,
)

# 自反思模板
from src.agent.prompts.reflection import (
    SelfReflection,
    ProgressSummary,
)

__all__ = [
    # 核心
    "PromptTemplate",
    "register_template",
    "env",
    "PromptManager",
    "prompt_manager",
    # 系统
    "SystemPrompt",
    "ResponseFormat",
    "ThinkingChain",
    "ToolDescription",
    # 历史
    "HistoryContext",
    "FormatMessages",
    "DebugPrompt",
    "ContinuationPrompt",
    "ElementSummary",
    # 反思
    "SelfReflection",
    "ProgressSummary",
]
