"""模块名称: base
主要功能: Prompt 模板基类和装饰器

提供:
- PromptTemplate 基类：支持 Pydantic 数据验证
- register_template 装饰器：关联模板文件和宏名称
- 类型安全的模板渲染
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional, Type, TypeVar
import json as json_module
from datetime import datetime

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, PrivateAttr

from src.logger import get_logger

logger = get_logger(__name__)

# 模板目录
TEMPLATES_DIR = Path(__file__).parent / "templates"

# 创建 Jinja2 环境
env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    auto_reload=False,
)

T = TypeVar("T", bound="PromptTemplate")


def register_template(
    template_name: str, macro_name: Optional[str] = None
) -> Callable[[Type[T]], Type[T]]:
    """注册模板装饰器

    将 PromptTemplate 子类与指定的模板文件和宏关联。

    Args:
        template_name: 模板文件路径 (相对于 templates 目录)
        macro_name: 宏名称；如果为 None 则渲染整个模板

    Example:
        ```python
        @register_template("system.jinja2", "system_prompt")
        class SystemPrompt(PromptTemplate):
            agent_name: str
            role: str
            tools: List[Dict]
        ```
    """

    def decorator(cls: Type[T]) -> Type[T]:
        # 使用 PrivateAttr 设置私有属性
        cls._template_name = PrivateAttr(default=template_name)
        cls._macro_name = PrivateAttr(default=macro_name)
        # 同时存储原始值为类属性，便于访问
        cls._template_name_str = template_name  # type: ignore
        cls._macro_name_str = macro_name  # type: ignore
        return cls

    return decorator


class PromptTemplate(BaseModel):
    """提示模板基类

    所有 Prompt 模板类都应继承此基类。
    使用 Pydantic 进行参数验证，支持类型安全的模板渲染。

    Attributes:
        _template_name: 模板文件名 (由装饰器设置)
        _macro_name: 宏名称 (由装饰器设置；可选)

    Example:
        ```python
        @register_template("system.jinja2", "system_prompt")
        class SystemPrompt(PromptTemplate):
            agent_name: str
            role: str

        prompt = SystemPrompt(agent_name="Planner", role="绘图助手")
        text = prompt.render(env)
        ```
    """

    _template_name: str = PrivateAttr()
    _macro_name: Optional[str] = PrivateAttr()

    def render(self, template_env: Optional[Environment] = None) -> str:
        """渲染模板

        Args:
            template_env: Jinja2 环境；默认使用全局 env

        Returns:
            str: 渲染后的文本
        """
        if template_env is None:
            template_env = env

        # 使用类属性访问模板名和宏名
        template_name = getattr(self.__class__, "_template_name_str", None)
        macro_name = getattr(self.__class__, "_macro_name_str", None)

        if not template_name:
            raise ValueError(f"模板类 {self.__class__.__name__} 未注册模板文件")

        template = template_env.get_template(template_name)
        data = {k: v for k, v in self.model_dump().items() if not k.startswith("_")}

        if macro_name:
            # 如果指定了宏，调用对应的宏
            macro = getattr(template.module, macro_name, None)
            if macro is None:
                raise ValueError(f"模板 {template_name} 中未找到宏 {macro_name}")
            return macro(**data)

        # 否则直接渲染模板
        return template.render(**data)

    def to_json(self) -> Dict[str, Any]:
        """导出为 JSON 兼容的字典

        Returns:
            Dict: 模板参数字典
        """
        return self.model_dump(exclude_unset=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptTemplate":
        """从字典创建实例

        Args:
            data: 参数字典

        Returns:
            PromptTemplate: 模板实例
        """
        return cls(**data)


# 注册自定义过滤器
def _register_filters() -> None:
    """注册自定义 Jinja2 过滤器"""

    def format_list(items, style: str = "bullet") -> str:
        """格式化列表"""
        if style == "bullet":
            return "\n".join(f"- {item}" for item in items)
        elif style == "numbered":
            return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))
        elif style == "comma":
            return "; ".join(str(item) for item in items)  # 使用分号分隔
        return "\n".join(str(item) for item in items)

    def truncate(text: str, length: int = 100, suffix: str = "...") -> str:
        """截断文本"""
        if len(text) <= length:
            return text
        return text[: length - len(suffix)] + suffix

    def to_json(obj: Any, indent: int = 2) -> str:
        """转换为 JSON 字符串"""
        return json_module.dumps(obj, ensure_ascii=False, indent=indent)

    def code_block(code: str, lang: str = "") -> str:
        """包装为代码块"""
        return f"```{lang}\n{code}\n```"

    env.filters["format_list"] = format_list
    env.filters["truncate"] = truncate
    env.filters["to_json"] = to_json
    env.filters["code_block"] = code_block


# 注册全局变量
def _register_globals() -> None:
    """注册全局变量和函数"""

    env.globals["now"] = datetime.now
    env.globals["version"] = "1.1.0"


# 初始化
_register_filters()
_register_globals()
