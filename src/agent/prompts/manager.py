"""模块名称: manager
主要功能: Prompt 模板管理器
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List

from jinja2 import TemplateNotFound

from src.agent.prompts.base import env, TEMPLATES_DIR
from src.logger import get_logger

logger = get_logger(__name__)


class PromptManager:
    """Prompt 模板管理器

    管理和渲染 Jinja2 模板，复用 base.py 的环境配置。

    Example:
        ```python
        pm = PromptManager()
        prompt = pm.render("planner.jinja2", tools=[...])
        ```
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """初始化模板管理器

        Args:
            templates_dir: 模板文件目录，默认为 prompts/templates
        """
        self._templates_dir = templates_dir or TEMPLATES_DIR
        self._env = env  # 复用 base.py 的环境
        self._string_templates: dict[str, str] = {}

        logger.debug("Prompt 模板管理器已初始化，模板目录: %s", self._templates_dir)

    def register(self, name: str, template_str: str) -> None:
        """注册字符串模板"""
        self._string_templates[name] = template_str
        logger.debug("注册字符串模板: %s", name)

    def render(self, template_name: str, **kwargs) -> str:
        """渲染模板

        Args:
            template_name: 模板名称 (文件名或注册的字符串模板名)
            **kwargs: 模板变量

        Returns:
            str: 渲染后的文本
        """
        try:
            # 先尝试从字符串模板加载
            if template_name in self._string_templates:
                template = self._env.from_string(self._string_templates[template_name])
            else:
                # 从文件加载
                template = self._env.get_template(template_name)

            return template.render(**kwargs)

        except TemplateNotFound:
            logger.error("模板不存在: %s", template_name)
            raise
        except Exception as e:  # pylint: disable=broad-except
            logger.error("渲染模板失败: %s, 错误: %s", template_name, e)
            raise

    def render_string(self, template_str: str, **kwargs) -> str:
        """直接渲染字符串模板"""
        template = self._env.from_string(template_str)
        return template.render(**kwargs)

    def list_templates(self) -> List[str]:
        """列出所有可用模板"""
        templates = []

        # 文件模板
        if self._templates_dir.exists():
            for f in self._templates_dir.glob("*.jinja2"):
                templates.append(f.name)
            for f in self._templates_dir.glob("*.j2"):
                templates.append(f.name)

        # 字符串模板
        templates.extend(self._string_templates.keys())

        return sorted(templates)

    def get_template_source(self, template_name: str) -> Optional[str]:
        """获取模板源码"""
        # 字符串模板
        if template_name in self._string_templates:
            return self._string_templates[template_name]

        # 文件模板
        template_path = self._templates_dir / template_name
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")

        return None


# 全局实例
prompt_manager = PromptManager()
