from __future__ import annotations
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import tomllib
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

RICH_AVAILABLE = True


# ==================== 日志分类 ====================

# 前端相关模块 (WebSocket, 实时同步等) - 可被单独过滤
FRONTEND_MODULES = frozenset(
    {
        "src.ws",
        "src.ws.sync",
        "src.ws.message_router",
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "websockets",
        "pycrdt",
    }
)

# Agent 相关模块 - 详细思考日志
AGENT_MODULES = frozenset(
    {
        "src.agent",
        "src.agent.base",
        "src.agent.llm",
        "src.agent.pipeline",
        "src.agent.canvas",
        "src.agent.tools",
    }
)


# ==================== 过滤器 ====================


class FrontendFilter(logging.Filter):
    """过滤前端相关日志

    当 exclude_frontend=True 时，过滤掉所有前端模块的日志
    """

    def __init__(self, exclude_frontend: bool = False):
        super().__init__()
        self.exclude_frontend = exclude_frontend

    def filter(self, record: logging.LogRecord) -> bool:
        if not self.exclude_frontend:
            return True

        # 检查是否是前端模块
        for prefix in FRONTEND_MODULES:
            if record.name.startswith(prefix):
                return False
        return True


class ModuleLevelFilter(logging.Filter):
    """按模块设置不同日志级别"""

    def __init__(self, module_levels: Dict[str, int] = None):
        super().__init__()
        self.module_levels = module_levels or {}

    def filter(self, record: logging.LogRecord) -> bool:
        for prefix, level in self.module_levels.items():
            if record.name.startswith(prefix):
                return record.levelno >= level
        return True


# ==================== Rich 主题 ====================

CUSTOM_THEME = Theme(
    {
        "logging.level.debug": "dim cyan",
        "logging.level.info": "bold green",
        "logging.level.warning": "bold yellow",
        "logging.level.error": "bold red",
        "logging.level.critical": "bold white on red",
        "repr.number": "cyan",
        "repr.string": "green",
        "agent": "bold magenta",
        "frontend": "dim blue",
        "backend": "bold cyan",
    }
)


# ==================== 自定义格式化器 ====================


class SimpleColorFormatter(logging.Formatter):
    """简单的颜色格式化器 (不使用 rich 时的备选)"""

    COLORS = {
        "DEBUG": "\033[2;37m",  # dim white
        "INFO": "\033[1;32m",  # bold green
        "WARNING": "\033[1;33m",  # bold yellow
        "ERROR": "\033[1;31m",  # bold red
        "CRITICAL": "\033[1;41;37m",  # white on red
    }
    RESET = "\033[0m"

    MODULE_COLORS = {
        "agent": "\033[1;35m",  # bold magenta
        "ws": "\033[2;34m",  # dim blue
        "routers": "\033[1;36m",  # bold cyan
        "services": "\033[36m",  # cyan
        "db": "\033[33m",  # yellow
    }

    def format(self, record: logging.LogRecord) -> str:
        # 简化模块名
        name = record.name
        if name.startswith("src."):
            name = name[4:]
        if len(name) > 22:
            parts = name.split(".")
            if len(parts) > 2:
                name = f"{parts[0]}...{parts[-1]}"
            else:
                name = name[:19] + "..."

        # 获取颜色
        level_color = self.COLORS.get(record.levelname, "")
        module_color = ""
        for prefix, color in self.MODULE_COLORS.items():
            if name.startswith(prefix):
                module_color = color
                break

        # 格式化
        if sys.stdout.isatty():
            level_str = f"{level_color}[{record.levelname[0]}]{self.RESET}"
            name_str = f"{module_color}{name:<22}{self.RESET}"
        else:
            level_str = f"[{record.levelname[0]}]"
            name_str = f"{name:<22}"

        # 时间戳
        time_str = self.formatTime(record, "%H:%M:%S")

        return f"{time_str} {level_str} {name_str} {record.getMessage()}"


