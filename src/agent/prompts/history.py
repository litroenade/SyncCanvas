"""模块名称: history
主要功能: 历史消息和上下文模板类
"""

from typing import Any, Dict, List, Optional

from src.agent.prompts.base import PromptTemplate, register_template


@register_template("history.jinja2", "history_context")
class HistoryContext(PromptTemplate):
    """历史上下文模板"""

    tool_results: List[Dict[str, Any]] = []
    created_element_ids: List[str] = []
    current_time: str = ""


@register_template("history.jinja2", "format_messages")
class FormatMessages(PromptTemplate):
    """格式化消息模板"""

    messages: List[Dict[str, str]] = []
    max_messages: int = 10


@register_template("history.jinja2", "debug_prompt")
class DebugPrompt(PromptTemplate):
    """调试提示模板"""

    error_type: str
    error_message: str
    code_output: Optional[str] = None


@register_template("history.jinja2", "continuation_prompt")
class ContinuationPrompt(PromptTemplate):
    """继续执行提示模板"""

    previous_action: str
    result_summary: str


@register_template("history.jinja2", "element_summary")
class ElementSummary(PromptTemplate):
    """元素摘要模板"""

    elements: List[Dict[str, Any]] = []
