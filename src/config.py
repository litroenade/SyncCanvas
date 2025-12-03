"""模块名称: config
主要功能: 配置管理，支持 TOML 文件和热重载
"""

import os
import secrets
import time
from pathlib import Path
from typing import Any, Dict

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback

from src.logger import get_logger

logger = get_logger(__name__)

# 配置文件路径
CONFIG_FILE = Path(__file__).resolve().parents[1] / "config.toml"


class Config:
    """配置管理类，支持热重载"""

    def __init__(self, config_file: Path = CONFIG_FILE):
        self._config_file = config_file
        self._config: Dict[str, Any] = {}
        self._last_mtime = 0.0
        self._load_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        if not self._config_file.exists():
            self._create_default_config()

        try:
            mtime = self._config_file.stat().st_mtime
            if mtime > self._last_mtime:
                with self._config_file.open("rb") as f:
                    self._config = tomllib.load(f)
                self._last_mtime = mtime
                logger.info(f"配置已加载: {self._config_file}")
        except Exception as e:
            logger.error(f"加载配置失败: {e}")

    def _create_default_config(self) -> None:
        """创建默认配置文件"""
        secret_key = secrets.token_hex(32)
        content = f"""# SyncCanvas 配置文件

[security]
# 服务端密钥，用于认证
secret_key = "{secret_key}"

[server]
# 服务端口
port = 8000
# 绑定主机
host = "0.0.0.0"
"""
        try:
            with self._config_file.open("w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"已创建默认配置文件: {self._config_file}")
        except Exception as e:
            logger.error(f"创建默认配置失败: {e}")

    def _check_reload(self) -> None:
        """检查文件是否修改并重载"""
        try:
            if self._config_file.exists():
                mtime = self._config_file.stat().st_mtime
                if mtime > self._last_mtime:
                    logger.info("检测到配置变更，正在重载...")
                    self._load_config()
        except Exception as e:
            logger.error(f"检查配置变更失败: {e}")

    @property
    def secret_key(self) -> str:
        """获取 secret_key，支持热重载"""
        self._check_reload()
        return self._config.get("security", {}).get("secret_key", "")

    @property
    def database_url(self) -> str:
        """获取数据库连接 URL"""
        self._check_reload()
        return self._config.get("database", {}).get(
            "url", "sqlite:///./data/sync_canvas.db"
        )

    @property
    def db_echo(self) -> bool:
        """获取数据库 Echo 设置"""
        self._check_reload()
        return self._config.get("database", {}).get("echo", False)

    @property
    def host(self) -> str:
        """获取服务绑定主机"""
        self._check_reload()
        return self._config.get("server", {}).get("host", "0.0.0.0")

    @property
    def port(self) -> int:
        """获取服务端口"""
        self._check_reload()
        return self._config.get("server", {}).get("port", 8000)

    @property
    def allowed_origins(self) -> list[str]:
        """获取允许的跨域来源"""
        self._check_reload()
        return self._config.get("server", {}).get("allowed_origins", ["*"])

    @property
    def openai_api_key(self) -> str:
        """获取 OpenAI API Key"""
        self._check_reload()
        return self._config.get("ai", {}).get("openai_api_key", "")

    @property
    def openai_base_url(self) -> str:
        """获取 OpenAI Base URL"""
        self._check_reload()
        return self._config.get("ai", {}).get(
            "openai_base_url", "https://api.openai.com/v1"
        )

    @property
    def openai_model(self) -> str:
        """获取 OpenAI 模型名称"""
        self._check_reload()
        return self._config.get("ai", {}).get("openai_model", "gpt-3.5-turbo")


# 全局配置实例
config = Config()

# 导出常用配置项，保持兼容性
DATABASE_URL = config.database_url
DB_ECHO = config.db_echo
HOST = config.host
PORT = config.port
ALLOWED_ORIGINS = config.allowed_origins
OPENAI_API_KEY = config.openai_api_key
OPENAI_BASE_URL = config.openai_base_url
OPENAI_MODEL = config.openai_model
