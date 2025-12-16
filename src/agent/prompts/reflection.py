"""模块名称: reflection
主要功能: ReAct 自反思模板类
"""

from typing import Any, Dict, List

from src.agent.prompts.base import PromptTemplate, register_template


@register_template("reflection.jinja2", "self_reflection")
class SelfReflection(PromptTemplate):
    """ReAct 循环自反思模板"""

    current_iteration: int
    max_iterations: int
    tool_results: List[Dict[str, Any]] = []
    created_element_ids: List[str] = []


@register_template("reflection.jinja2", "progress_summary")
class ProgressSummary(PromptTemplate):
    """进度摘要模板"""

    tool_results: List[Dict[str, Any]] = []
    created_element_ids: List[str] = []
