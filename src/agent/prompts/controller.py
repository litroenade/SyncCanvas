"""模块名称: controller
主要功能: 画布控制器模板类
"""

from src.agent.prompts.base import PromptTemplate, register_template


@register_template("controller.jinja2", "controller_system_prompt")
class ControllerPrompt(PromptTemplate):
    """画布控制器系统提示词模板"""

    canvas_summary: str = ""
    element_list: str = ""
