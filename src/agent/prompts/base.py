"""模块名称: base
主要功能: Prompt 模板基类和装饰器
"""

from pathlib import Path
from typing import Callable, Optional, Type, TypeVar

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, PrivateAttr

# 模板目录
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Jinja2 环境
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

    Args:
        template_name: 模板文件路径
        macro_name: 宏名称，可选
    """

    def decorator(cls: Type[T]) -> Type[T]:
        cls._template_name = PrivateAttr(default=template_name)
        cls._macro_name = PrivateAttr(default=macro_name)
        cls._template_name_str = template_name  # type: ignore
        cls._macro_name_str = macro_name  # type: ignore
        return cls

    return decorator


class PromptTemplate(BaseModel):
    """提示模板基类"""

    _template_name: str = PrivateAttr()
    _macro_name: Optional[str] = PrivateAttr()

    def render(self, template_env: Optional[Environment] = None) -> str:
        """渲染模板"""
        if template_env is None:
            template_env = env

        template = template_env.get_template(self.__class__._template_name_str)  # type: ignore
        data = {k: v for k, v in self.model_dump().items() if not k.startswith("_")}

        macro_name = self.__class__._macro_name_str  # type: ignore
        if macro_name:
            macro = getattr(template.module, macro_name)
            return macro(**data)

        return template.render(**data)
