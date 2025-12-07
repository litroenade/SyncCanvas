"""模块名称: config
主要功能: 配置管理，提供版本化、热重载与默认文件生成
"""

from __future__ import annotations

import secrets
import shutil
from pathlib import Path
from typing import Any, Dict, Tuple

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover - 兼容低版本
    import tomli as tomllib  # type: ignore

import tomli_w

from src.logger import get_logger

logger = get_logger(__name__)

CONFIG_VERSION_LATEST = 1
CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
CONFIG_FILE = CONFIG_DIR / "config.toml"
LEGACY_CONFIG_FILE = Path(__file__).resolve().parents[1] / "config.toml"


def _build_default_config(secret_key: str | None = None) -> Dict[str, Any]:
    """构建默认配置字典，便于落盘或用于缺省值。"""

    secret_value = secret_key or secrets.token_hex(32)
    return {
        "version": CONFIG_VERSION_LATEST,
        "security": {
            "secret_key": secret_value,
            "admin_key": "admin",
        },
        "server": {
            "host": "0.0.0.0",
            "port": 8000,
            "allowed_origins": ["*"],
        },
        "database": {
            "url": "sqlite:///./data/sync_canvas.db",
            "echo": False,
        },
        "ai": {
            "provider": "siliconflow",
            "model": "Qwen/Qwen2.5-14B-Instruct",
            "base_url": "https://api.siliconflow.cn/v1",
            "api_key": "",
            "fallback_provider": "openai",
            "fallback_model": "gpt-4o-mini",
            "fallback_base_url": "https://api.openai.com/v1",
            "fallback_api_key": "",
            "tool_choice": "auto",
            "max_tool_calls": 6,
        },
    }