# ==================== 配置状态 ====================


class _LoggerState:
    """日志配置状态"""

    configured: bool = False
    console: Optional[Console] = None


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
        "exclude_frontend": False,  # 是否过滤前端日志
        "frontend_level": "WARNING",  # 前端日志级别
        "agent_level": "DEBUG",  # Agent 日志级别
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

    level_str = settings.get("level", "INFO")
    level = getattr(logging, level_str.upper(), logging.INFO)
    colorize = settings.get("colorize", True)
    log_file = settings.get("file")
    max_bytes = int(settings.get("max_bytes", 10_485_760))
    backup_count = int(settings.get("backup_count", 5))
    exclude_frontend = settings.get("exclude_frontend", False)
    frontend_level_str = settings.get("frontend_level", "WARNING")
    agent_level_str = settings.get("agent_level", "DEBUG")

    frontend_level = getattr(logging, frontend_level_str.upper(), logging.WARNING)
    agent_level = getattr(logging, agent_level_str.upper(), logging.DEBUG)

    # 创建根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 允许最低级别，由 handler 控制

    # 清除现有 handlers
    root_logger.handlers.clear()

    # 控制台 handler
    if RICH_AVAILABLE and colorize:
        # 使用 Rich
        _state.console = Console(theme=CUSTOM_THEME, force_terminal=True)
        console_handler = RichHandler(
            console=_state.console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            tracebacks_show_locals=False,
            markup=True,
        )
        console_handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        # 使用简单颜色
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(SimpleColorFormatter())

    console_handler.setLevel(level)

    # 添加前端过滤器
    console_handler.addFilter(FrontendFilter(exclude_frontend=exclude_frontend))

    # 添加模块级别过滤器
    module_levels = {}
    for prefix in FRONTEND_MODULES:
        module_levels[prefix] = frontend_level
    for prefix in AGENT_MODULES:
        module_levels[prefix] = agent_level
    console_handler.addFilter(ModuleLevelFilter(module_levels))

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
            file_handler.setLevel(logging.DEBUG)  # 文件记录所有日志
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    "%Y-%m-%d %H:%M:%S",
                )
            )
            root_logger.addHandler(file_handler)
        except OSError as e:
            sys.stderr.write(f"无法创建日志文件 {log_path}: {e}\n")

    # 降低第三方库的日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("anyio").setLevel(logging.WARNING)

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


def get_console() -> Optional[Console]:
    """获取 Rich Console 实例 (用于特殊输出)"""
    if not _state.configured:
        setup_logging()
    return _state.console


# ==================== 便捷函数 ====================


def log_agent_thinking(logger: logging.Logger, thought: str, step: int = 0) -> None:
    """记录 Agent 思考过程

    Args:
        logger: Logger 实例
        thought: 思考内容
        step: 步骤编号
    """
    if step > 0:
        logger.debug("[THINK Step %d] %s", step, thought)
    else:
        logger.debug("[THINK] %s", thought)


def log_agent_action(
    logger: logging.Logger, action: str, args: Dict[str, Any] = None
) -> None:
    """记录 Agent 动作

    Args:
        logger: Logger 实例
        action: 动作名称
        args: 动作参数
    """
    if args:
        # 截断过长的参数
        args_str = str(args)
        if len(args_str) > 200:
            args_str = args_str[:197] + "..."
        logger.debug("[ACTION] %s -> %s", action, args_str)
    else:
        logger.debug("[ACTION] %s", action)


def log_agent_observation(
    logger: logging.Logger, observation: str, success: bool = True
) -> None:
    """记录 Agent 观察结果

    Args:
        logger: Logger 实例
        observation: 观察内容
        success: 是否成功
    """
    status = "✓" if success else "✗"
    # 截断过长的观察
    if len(observation) > 300:
        observation = observation[:297] + "..."
    logger.debug("[OBSERVE %s] %s", status, observation)
