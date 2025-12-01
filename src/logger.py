"""模块名称: logger
主要功能: 日志系统配置和管理，从 config.toml 加载日志配置
"""

from __future__ import annotations

import logging
import logging.config
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict
import tomllib as _toml

# 默认日志配置
_DEFAULT_LOGGING: Dict[str, Any] = {
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    "datefmt": "%Y-%m-%d %H:%M:%S",
    "file": None,
    "max_bytes": 1_048_576,  # 1 MiB
    "backup_count": 3,
}


class _LoggerState:
    """日志配置状态管理类"""

    configured: bool = False


_state = _LoggerState()


def _load_settings() -> Dict[str, Any]:
    """读取 ``config.toml`` 中的日志配置, 如不存在则返回默认配置。"""
    project_root = Path(__file__).resolve().parents[1]
    config_path = project_root / "config.toml"

    if not config_path.exists():
        return dict(_DEFAULT_LOGGING)

    try:
        with config_path.open("rb") as fp:
            raw = _toml.load(fp)
    except (_toml.TOMLDecodeError, OSError) as exc:
        sys.stderr.write(f"[logger] 无法读取 config.toml: {exc}\n")
        return dict(_DEFAULT_LOGGING)

    settings = dict(_DEFAULT_LOGGING)
    logging_section = raw.get("logging", {})
    if isinstance(logging_section, dict):
        settings.update(logging_section)

    return settings


def setup_logging(force: bool = False) -> None:
    """初始化日志系统。

    Args:
        force: 是否强制重新配置日志。
    """
    if _state.configured and not force:
        return

    settings = _load_settings()
    level = settings.get("level", "INFO")
    log_format = settings.get("format", _DEFAULT_LOGGING["format"])
    date_format = settings.get("datefmt", _DEFAULT_LOGGING["datefmt"])
    log_file = settings.get("file")
    max_bytes = int(settings.get("max_bytes", _DEFAULT_LOGGING["max_bytes"]))
    backup_count = int(settings.get("backup_count", _DEFAULT_LOGGING["backup_count"]))

    handlers: Dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": level,
            "stream": "ext://sys.stdout",
        }
    }
    root_handlers = ["console"]

    if log_file:
        log_path = Path(log_file)
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            sys.stderr.write(f"[logger] 无法创建日志目录 {log_path.parent}: {exc}\n")
        else:
            handlers["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "level": level,
                "filename": str(log_path),
                "maxBytes": max_bytes,
                "backupCount": backup_count,
                "encoding": "utf-8",
            }
            root_handlers.append("file")

    config_dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": log_format,
                "datefmt": date_format,
            }
        },
        "handlers": handlers,
        "root": {
            "level": level,
            "handlers": root_handlers,
        },
    }

    logging.config.dictConfig(config_dict)
    _state.configured = True


def get_logger(name: str | None = None) -> logging.Logger:
    """获取带名称的 logger, 确保日志系统已配置。"""
    if not _state.configured:
        setup_logging()
    return logging.getLogger(name)
