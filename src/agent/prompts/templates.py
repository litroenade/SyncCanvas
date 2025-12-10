"""模块名称: templates
主要功能: Prompt 模板类定义

提供类型安全的模板类，每个类通过 register_template 装饰器关联模板文件和宏名称。
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.agent.prompts.base import PromptTemplate, register_template


# ==================== 系统提示词模板 ====================


@register_template("system.jinja2", "system_prompt")
class SystemPrompt(PromptTemplate):
    """系统提示词模板

    用于生成 Agent 的基础系统提示词。

    Attributes:
        agent_name: Agent 名称
        role: Agent 角色描述
        tools: 可用工具列表
        canvas_info: 画布状态信息 (可选)
    """

    agent_name: str
    role: str
    tools: List[Dict[str, Any]] = []
    canvas_info: Optional[Dict[str, Any]] = None


@register_template("system.jinja2", "response_format")
class ResponseFormat(PromptTemplate):
    """响应格式模板

    用于生成 JSON 响应格式说明。
    """  # 无具体实现，继承自 PromptTemplate


@register_template("system.jinja2", "thinking_chain")
class ThinkingChain(PromptTemplate):
    """思维链模板

    用于生成思维链分析提示。

    Attributes:
        user_request: 用户请求内容
    """

    user_request: str


@register_template("system.jinja2", "tool_description")
class ToolDescription(PromptTemplate):
    """工具描述模板

    用于生成单个工具的详细说明。

    Attributes:
        tool: 工具信息字典
    """

    tool: Dict[str, Any]


# ==================== 历史消息模板 ====================


@register_template("history.jinja2", "history_context")
class HistoryContext(PromptTemplate):
    """历史上下文模板

    用于生成当前执行上下文信息。

    Attributes:
        tool_results: 工具执行结果列表
        created_element_ids: 已创建的元素 ID 列表
        current_time: 当前时间字符串
    """

    tool_results: List[Dict[str, Any]] = []
    created_element_ids: List[str] = []
    current_time: str = ""


@register_template("history.jinja2", "format_messages")
class FormatMessages(PromptTemplate):
    """格式化消息模板

    用于格式化历史对话记录。

    Attributes:
        messages: 消息列表
        max_messages: 最大消息数量
    """

    messages: List[Dict[str, str]] = []
    max_messages: int = 10


@register_template("history.jinja2", "debug_prompt")
class DebugPrompt(PromptTemplate):
    """调试提示模板

    用于生成错误调试提示。

    Attributes:
        error_type: 错误类型
        error_message: 错误信息
        code_output: 代码输出 (可选)
    """

    error_type: str
    error_message: str
    code_output: Optional[str] = None


@register_template("history.jinja2", "continuation_prompt")
class ContinuationPrompt(PromptTemplate):
    """继续执行提示模板

    用于生成继续执行的提示。

    Attributes:
        previous_action: 上一步操作
        result_summary: 结果摘要
    """

    previous_action: str
    result_summary: str


@register_template("history.jinja2", "element_summary")
class ElementSummary(PromptTemplate):
    """元素摘要模板

    用于生成画布元素摘要表格。

    Attributes:
        elements: 元素列表
    """

    elements: List[Dict[str, Any]] = []


# ==================== 导出 ====================


# 方便导入的快捷函数
def render_system_prompt(
    agent_name: str,
    role: str,
    tools: List[Dict[str, Any]] = None,
    canvas_info: Optional[Dict[str, Any]] = None,
) -> str:
    """渲染系统提示词"""
    return SystemPrompt(
        agent_name=agent_name,
        role=role,
        tools=tools or [],
        canvas_info=canvas_info,
    ).render()


def render_history_context(
    tool_results: List[Dict[str, Any]] = None,
    created_element_ids: List[str] = None,
    current_time: str = "",
) -> str:
    """渲染历史上下文"""

    if not current_time:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return HistoryContext(
        tool_results=tool_results or [],
        created_element_ids=created_element_ids or [],
        current_time=current_time,
    ).render()


def render_thinking_chain(user_request: str) -> str:
    """渲染思维链"""
    return ThinkingChain(user_request=user_request).render()
