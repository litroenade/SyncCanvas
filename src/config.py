"""模块名称: config
主要功能: 应用配置管理，从 config.toml 和环境变量加载配置项
"""

from __future__ import annotations

import json
import os
import secrets
import sys
from typing import List, Any

# Python 3.11+ has tomllib, otherwise use tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        print("Error: tomli is required for Python < 3.11")
        sys.exit(1)


def load_config() -> dict[str, Any]:
    """加载 config.toml 配置文件

    Returns:
        dict[str, Any]: 配置字典，若加载失败返回空字典
    """
    config_path = "config.toml"
    if not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except (tomllib.TOMLDecodeError, OSError) as e:
        print("Error loading config.toml: %s" % e)
        return {}


_CONFIG = load_config()
_SERVER = _CONFIG.get("server", {})
_APP = _CONFIG.get("app", {})
_LOGGING = _CONFIG.get("logging", {})


def _get(section: dict, key: str, env_key: str, default: Any = None) -> Any:
    """优先从 config.toml 读取，其次环境变量，最后默认值"""
    val = section.get(key)
    if val is not None:
        return val
    return os.getenv(env_key, default)


def _parse_csv(value: str | list) -> List[str]:
    """解析逗号分隔的字符串或列表

    Args:
        value: 逗号分隔的字符串或列表

    Returns:
        List[str]: 解析后的字符串列表
    """
    if isinstance(value, list):
        return value
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


# 确保 data 目录存在
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")


def get_or_create_secret_key() -> str:
    """获取或创建密钥

    Returns:
        str: 64 字符的十六进制密钥
    """
    settings: dict = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print("Error loading settings.json: %s" % e)

    if "secret_key" not in settings:
        print("Generating new secret key...")
        settings["secret_key"] = secrets.token_hex(32)  # 64 字符
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
        except OSError as e:
            print("Error saving settings.json: %s" % e)

    return settings["secret_key"]


# Server Config (服务器配置)
HOST = _get(_SERVER, "host", "HOST", "0.0.0.0")
PORT = int(_get(_SERVER, "port", "PORT", 8021))
RELOAD = _get(_SERVER, "reload", "RELOAD", True)

# App Config (应用配置)
ALLOWED_ORIGINS = _parse_csv(_get(_APP, "allowed_origins", "ALLOWED_ORIGINS", "*"))
DATABASE_URL = _get(
    _APP, "database_url", "DATABASE_URL", "sqlite:///./data/sync_canvas.db"
)
WEBSOCKET_API_TOKEN = _get(_APP, "websocket_api_token", "WEBSOCKET_API_TOKEN")
SECRET_KEY = get_or_create_secret_key()

# Logging Config (日志配置)
LOG_LEVEL = _get(_LOGGING, "level", "LOG_LEVEL", "INFO")

# Database Config (数据库配置)
DB_ECHO = _get(_APP, "db_echo", "DB_ECHO", False)

# OpenAI Config (OpenAI 配置)
OPENAI_API_KEY = _get(_APP, "openai_api_key", "OPENAI_API_KEY")
OPENAI_BASE_URL = _get(_APP, "openai_base_url", "OPENAI_BASE_URL")
OPENAI_MODEL = _get(_APP, "openai_model", "OPENAI_MODEL", "gpt-3.5-turbo")
