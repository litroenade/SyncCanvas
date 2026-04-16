"""Prompt template manager."""

from pathlib import Path
from typing import List, Optional

from jinja2 import TemplateNotFound

from src.application.ai.prompts.base import TEMPLATES_DIR, env
from src.infra.logging import get_logger

logger = get_logger(__name__)


class PromptManager:
    """Render and inspect prompt templates."""

    def __init__(self, templates_dir: Optional[Path] = None):
        self._templates_dir = templates_dir or TEMPLATES_DIR
        self._env = env
        self._string_templates: dict[str, str] = {}
        logger.debug(
            "Prompt manager initialized with templates_dir=%s",
            self._templates_dir,
        )

    def register(self, name: str, template_str: str) -> None:
        self._string_templates[name] = template_str
        logger.debug("Registered in-memory prompt template: %s", name)

    def render(self, template_name: str, **kwargs) -> str:
        try:
            if template_name in self._string_templates:
                template = self._env.from_string(self._string_templates[template_name])
            else:
                template = self._env.get_template(template_name)
            return template.render(**kwargs)
        except TemplateNotFound:
            logger.error("Prompt template not found: %s", template_name)
            raise
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to render template %s: %s", template_name, exc)
            raise

    def render_string(self, template_str: str, **kwargs) -> str:
        template = self._env.from_string(template_str)
        return template.render(**kwargs)

    def list_templates(self) -> List[str]:
        templates: list[str] = []
        if self._templates_dir.exists():
            for template_file in self._templates_dir.glob("*.jinja2"):
                templates.append(template_file.name)
            for template_file in self._templates_dir.glob("*.j2"):
                templates.append(template_file.name)
        templates.extend(self._string_templates.keys())
        return sorted(templates)

    def get_template_source(self, template_name: str) -> Optional[str]:
        if template_name in self._string_templates:
            return self._string_templates[template_name]

        template_path = self._templates_dir / template_name
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
        return None


prompt_manager = PromptManager()
