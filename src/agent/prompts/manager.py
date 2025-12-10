"""模块名称: manager
主要功能: Prompt 模板管理器

使用 Jinja2 模板引擎管理和渲染 AI Prompt。
支持模板继承、变量替换、条件渲染等功能。
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, List

from jinja2 import (
    Environment,
    FileSystemLoader,
    BaseLoader,
    TemplateNotFound,
    select_autoescape,
)

from src.logger import get_logger

logger = get_logger(__name__)

# 模板目录
TEMPLATES_DIR = Path(__file__).parent / "templates"


class StringLoader(BaseLoader):
    """字符串模板加载器
    
    支持直接从字符串加载模板。
    """

    def __init__(self):
        self._templates: Dict[str, str] = {}

    def add_template(self, name: str, source: str) -> None:
        """添加字符串模板"""
        self._templates[name] = source

    def get_source(self, environment: Environment, template: str):
        if template in self._templates:
            source = self._templates[template]
            return source, None, lambda: True
        raise TemplateNotFound(template)


class PromptManager:
    """Prompt 模板管理器
    
    管理和渲染 Jinja2 模板，支持:
    - 文件模板加载
    - 字符串模板注册
    - 模板继承和包含
    - 自定义过滤器和函数
    
    Example:
        ```python
        pm = PromptManager()
        
        # 渲染文件模板
        prompt = pm.render("teacher.jinja2", tools=["tool1", "tool2"])
        
        # 注册并渲染字符串模板
        pm.register("custom", "Hello {{ name }}!")
        prompt = pm.render("custom", name="World")
        ```
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """初始化模板管理器
        
        Args:
            templates_dir: 模板文件目录，默认为 prompts/templates
        """
        self._templates_dir = templates_dir or TEMPLATES_DIR
        self._string_loader = StringLoader()

        # 确保模板目录存在
        self._templates_dir.mkdir(parents=True, exist_ok=True)

        # 创建 Jinja2 环境
        self._env = Environment(
            loader=FileSystemLoader(str(self._templates_dir)),
            autoescape=select_autoescape(disabled_extensions=["jinja2", "j2"]),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        # 注册自定义过滤器
        self._register_filters()

        # 注册全局变量
        self._register_globals()

        logger.debug("Prompt 模板管理器已初始化，模板目录: %s", self._templates_dir)

    def _register_filters(self) -> None:
        """注册自定义过滤器"""

        # 列表格式化
        def format_list(items: List[str], style: str = "bullet") -> str:
            if style == "bullet":
                return "\n".join(f"- {item}" for item in items)
            elif style == "numbered":
                return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
            elif style == "comma":
                return ", ".join(items)
            return "\n".join(items)

        # 截断文本
        def truncate(text: str, length: int = 100, suffix: str = "...") -> str:
            if len(text) <= length:
                return text
            return text[:length - len(suffix)] + suffix

        # JSON 格式化
        def to_json(obj: Any, indent: int = 2) -> str:

            return json.dumps(obj, ensure_ascii=False, indent=indent)

        # 代码块格式化
        def code_block(code: str, lang: str = "") -> str:
            return f"```{lang}\n{code}\n```"

        self._env.filters["format_list"] = format_list
        self._env.filters["truncate"] = truncate
        self._env.filters["to_json"] = to_json
        self._env.filters["code_block"] = code_block

    def _register_globals(self) -> None:
        """注册全局变量和函数"""

        self._env.globals["now"] = datetime.now
        self._env.globals["version"] = "1.1.0"

    def register(self, name: str, template_str: str) -> None:
        """注册字符串模板
        
        Args:
            name: 模板名称
            template_str: 模板字符串
        """
        self._string_loader.add_template(name, template_str)
        logger.debug("注册字符串模板: %s", name)

    def render(self, template_name: str, **kwargs) -> str:
        """渲染模板
        
        Args:
            template_name: 模板名称 (文件名或注册的字符串模板名)
            **kwargs: 模板变量
            
        Returns:
            str: 渲染后的文本
            
        Raises:
            TemplateNotFound: 模板不存在
        """
        try:
            # 先尝试从字符串模板加载
            if template_name in self._string_loader._templates:
                template = self._env.from_string(
                    self._string_loader._templates[template_name]
                )
            else:
                # 从文件加载
                template = self._env.get_template(template_name)

            return template.render(**kwargs)

        except TemplateNotFound:
            logger.error("模板不存在: %s", template_name)
            raise
        except Exception as e:
            logger.error("渲染模板失败: %s, 错误: %s", template_name, e)
            raise

    def render_string(self, template_str: str, **kwargs) -> str:
        """直接渲染字符串模板
        
        Args:
            template_str: 模板字符串
            **kwargs: 模板变量
            
        Returns:
            str: 渲染后的文本
        """
        template = self._env.from_string(template_str)
        return template.render(**kwargs)

    def list_templates(self) -> List[str]:
        """列出所有可用模板
        
        Returns:
            list: 模板名称列表
        """
        templates = []

        # 文件模板
        if self._templates_dir.exists():
            for f in self._templates_dir.glob("*.jinja2"):
                templates.append(f.name)
            for f in self._templates_dir.glob("*.j2"):
                templates.append(f.name)

        # 字符串模板
        templates.extend(self._string_loader._templates.keys())

        return sorted(templates)

    def get_template_source(self, template_name: str) -> Optional[str]:
        """获取模板源码
        
        Args:
            template_name: 模板名称
            
        Returns:
            str: 模板源码，不存在则返回 None
        """
        # 字符串模板
        if template_name in self._string_loader._templates:
            return self._string_loader._templates[template_name]

        # 文件模板
        template_path = self._templates_dir / template_name
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")

        return None


# 全局实例
prompt_manager = PromptManager()