class Config:
    """配置管理类，支持版本迁移与热重载。"""

    def __init__(self, config_file: Path = CONFIG_FILE):
        self._config_dir = CONFIG_DIR
        self._config_file = config_file
        self._legacy_config_file = LEGACY_CONFIG_FILE
        self._config: Dict[str, Any] = {}
        self._last_mtime = 0.0
        self._ensure_config_dir()
        self._bootstrap_config_file()
        self._load_config()

    def _ensure_config_dir(self) -> None:
        """确保配置目录存在。"""

        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # pragma: no cover - 目录创建极少失败
            logger.error("创建配置目录失败: %s", exc)

    def _bootstrap_config_file(self) -> None:
        """初始化配置文件: 优先迁移旧文件，否则写入默认模板。"""

        if self._config_file.exists():
            return

        if self._legacy_config_file.exists():
            try:
                shutil.copy(self._legacy_config_file, self._config_file)
                logger.info(
                    "已迁移旧版配置文件", extra={"from": str(self._legacy_config_file)}
                )
                return
            except Exception as exc:  # pragma: no cover - 迁移失败属异常场景
                logger.warning("迁移旧配置失败，将使用默认配置: %s", exc)

        self._write_config(_build_default_config())
        logger.info("已创建默认配置文件: %s", self._config_file)

    def _write_config(self, data: Dict[str, Any]) -> None:
        """将配置安全写入磁盘。"""

        try:
            with self._config_file.open("wb") as handle:
                tomli_w.dump(data, handle)
        except Exception as exc:  # pragma: no cover - IO 异常
            logger.error("写入配置失败: %s", exc)

    def _merge_defaults(
        self, current: Dict[str, Any], defaults: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], bool]:
        """用默认值填充缺失键，返回合并结果与是否发生变化。"""

        merged: Dict[str, Any] = {}
        changed = False

        for key, default_value in defaults.items():
            if key in current:
                if isinstance(default_value, dict) and isinstance(current[key], dict):
                    nested, nested_changed = self._merge_defaults(
                        current[key], default_value
                    )
                    merged[key] = nested
                    changed = changed or nested_changed
                else:
                    merged[key] = current[key]
            else:
                merged[key] = default_value
                changed = True

        for key, value in current.items():
            if key not in merged:
                merged[key] = value

        return merged, changed

    def _upgrade_config_if_needed(self) -> None:
        """当版本落后或缺失字段时自动升级配置文件。"""

        defaults = _build_default_config()
        merged, changed = self._merge_defaults(self._config, defaults)
        current_version = int(self._config.get("version", 0))

        if current_version < CONFIG_VERSION_LATEST:
            merged["version"] = CONFIG_VERSION_LATEST
            changed = True

        if changed:
            self._config = merged
            self._write_config(self._config)
            self._last_mtime = self._config_file.stat().st_mtime
            logger.info("配置已自动升级到最新版本", extra={"version": CONFIG_VERSION_LATEST})

    def _load_config(self) -> None:
        """加载配置文件并在必要时触发升级。"""

        if not self._config_file.exists():
            self._bootstrap_config_file()

        try:
            mtime = self._config_file.stat().st_mtime
            if mtime <= self._last_mtime:
                return

            with self._config_file.open("rb") as handle:
                raw_config = tomllib.load(handle)

            self._config = raw_config
            self._last_mtime = mtime
            self._upgrade_config_if_needed()
            logger.info("配置已加载", extra={"path": str(self._config_file)})
        except Exception as exc:  # pragma: no cover - 防止配置损坏致崩溃
            logger.error("加载配置失败: %s", exc)

    def _check_reload(self) -> None:
        """检测磁盘变更并热重载。"""

        try:
            if not self._config_file.exists():
                return
            mtime = self._config_file.stat().st_mtime
            if mtime > self._last_mtime:
                logger.info("检测到配置变更，正在热重载")
                self._load_config()
        except Exception as exc:  # pragma: no cover - 文件系统异常
            logger.error("检查配置变更失败: %s", exc)

    def _get(self, section: str, key: str, fallback: Any) -> Any:
        """安全读取配置项，缺失时返回默认值。"""

        self._check_reload()
        section_data = self._config.get(section, {})
        return section_data.get(key, fallback)

    @property
    def version(self) -> int:
        """获取配置文件版本号。"""

        self._check_reload()
        return int(self._config.get("version", CONFIG_VERSION_LATEST))

    @property
    def secret_key(self) -> str:
        """获取 secret_key，支持热重载。"""

        return str(self._get("security", "secret_key", ""))

    @property
    def admin_key(self) -> str:
        """获取 admin_key，支持热重载。"""

        return str(self._get("security", "admin_key", ""))

    @property
    def database_url(self) -> str:
        """获取数据库连接 URL。"""

        return str(
            self._get("database", "url", "sqlite:///./data/sync_canvas.db")
        )

    @property
    def db_echo(self) -> bool:
        """获取数据库 Echo 设置。"""

        return bool(self._get("database", "echo", False))

    @property
    def host(self) -> str:
        """获取服务绑定主机。"""

        return str(self._get("server", "host", "0.0.0.0"))

    @property
    def port(self) -> int:
        """获取服务端口。"""

        return int(self._get("server", "port", 8000))

    @property
    def allowed_origins(self) -> list[str]:
        """获取允许的跨域来源。"""

        origins = self._get("server", "allowed_origins", ["*"])
        if isinstance(origins, list):
            return [str(item) for item in origins]
        return ["*"]

    @property
    def llm_provider(self) -> str:
        """获取首选 LLM 服务商。"""

        return str(self._get("ai", "provider", "siliconflow"))

    @property
    def llm_model(self) -> str:
        """获取首选 LLM 模型名称。"""

        return str(self._get("ai", "model", "Qwen/Qwen2.5-14B-Instruct"))

    @property
    def llm_base_url(self) -> str:
        """获取首选 LLM Base URL。"""

        return str(self._get("ai", "base_url", "https://api.siliconflow.cn/v1"))

    @property
    def llm_api_key(self) -> str:
        """统一获取首选 LLM 的 API Key。"""

        primary_key = str(self._get("ai", "api_key", ""))
        if primary_key:
            return primary_key

        fallback_key = str(self._get("ai", "fallback_api_key", ""))
        return fallback_key

    @property
    def llm_fallback_provider(self) -> str:
        """获取兜底 LLM 服务商。"""

        return str(self._get("ai", "fallback_provider", "openai"))

    @property
    def llm_fallback_model(self) -> str:
        """获取兜底 LLM 模型名称。"""

        return str(self._get("ai", "fallback_model", "gpt-4o-mini"))

    @property
    def llm_fallback_base_url(self) -> str:
        """获取兜底 LLM Base URL。"""

        return str(self._get("ai", "fallback_base_url", "https://api.openai.com/v1"))

    @property
    def llm_fallback_api_key(self) -> str:
        """获取兜底 LLM 的 API Key。"""

        return str(self._get("ai", "fallback_api_key", ""))

    @property
    def llm_tool_choice(self) -> str:
        """获取工具调用策略 (auto/none/required)。"""

        choice = str(self._get("ai", "tool_choice", "auto"))
        if choice not in {"auto", "none", "required"}:
            return "auto"
        return choice

    @property
    def llm_max_tool_calls(self) -> int:
        """获取单次会话允许的工具调用上限。"""

        return int(self._get("ai", "max_tool_calls", 6))

    @property
    def openai_api_key(self) -> str:
        """获取 OpenAI API Key（兼容旧用法）。"""

        return str(self._get("ai", "fallback_api_key", ""))

    @property
    def openai_base_url(self) -> str:
        """获取 OpenAI Base URL（兼容旧用法）。"""

        return str(self._get("ai", "fallback_base_url", "https://api.openai.com/v1"))

    @property
    def openai_model(self) -> str:
        """获取 OpenAI 模型名称（兼容旧用法）。"""

        return str(self._get("ai", "fallback_model", "gpt-4o-mini"))

    @property
    def siliconflow_api_key(self) -> str:
        """获取 SiliconFlow API Key（兼容旧用法）。"""

        return str(self._get("ai", "api_key", ""))

    @property
    def siliconflow_base_url(self) -> str:
        """获取 SiliconFlow Base URL（兼容旧用法）。"""

        return str(self._get("ai", "base_url", "https://api.siliconflow.cn/v1"))

    @property
    def siliconflow_model(self) -> str:
        """获取 SiliconFlow 模型名称（兼容旧用法）。"""

        return str(self._get("ai", "model", "Qwen/Qwen2.5-14B-Instruct"))


# 全局配置实例
config = Config()

# 导出常用配置项，保持兼容性
CONFIG_VERSION = config.version
DATABASE_URL = config.database_url
DB_ECHO = config.db_echo
HOST = config.host
PORT = config.port
ALLOWED_ORIGINS = config.allowed_origins
OPENAI_API_KEY = config.openai_api_key
OPENAI_BASE_URL = config.openai_base_url
OPENAI_MODEL = config.openai_model
SILICONFLOW_API_KEY = config.siliconflow_api_key
SILICONFLOW_BASE_URL = config.siliconflow_base_url
SILICONFLOW_MODEL = config.siliconflow_model
LLM_PROVIDER = config.llm_provider
LLM_API_KEY = config.llm_api_key
LLM_BASE_URL = config.llm_base_url
LLM_MODEL = config.llm_model
LLM_TOOL_CHOICE = config.llm_tool_choice
LLM_MAX_TOOL_CALLS = config.llm_max_tool_calls
