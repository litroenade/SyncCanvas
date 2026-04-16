"""Typed application configuration schema."""


import secrets
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ExtraField(BaseModel):
    is_secret: bool = False
    is_textarea: bool = False
    is_hidden: bool = False
    placeholder: str = ""
    overridable: bool = False
    required: bool = False
    ref_model_groups: bool = False
    model_type: str = ""
    enable_toggle: str = ""
    is_need_restart: bool = False
    sub_item_name: str = ""
    enum: Optional[List[str]] = None


class SecurityConfig(BaseModel):
    secret_key: str = Field(
        default_factory=lambda: secrets.token_hex(32),
        json_schema_extra=ExtraField(is_secret=True, is_hidden=True).model_dump(),
    )


class ServerConfig(BaseModel):
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    allowed_origins: List[str] = Field(default_factory=lambda: ["*"])


class DatabaseConfig(BaseModel):
    url: str = Field(default="sqlite:///./data/sync_canvas.db")
    echo: bool = Field(default=False)


class ModelConfig(BaseModel):
    provider: str
    model: str
    base_url: str
    api_key: str = Field(
        ...,
        json_schema_extra=ExtraField(is_secret=True).model_dump(),
    )
    model_type: str = Field(default="chat")
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    extra_body: Optional[str] = Field(
        default=None,
        json_schema_extra=ExtraField(is_textarea=True).model_dump(),
    )
    enable_cot: bool = Field(default=False)


class ModelGroup(BaseModel):
    name: str
    chat_model: ModelConfig
    embedding_model: Optional[ModelConfig] = None


class AIProviderConfig(BaseModel):
    provider: str = Field(default="siliconflow")
    model: str = Field(default="Qwen/Qwen2.5-14B-Instruct")
    base_url: str = Field(default="https://api.siliconflow.cn/v1")
    api_key: str = Field(
        default="",
        json_schema_extra=ExtraField(is_secret=True, placeholder="sk-xxx").model_dump(),
    )
    fallback_provider: str = Field(default="openai")
    fallback_model: str = Field(default="gpt-4o-mini")
    fallback_base_url: str = Field(default="https://api.openai.com/v1")
    fallback_api_key: str = Field(
        default="",
        json_schema_extra=ExtraField(is_secret=True, placeholder="sk-xxx").model_dump(),
    )
    model_groups: Dict[str, ModelGroup] = Field(default_factory=dict)
    current_model_group: str = Field(
        default="",
        json_schema_extra=ExtraField(ref_model_groups=True).model_dump(),
    )
    tool_choice: str = Field(default="auto")
    max_tool_calls: int = Field(default=10)


class LoggingConfig(BaseModel):
    level: str = Field(default="INFO")
    colorize: bool = Field(default=True)
    show_time: bool = Field(default=True)
    file: Optional[str] = None
    exclude_frontend: bool = Field(default=False)
    frontend_level: str = Field(default="WARNING")
    agent_level: str = Field(default="DEBUG")


class CanvasTheme(BaseModel):
    stroke: str = Field(default="#1e1e1e")
    background: str = Field(default="#a5d8ff")
    text: str = Field(default="#1e1e1e")
    arrow: str = Field(default="#374151")


class CanvasConfig(BaseModel):
    node_width: float = Field(default=200.0)
    node_height: float = Field(default=80.0)
    ellipse_width: float = Field(default=160.0)
    ellipse_height: float = Field(default=60.0)
    diamond_size: float = Field(default=140.0)
    base_horizontal_gap: float = Field(default=80.0)
    base_vertical_gap: float = Field(default=100.0)
    gap_scale_factor: float = Field(default=0.1)
    max_gap_scale: float = Field(default=2.0)
    start_x: float = Field(default=400.0)
    start_y: float = Field(default=100.0)
    font_size: int = Field(default=18)
    font_family: int = Field(default=1)
    pathfinding_grid_size: float = Field(default=10.0)
    pathfinding_obstacle_padding: float = Field(default=25.0)
    pathfinding_max_iterations: int = Field(default=2000)
    pathfinding_turn_penalty: float = Field(default=0.5)
    light_theme: CanvasTheme = Field(default_factory=CanvasTheme)
    dark_theme: CanvasTheme = Field(
        default_factory=lambda: CanvasTheme(
            stroke="#f1f5f9",
            background="#1e3a5f",
            text="#ffffff",
            arrow="#94a3b8",
        )
    )

    def get_theme_colors(self, theme: str = "light") -> dict:
        if theme == "dark":
            return self.dark_theme.model_dump()
        return self.light_theme.model_dump()

    def calculate_dynamic_gaps(self, node_count: int) -> tuple[float, float]:
        factor = 1.0 + max(0, node_count - 5) * self.gap_scale_factor
        factor = min(factor, self.max_gap_scale)
        return self.base_horizontal_gap * factor, self.base_vertical_gap * factor


class AppConfig(BaseModel):
    version: str = "0.1.1"
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    ai: AIProviderConfig = Field(default_factory=AIProviderConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    canvas: CanvasConfig = Field(default_factory=CanvasConfig)

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        parts = value.split(".")
        if len(parts) != 3 or any(not part.isdigit() for part in parts):
            raise ValueError("version must be formatted as x.x.x")
        return value


__all__ = [
    "AIProviderConfig",
    "AppConfig",
    "CanvasConfig",
    "CanvasTheme",
    "DatabaseConfig",
    "ExtraField",
    "LoggingConfig",
    "ModelConfig",
    "ModelGroup",
    "SecurityConfig",
    "ServerConfig",
]
