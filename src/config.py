from __future__ import annotations
import secrets
from pathlib import Path
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator
import tomllib
import tomli_w
from src.logger import get_logger

logger = get_logger(__name__)

# 配置文件路径
CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
CONFIG_FILE = CONFIG_DIR / "config.toml"


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


class SecurityConfig(BaseModel):
    """安全配置"""

    secret_key: str = Field(
        default_factory=lambda: secrets.token_hex(32),
        title="密钥",
        description="应用安全密钥，用于 JWT 签名",
        json_schema_extra=ExtraField(is_secret=True, is_hidden=True).model_dump(),
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


class ModelGroup(BaseModel):
    """模型组配置 - 包含对话、视觉、嵌入三种模型"""

    name: str = Field(..., title="组名称")

    # 对话模型 (必填)
    chat_model: ModelConfig = Field(
        ..., title="对话模型", description="用于 Agent 推理"
    )

    # 视觉模型 (可选)
    vision_model: Optional[ModelConfig] = Field(
        None, title="视觉模型", description="用于图像识别"
    )

    # 嵌入模型 (可选)
    embedding_model: Optional[ModelConfig] = Field(
        None, title="嵌入模型", description="用于向量化"
    )


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

    # 模型组管理 - 每个组包含对话/视觉/嵌入三种模型
    model_groups: Dict[str, ModelGroup] = Field(
        default_factory=dict,
        title="模型组列表",
        description="自定义模型组配置，每个组包含对话、视觉、嵌入三种模型",
    )

    # 当前使用的模型组
    current_model_group: str = Field(
        default="",
        title="当前模型组",
        description="选择要使用的模型组",
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

    level: str = Field(default="INFO", title="日志级别", description="全局日志级别")
    colorize: bool = Field(
        default=True, title="彩色输出", description="是否启用彩色日志"
    )
    show_time: bool = Field(
        default=True, title="显示时间", description="是否显示时间戳"
    )
    file: Optional[str] = Field(
        default=None, title="日志文件", description="日志输出文件路径"
    )

    # 前后端分离配置
    exclude_frontend: bool = Field(
        default=False,
        title="过滤前端日志",
        description="是否过滤 WebSocket/Uvicorn 等前端相关日志",
    )
    frontend_level: str = Field(
        default="WARNING",
        title="前端日志级别",
        description="前端模块 (ws, uvicorn) 的日志级别",
    )
    agent_level: str = Field(
        default="DEBUG",
        title="Agent 日志级别",
        description="AI Agent 思考过程的日志级别",
    )


class AppConfig(BaseModel):
    """应用主配置

    基于 Pydantic 的配置模型，支持类型验证和默认值。
    """

    # 配置文件版本，用于自动迁移
    version: str = "0.1.1"

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
        """加载配置文件，自动迁移旧版本配置"""
        # 获取代码中定义的默认版本
        default_config = AppConfig()
        code_version = default_config.version

        if not self._config_file.exists():
            # 创建默认配置
            self._config = default_config
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

            file_version = raw.get("version", "0.0.0")

            # 版本检查和自动迁移
            if self._version_compare(file_version, code_version) < 0:
                logger.info(
                    "检测到旧版本配置 (v%s -> v%s)，正在迁移...",
                    file_version,
                    code_version,
                )
                raw = self._migrate_config(raw, default_config)
                raw["version"] = code_version

                # 立即保存迁移后的配置
                self._config = AppConfig(**raw)
                self._save()
                logger.info("配置已迁移到 v%s", code_version)
            else:
                # 版本相同，但仍需检查并迁移旧格式的 model_groups
                raw, was_migrated = self._migrate_model_groups_if_needed(raw)

                # 如果发生了迁移，先保存再验证
                if was_migrated:
                    # 先写入文件（如果解析失败，至少文件已更新）
                    try:
                        with self._config_file.open("wb") as f:
                            tomli_w.dump(raw, f)
                        logger.info("配置文件已更新（模型组格式迁移）")
                    except Exception as save_err:
                        logger.error("保存迁移后配置失败: %s", save_err)

                self._config = AppConfig(**raw)
                # 检查是否有缺失字段被默认值填充，如有则补全保存
                loaded_dict = self._config.model_dump()
                if loaded_dict != raw:
                    self._save()
                    logger.info("配置已补全缺失字段")

            self._last_mtime = self._config_file.stat().st_mtime
            logger.info("配置已加载 (v%s)", self._config.version)

        except Exception as e:  # pylint: disable=broad-except
            logger.error("加载配置失败: %s", e)
            self._config = AppConfig()

    def _version_compare(self, v1: str, v2: str) -> int:
        """比较版本号: 返回 -1 (v1 < v2), 0 (v1 == v2), 1 (v1 > v2)"""
        try:
            parts1 = [int(x) for x in v1.split(".")]
            parts2 = [int(x) for x in v2.split(".")]
            for p1, p2 in zip(parts1, parts2):
                if p1 < p2:
                    return -1
                if p1 > p2:
                    return 1
            return 0
        except (ValueError, AttributeError):
            return -1

    def _migrate_model_groups_if_needed(self, raw: Dict) -> tuple[Dict, bool]:
        """迁移旧格式的 model_groups (ModelConfig -> ModelGroup)

        Returns:
            (raw, migrated): 迁移后的配置字典和是否发生了迁移
        """
        if "ai" not in raw or "model_groups" not in raw["ai"]:
            return raw, False

        migrated = False
        old_groups = raw["ai"]["model_groups"]
        new_groups = {}

        for name, group_data in old_groups.items():
            # 检查是否是旧格式 (直接包含 provider/model 等字段)
            if (
                isinstance(group_data, dict)
                and "provider" in group_data
                and "chat_model" not in group_data
            ):
                # 旧格式: 转换为新的 ModelGroup 格式
                new_groups[name] = {
                    "name": name,
                    "chat_model": group_data,
                    "vision_model": None,
                    "embedding_model": None,
                }
                migrated = True
                logger.info("迁移模型组 '%s' 到新格式", name)
            else:
                # 已经是新格式，保持不变
                new_groups[name] = group_data

        if migrated:
            raw["ai"]["model_groups"] = new_groups
            # 同时删除废弃字段
            for deprecated_field in ["current_vision_model", "current_embedding_model"]:
                if deprecated_field in raw["ai"]:
                    del raw["ai"][deprecated_field]

        return raw, migrated

    def _migrate_config(self, old: Dict, default: AppConfig) -> Dict:
        """迁移旧配置，保留用户数据并添加新字段"""
        default_dict = default.model_dump()

        def deep_merge(base: Dict, override: Dict) -> Dict:
            """深度合并字典，override 中的值优先"""
            result = base.copy()
            for key, value in override.items():
                if (
                    key in result
                    and isinstance(result[key], dict)
                    and isinstance(value, dict)
                ):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result

        # 用默认配置作为基础，用户配置覆盖
        migrated = deep_merge(default_dict, old)

        # 删除已废弃的字段
        if "security" in migrated and "admin_key" in migrated["security"]:
            del migrated["security"]["admin_key"]
        if "logging" in migrated and "format" in migrated["logging"]:
            del migrated["logging"]["format"]

        # 删除新废弃的字段 (current_vision_model, current_embedding_model)
        if "ai" in migrated:
            for deprecated_field in ["current_vision_model", "current_embedding_model"]:
                if deprecated_field in migrated["ai"]:
                    del migrated["ai"][deprecated_field]

        if "ai" in migrated and "model_groups" in migrated["ai"]:
            old_groups = migrated["ai"]["model_groups"]
            new_groups = {}

            for name, group_data in old_groups.items():
                if (
                    isinstance(group_data, dict)
                    and "provider" in group_data
                    and "chat_model" not in group_data
                ):
                    new_groups[name] = {
                        "name": name,
                        "chat_model": group_data,
                        "vision_model": None,
                        "embedding_model": None,
                    }
                    logger.info("迁移模型组 '%s' 到新格式", name)
                else:
                    new_groups[name] = group_data

            migrated["ai"]["model_groups"] = new_groups

        return migrated

    def _save(self) -> None:
        """保存配置到文件"""
        if self._config is None:
            return

        try:
            # exclude_none=True 过滤 None 值，TOML 不支持 None
            data = self._config.model_dump(exclude_none=True)
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

    @property
    def version(self) -> str:
        return self.config.version

    @property
    def secret_key(self) -> str:
        return self.config.security.secret_key

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
