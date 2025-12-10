"""模块名称: logger
主要功能: 日志系统配置，支持颜色输出和模块区分
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib


# ==================== 颜色定义 ====================

class Colors:
    """ANSI 颜色码"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # 前景色
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # 亮色
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"


# 日志级别颜色映射
LEVEL_COLORS = {
    "DEBUG": Colors.DIM + Colors.WHITE,
    "INFO": Colors.BRIGHT_GREEN,
    "WARNING": Colors.BRIGHT_YELLOW,
    "ERROR": Colors.BRIGHT_RED,
    "CRITICAL": Colors.BOLD + Colors.BRIGHT_RED,
}

# 模块颜色映射 (区分不同模块)
MODULE_COLORS = {
    "src.ws": Colors.BRIGHT_CYAN,        # WebSocket 相关
    "src.ai": Colors.BRIGHT_MAGENTA,     # AI 相关
    "src.routers": Colors.BRIGHT_BLUE,   # API 路由
    "src.db": Colors.YELLOW,             # 数据库
    "src.services": Colors.CYAN,         # 服务层
    "uvicorn": Colors.DIM,               # Uvicorn 服务器
    "__main__": Colors.BRIGHT_GREEN,     # 主程序
}


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        colorize: bool = True,
        show_time: bool = True,
    ):
        self.colorize = colorize and sys.stdout.isatty()
        self.show_time = show_time

        # 构建格式字符串
        if fmt is None:
            if show_time:
                fmt = "%(asctime)s %(levelname_colored)s %(name_colored)s %(message)s"
            else:
                fmt = "%(levelname_colored)s %(name_colored)s %(message)s"

        if datefmt is None:
            datefmt = "%H:%M:%S"

        super().__init__(fmt, datefmt)

    def format(self, record: logging.LogRecord) -> str:
        # 获取模块颜色
        module_color = Colors.WHITE
        for prefix, color in MODULE_COLORS.items():
            if record.name.startswith(prefix):
                module_color = color
                break

        # 简化模块名
        name = record.name
        if name.startswith("src."):
            name = name[4:]  # 去掉 src. 前缀

        # 截断过长的模块名
        if len(name) > 20:
            parts = name.split(".")
            if len(parts) > 2:
                name = f"{parts[0]}...{parts[-1]}"
            else:
                name = name[:17] + "..."

        if self.colorize:
            # 级别颜色
            level_color = LEVEL_COLORS.get(record.levelname, "")
            record.levelname_colored = f"{level_color}[{record.levelname[0]}]{Colors.RESET}"

            # 模块颜色
            record.name_colored = f"{module_color}{name:<20}{Colors.RESET}"
        else:
            record.levelname_colored = f"[{record.levelname[0]}]"
            record.name_colored = f"{name:<20}"

        return super().format(record)


class _LoggerState:
    """日志配置状态"""
    configured: bool = False


_state = _LoggerState()


def _load_settings() -> Dict[str, Any]:
    """从配置文件加载日志设置"""
    defaults = {
        "level": "INFO",
        "colorize": True,
        "show_time": True,
        "file": None,
        "max_bytes": 10_485_760,  # 10 MiB
        "backup_count": 5,
    }

    config_path = Path(__file__).resolve().parents[1] / "config" / "config.toml"

    if not config_path.exists():
        return defaults

    try:
        with config_path.open("rb") as f:
            raw = tomllib.load(f)

        logging_section = raw.get("logging", {})
        if isinstance(logging_section, dict):
            defaults.update(logging_section)

        return defaults
    except Exception:
        return defaults


def setup_logging(force: bool = False) -> None:
    """初始化日志系统
    
    Args:
        force: 是否强制重新配置
    """
    if _state.configured and not force:
        return

    settings = _load_settings()

    level = settings.get("level", "INFO")
    colorize = settings.get("colorize", True)
    show_time = settings.get("show_time", True)
    log_file = settings.get("file")
    max_bytes = int(settings.get("max_bytes", 10_485_760))
    backup_count = int(settings.get("backup_count", 5))

    # 创建根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除现有 handlers
    root_logger.handlers.clear()

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter(
        colorize=colorize,
        show_time=show_time,
    ))
    root_logger.addHandler(console_handler)

    # 文件 handler (可选)
    if log_file:
        log_path = Path(log_file)
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "%Y-%m-%d %H:%M:%S",
            ))
            root_logger.addHandler(file_handler)
        except OSError as e:
            sys.stderr.write(f"无法创建日志文件 {log_path}: {e}\n")

    # 降低第三方库的日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    _state.configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取 logger 实例
    
    Args:
        name: logger 名称，通常使用 __name__
        
    Returns:
        logging.Logger 实例
    """
    if not _state.configured:
        setup_logging()
    return logging.getLogger(name)
