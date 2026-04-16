"""Prompt template base helpers."""

from pathlib import Path
from typing import Callable, Optional, Type, TypeVar

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, PrivateAttr

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    auto_reload=False,
)

T = TypeVar("T", bound="PromptTemplate")


def register_template(
    template_name: str,
    macro_name: Optional[str] = None,
) -> Callable[[Type[T]], Type[T]]:
    def decorator(cls: Type[T]) -> Type[T]:
        cls._template_name = PrivateAttr(default=template_name)
        cls._macro_name = PrivateAttr(default=macro_name)
        cls._template_name_str = template_name  # type: ignore[attr-defined]
        cls._macro_name_str = macro_name  # type: ignore[attr-defined]
        return cls

    return decorator


class PromptTemplate(BaseModel):
    """Base class for typed prompt templates."""

    _template_name: str = PrivateAttr()
    _macro_name: Optional[str] = PrivateAttr()

    def render(self, template_env: Optional[Environment] = None) -> str:
        template_env = template_env or env
        template = template_env.get_template(self.__class__._template_name_str)  # type: ignore[attr-defined]
        data = {
            key: value
            for key, value in self.model_dump().items()
            if not key.startswith("_")
        }

        macro_name = self.__class__._macro_name_str  # type: ignore[attr-defined]
        if macro_name:
            macro = getattr(template.module, macro_name)
            return macro(**data)

        return template.render(**data)
