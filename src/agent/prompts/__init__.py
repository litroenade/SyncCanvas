"""模块名称: prompts
主要功能: Jinja2 模板管理系统

提供 Prompt 模板的加载、渲染和管理功能。
"""

from src.agent.prompts.manager import PromptManager, prompt_manager

__all__ = ["PromptManager", "prompt_manager"]

