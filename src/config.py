"""模块名称: config
主要功能: 配置管理，基于 Pydantic 模型的类型安全配置系统
"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import List, Optional, Dict


from pydantic import BaseModel, Field, field_validator

try:
    import tomllib
except ImportError:
    import tomli as tomllib

import tomli_w

from src.logger import get_logger

logger = get_logger(__name__)

# 配置文件路径
CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
CONFIG_FILE = CONFIG_DIR / "config.toml"


# ==================== 配置字段元数据 ====================


class ExtraField(BaseModel):
    """配置字段扩展元数据

    用于向前端传递 UI 渲染相关信息。

    Attributes:
        is_secret: 敏感字段 (显示为密码框)
        is_textarea: 多行文本输入
        is_hidden: 隐藏字段 (不在 UI 显示)
        placeholder: 输入占位符
        overridable: 可被房间级配置覆盖
        required: 必填字段
        ref_model_groups: 引用模型组选择器
        model_type: 模型类型筛选 (chat/vision)
        enable_toggle: 依赖的开关字段名
        is_need_restart: 修改后需要重启服务
        sub_item_name: 列表项名称 (用于数组字段)
        enum: 枚举值列表 (下拉选择)
    """

    is_secret: bool = False  # 敏感字段 (显示为密码框)
    is_textarea: bool = False  # 多行文本输入
    is_hidden: bool = False  # 隐藏字段 (不在 UI 显示)
    placeholder: str = ""  # 输入占位符
    overridable: bool = False  # 可被房间级配置覆盖
    required: bool = False  # 必填字段
    ref_model_groups: bool = False  # 引用模型组选择器
    model_type: str = ""  # 模型类型筛选 (chat/vision)
    enable_toggle: str = ""  # 依赖的开关字段名
    is_need_restart: bool = False  # 修改后需要重启服务
    sub_item_name: str = ""  # 列表项名称 (用于数组字段)
    enum: Optional[List[str]] = None  # 枚举值列表 (下拉选择)


# ==================== 配置模型 ====================


class SecurityConfig(BaseModel):
    """安全配置"""

    secret_key: str = Field(
        default_factory=lambda: secrets.token_hex(32),
        title="密钥",
        description="应用安全密钥，用于 JWT 签名",
        json_schema_extra=ExtraField(is_secret=True, is_hidden=True).model_dump(),
    )
    admin_key: str = Field(
        default="admin",
        title="管理员密钥",
        description="管理员 API 访问密钥",
        json_schema_extra=ExtraField(is_secret=True).model_dump(),
    )


class ServerConfig(BaseModel):
    """服务器配置"""

    host: str = Field(
        default="0.0.0.0", title="监听地址", description="服务器监听的 IP 地址"
    )
    port: int = Field(default=8000, title="监听端口", description="服务器监听的端口号")
    allowed_origins: List[str] = Field(
        default=["*"], title="允许的跨域来源", description="CORS 允许的 Origin 列表"
    )


class DatabaseConfig(BaseModel):
    """数据库配置"""

    url: str = Field(
        default="sqlite:///./data/sync_canvas.db",
        title="数据库 URL",
        description="SQLAlchemy 数据库连接字符串",
    )
    echo: bool = Field(
        default=False, title="SQL 日志", description="是否打印 SQL 语句到日志"
    )


class ModelConfig(BaseModel):
    """单个模型配置"""

    provider: str = Field(..., title="提供商")
    model: str = Field(..., title="模型名称")
    base_url: str = Field(..., title="Base URL")
    api_key: str = Field(
        ..., title="API Key", json_schema_extra=ExtraField(is_secret=True).model_dump()
    )

    # 高级参数
    model_type: str = Field("chat", title="模型类型")
    temperature: Optional[float] = Field(None, title="Temperature")
    top_p: Optional[float] = Field(None, title="Top P")
    presence_penalty: Optional[float] = Field(None, title="Presence Penalty")
    frequency_penalty: Optional[float] = Field(None, title="Frequency Penalty")
    extra_body: Optional[str] = Field(
        None,
        title="额外参数",
        json_schema_extra=ExtraField(is_textarea=True).model_dump(),
    )
    enable_vision: bool = Field(True, title="视觉支持")
    enable_cot: bool = Field(False, title="外置思维链")


class AIProviderConfig(BaseModel):
    """AI 提供商配置"""

    provider: str = Field(
        default="siliconflow", title="主模型提供商", description="AI 服务提供商名称"
    )
    model: str = Field(
        default="Qwen/Qwen2.5-14B-Instruct",
        title="主模型名称",
        description="用于 Agent 推理的模型",
    )
    base_url: str = Field(
        default="https://api.siliconflow.cn/v1",
        title="API 地址",
        description="模型 API 端点 URL",
    )
    api_key: str = Field(
        default="",
        title="API 密钥",
        description="模型服务 API Key",
        json_schema_extra=ExtraField(is_secret=True, placeholder="sk-xxx").model_dump(),
    )

    # 备用提供商
    fallback_provider: str = Field(
        default="openai", title="备用提供商", description="主模型不可用时的备用提供商"
    )
    fallback_model: str = Field(
        default="gpt-4o-mini", title="备用模型", description="备用模型名称"
    )
    fallback_base_url: str = Field(
        default="https://api.openai.com/v1",
        title="备用 API 地址",
        description="备用模型 API 端点",
    )
    fallback_api_key: str = Field(
        default="",
        title="备用 API 密钥",
        description="备用模型服务 API Key",
        json_schema_extra=ExtraField(is_secret=True, placeholder="sk-xxx").model_dump(),
    )

    # 模型组管理
    model_groups: Dict[str, ModelConfig] = Field(
        default_factory=dict,
        title="模型组列表",
        description="自定义模型组配置",
    )

    # 当前使用的模型组
    current_model_group: str = Field(
        default="",
        title="当前模型组",
        description="选择要使用的预定义模型组",
        json_schema_extra=ExtraField(ref_model_groups=True).model_dump(),
    )

    # 工具调用配置
    tool_choice: str = Field(
        default="auto", title="工具选择模式", description="auto/required/none"
    )
    max_tool_calls: int = Field(
        default=10,
        title="最大工具调用数",
        description="单次 Agent 运行最大工具调用次数",
    )


class LoggingConfig(BaseModel):
    """日志配置"""

    level: str = "INFO"
    format: str = "[%(levelname).1s] %(name)s: %(message)s"
    show_time: bool = True
    colorize: bool = True
    file: Optional[str] = None


class AppConfig(BaseModel):
    """应用主配置

    基于 Pydantic 的配置模型，支持类型验证和默认值。
    """

    version: str = "1.0.0"
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    ai: AIProviderConfig = Field(default_factory=AIProviderConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """验证版本号格式 (x.x.x)"""
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("版本号格式必须为 x.x.x")
        for part in parts:
            if not part.isdigit():
                raise ValueError("版本号各部分必须为数字")
        return v


class ConfigManager:
    """配置管理器

    负责加载、保存和管理应用配置。
    """

    def __init__(self, config_file: Path = CONFIG_FILE):
        self._config_file = config_file
        self._config: Optional[AppConfig] = None
        self._last_mtime: float = 0.0
        self._ensure_config_dir()
        self._load()

    def _ensure_config_dir(self) -> None:
        """确保配置目录存在"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        """加载配置文件"""
        if not self._config_file.exists():
            # 创建默认配置
            self._config = AppConfig()
            self._save()
            logger.info("已创建默认配置文件: %s", self._config_file)
            return

        try:
            mtime = self._config_file.stat().st_mtime
            if mtime <= self._last_mtime and self._config is not None:
                return

            with self._config_file.open("rb") as f:
                raw = tomllib.load(f)

            # 处理旧版本号格式
            if "version" in raw and isinstance(raw["version"], int):
                raw["version"] = f"{raw['version']}.0.0"

            self._config = AppConfig(**raw)
            self._last_mtime = mtime
            logger.info("配置已加载 (v%s)", self._config.version)

        except Exception as e:  # pylint: disable=broad-except
            logger.error("加载配置失败: %s", e)
            self._config = AppConfig()

    def _save(self) -> None:
        """保存配置到文件"""
        if self._config is None:
            return

        try:
            data = self._config.model_dump()
            with self._config_file.open("wb") as f:
                tomli_w.dump(data, f)
            self._last_mtime = self._config_file.stat().st_mtime
        except Exception as e:  # pylint: disable=broad-except
            logger.error("保存配置失败: %s", e)

    def reload(self) -> None:
        """重新加载配置"""
        self._last_mtime = 0.0
        self._load()

    @property
    def config(self) -> AppConfig:
        """获取配置对象"""
        if self._config is None:
            self._load()
        return self._config  # type: ignore

    # ==================== 配置节访问 ====================

    @property
    def security(self) -> SecurityConfig:
        return self.config.security

    @property
    def server(self) -> ServerConfig:
        return self.config.server

    @property
    def database(self) -> DatabaseConfig:
        return self.config.database

    @property
    def ai(self) -> AIProviderConfig:
        return self.config.ai

    @property
    def logging(self) -> LoggingConfig:
        return self.config.logging

    # ==================== 便捷属性 (兼容旧代码) ====================

    @property
    def version(self) -> str:
        return self.config.version

    @property
    def secret_key(self) -> str:
        return self.config.security.secret_key

    @property
    def admin_key(self) -> str:
        return self.config.security.admin_key

    @property
    def host(self) -> str:
        return self.config.server.host

    @property
    def port(self) -> int:
        return self.config.server.port

    @property
    def allowed_origins(self) -> List[str]:
        return self.config.server.allowed_origins

    @property
    def database_url(self) -> str:
        return self.config.database.url

    @property
    def db_echo(self) -> bool:
        return self.config.database.echo

    # AI 配置
    @property
    def llm_provider(self) -> str:
        return self.config.ai.provider

    @property
    def llm_model(self) -> str:
        return self.config.ai.model

    @property
    def llm_base_url(self) -> str:
        return self.config.ai.base_url

    @property
    def llm_api_key(self) -> str:
        key = self.config.ai.api_key
        if not key:
            key = self.config.ai.fallback_api_key
        return key

    @property
    def llm_fallback_provider(self) -> str:
        return self.config.ai.fallback_provider

    @property
    def llm_fallback_model(self) -> str:
        return self.config.ai.fallback_model

    @property
    def llm_fallback_base_url(self) -> str:
        return self.config.ai.fallback_base_url

    @property
    def llm_fallback_api_key(self) -> str:
        return self.config.ai.fallback_api_key

    @property
    def llm_tool_choice(self) -> str:
        return self.config.ai.tool_choice

    @property
    def llm_max_tool_calls(self) -> int:
        return self.config.ai.max_tool_calls

    # 兼容旧属性名
    @property
    def openai_api_key(self) -> str:
        return self.config.ai.fallback_api_key

    @property
    def openai_base_url(self) -> str:
        return self.config.ai.fallback_base_url

    @property
    def openai_model(self) -> str:
        return self.config.ai.fallback_model


# 全局配置实例
config = ConfigManager()
