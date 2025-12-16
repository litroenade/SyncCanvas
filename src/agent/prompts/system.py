"""模块名称: system
主要功能: 系统提示词模板类
"""

from typing import Any, Dict, List, Optional

from src.agent.prompts.base import PromptTemplate, register_template


@register_template("system.jinja2", "system_prompt")
class SystemPrompt(PromptTemplate):
    """系统提示词模板"""

    agent_name: str
    role: str
    tools: List[Dict[str, Any]] = []
    canvas_info: Optional[Dict[str, Any]] = None
    enable_cot: bool = True  # 启用思维链


@register_template("system.jinja2", "response_format")
class ResponseFormat(PromptTemplate):
    """响应格式模板"""


@register_template("system.jinja2", "thinking_chain")
class ThinkingChain(PromptTemplate):
    """思维链模板"""

    user_request: str


@register_template("system.jinja2", "tool_description")
class ToolDescription(PromptTemplate):
    """工具描述模板"""

    tool: Dict[str, Any]
