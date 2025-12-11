"""模块名称: errors
主要功能: Agent 模块统一异常定义

定义 Agent 系统中所有自定义异常类型,包括:
- LLM 调用异常
- 工具执行异常
- 房间操作异常
- Agent 执行异常
- 参数验证异常

所有异常都继承自 AIEngineError 基类,支持错误码和详情信息。
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from src.logger import get_logger

logger = get_logger(__name__)


# ==================== 错误码枚举 ====================


class ErrorCode(Enum):
    """错误代码枚举

    错误码分类:
    - 1xxx: 通用错误
    - 2xxx: LLM 相关错误
    - 3xxx: 工具执行错误
    - 4xxx: 房间操作错误
    - 5xxx: Agent 执行错误

    Attributes:
        UNKNOWN: 未知错误
        VALIDATION_ERROR: 参数验证失败
        TIMEOUT: 操作超时
        CANCELLED: 操作被取消
    """

    # 通用错误 (1xxx)
    UNKNOWN = 1000
    VALIDATION_ERROR = 1001
    TIMEOUT = 1002
    CANCELLED = 1003
    CONFIGURATION_ERROR = 1004

    # LLM 错误 (2xxx)
    LLM_CONNECTION = 2001
    LLM_TIMEOUT = 2002
    LLM_RATE_LIMIT = 2003
    LLM_INVALID_RESPONSE = 2004
    LLM_CONTENT_FILTER = 2005
    LLM_API_ERROR = 2006
    LLM_MODEL_NOT_FOUND = 2007

    # 工具错误 (3xxx)
    TOOL_NOT_FOUND = 3001
    TOOL_INVALID_ARGS = 3002
    TOOL_EXECUTION_ERROR = 3003
    TOOL_TIMEOUT = 3004
    TOOL_PERMISSION_DENIED = 3005
    TOOL_DISABLED = 3006

    # 房间错误 (4xxx)
    ROOM_NOT_FOUND = 4001
    ROOM_BUSY = 4002
    ROOM_LOCK_TIMEOUT = 4003
    ROOM_PERMISSION_DENIED = 4004
    ROOM_INVALID_STATE = 4005

    # Agent 错误 (5xxx)
    AGENT_MAX_ITERATIONS = 5001
    AGENT_INVALID_STATE = 5002
    AGENT_CONTEXT_MISSING = 5003
    AGENT_TOOL_REGISTRATION_ERROR = 5004


# ==================== HTTP 状态码映射 ====================

ERROR_HTTP_STATUS: Dict[ErrorCode, int] = {
    # 400 Bad Request
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.TOOL_INVALID_ARGS: 400,
    ErrorCode.LLM_INVALID_RESPONSE: 400,
    # 403 Forbidden
    ErrorCode.TOOL_PERMISSION_DENIED: 403,
    ErrorCode.ROOM_PERMISSION_DENIED: 403,
    ErrorCode.TOOL_DISABLED: 403,
    # 404 Not Found
    ErrorCode.ROOM_NOT_FOUND: 404,
    ErrorCode.TOOL_NOT_FOUND: 404,
    ErrorCode.LLM_MODEL_NOT_FOUND: 404,
    # 408 Request Timeout
    ErrorCode.TIMEOUT: 408,
    ErrorCode.LLM_TIMEOUT: 408,
    ErrorCode.TOOL_TIMEOUT: 408,
    ErrorCode.ROOM_LOCK_TIMEOUT: 408,
    # 409 Conflict
    ErrorCode.ROOM_BUSY: 409,
    ErrorCode.ROOM_INVALID_STATE: 409,
    ErrorCode.AGENT_INVALID_STATE: 409,
    # 429 Too Many Requests
    ErrorCode.LLM_RATE_LIMIT: 429,
    # 500 Internal Server Error
    ErrorCode.UNKNOWN: 500,
    ErrorCode.TOOL_EXECUTION_ERROR: 500,
    ErrorCode.LLM_CONNECTION: 500,
    ErrorCode.LLM_API_ERROR: 500,
    ErrorCode.AGENT_MAX_ITERATIONS: 500,
    ErrorCode.CONFIGURATION_ERROR: 500,
    # 503 Service Unavailable
    ErrorCode.LLM_CONTENT_FILTER: 503,
}


def get_http_status(code: ErrorCode) -> int:
    """获取错误码对应的 HTTP 状态码

    Args:
        code: 错误码枚举值

    Returns:
        int: HTTP 状态码,默认 500
    """
    return ERROR_HTTP_STATUS.get(code, 500)


# ==================== 基础异常类 ====================


class AIEngineError(Exception):
    """AI Engine 基础异常类

    所有 Agent 相关异常的基类,支持错误码、详情信息和原始异常。

    Attributes:
        message (str): 错误消息
        code (ErrorCode): 错误码
        details (Dict[str, Any]): 详细信息
        cause (Exception): 原始异常
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """初始化异常

        Args:
            message: 错误消息
            code: 错误码
            details: 详细信息字典
            cause: 导致此异常的原始异常
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.cause = cause

    @property
    def http_status(self) -> int:
        """获取对应的 HTTP 状态码"""
        return get_http_status(self.code)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式,用于 API 响应

        Returns:
            Dict: 包含错误信息的字典
        """
        result = {
            "error": self.message,
            "code": self.code.value,
            "code_name": self.code.name,
        }
        if self.details:
            result["details"] = self.details
        return result

    def __str__(self) -> str:
        return f"[{self.code.name}] {self.message}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, code={self.code.name})"


# ==================== 具体异常类 ====================


class LLMError(AIEngineError):
    """LLM 调用相关异常

    用于 LLM API 调用失败、超时、限流等情况。

    Attributes:
        provider (str): LLM 提供商名称
        model (str): 模型名称
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.LLM_CONNECTION,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ):
        """初始化 LLM 异常

        Args:
            message: 错误消息
            code: 错误码
            provider: LLM 提供商
            model: 模型名称
            **kwargs: 传递给父类的其他参数
        """
        details = kwargs.pop("details", {})
        if provider:
            details["provider"] = provider
        if model:
            details["model"] = model
        super().__init__(message, code, details=details, **kwargs)
        self.provider = provider
        self.model = model


class ToolError(AIEngineError):
    """工具执行异常

    用于工具调用失败、参数错误、权限不足等情况。

    Attributes:
        tool_name (str): 工具名称
        args (Dict): 调用参数
    """

    def __init__(
        self,
        message: str,
        tool_name: str,
        code: ErrorCode = ErrorCode.TOOL_EXECUTION_ERROR,
        args: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """初始化工具异常

        Args:
            message: 错误消息
            tool_name: 工具名称
            code: 错误码
            args: 调用参数
            **kwargs: 传递给父类的其他参数
        """
        details = kwargs.pop("details", {})
        details["tool_name"] = tool_name
        if args:
            # 截断过长的参数值
            details["args"] = {k: str(v)[:100] for k, v in args.items()}
        super().__init__(message, code, details=details, **kwargs)
        self.tool_name = tool_name
        self.args = args


class RoomError(AIEngineError):
    """房间操作异常

    用于房间不存在、锁定超时、权限不足等情况。

    Attributes:
        room_id (str): 房间 ID
    """

    def __init__(
        self,
        message: str,
        room_id: str,
        code: ErrorCode = ErrorCode.ROOM_NOT_FOUND,
        **kwargs,
    ):
        """初始化房间异常

        Args:
            message: 错误消息
            room_id: 房间 ID
            code: 错误码
            **kwargs: 传递给父类的其他参数
        """
        details = kwargs.pop("details", {})
        details["room_id"] = room_id
        super().__init__(message, code, details=details, **kwargs)
        self.room_id = room_id


class AgentError(AIEngineError):
    """Agent 执行异常

    用于 Agent 状态错误、迭代次数超限等情况。

    Attributes:
        agent_name (str): Agent 名称
        run_id (int): 运行记录 ID
    """

    def __init__(
        self,
        message: str,
        agent_name: str,
        code: ErrorCode = ErrorCode.UNKNOWN,
        run_id: Optional[int] = None,
        **kwargs,
    ):
        """初始化 Agent 异常

        Args:
            message: 错误消息
            agent_name: Agent 名称
            code: 错误码
            run_id: 运行记录 ID
            **kwargs: 传递给父类的其他参数
        """
        details = kwargs.pop("details", {})
        details["agent_name"] = agent_name
        if run_id is not None:
            details["run_id"] = run_id
        super().__init__(message, code, details=details, **kwargs)
        self.agent_name = agent_name
        self.run_id = run_id


class ValidationError(AIEngineError):
    """参数验证异常

    用于请求参数验证失败的情况。

    Attributes:
        field (str): 验证失败的字段名
        value: 导致验证失败的值
    """

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        value: Any = None,
        **kwargs,
    ):
        """初始化验证异常

        Args:
            message: 错误消息
            field_name: 字段名
            value: 字段值
            **kwargs: 传递给父类的其他参数
        """
        details = kwargs.pop("details", {})
        if field_name:
            details["field"] = field_name
        if value is not None:
            details["value"] = str(value)[:100]
        super().__init__(message, ErrorCode.VALIDATION_ERROR, details=details, **kwargs)
        self.field = field_name
        self.value = value


# ==================== 重试配置 ====================


@dataclass
class RetryConfig:
    """重试策略配置

    用于配置可重试操作的重试行为。

    Attributes:
        max_retries (int): 最大重试次数
        base_delay (float): 基础延迟(秒)
        max_delay (float): 最大延迟(秒)
        exponential_base (float): 指数退避基数
        retryable_codes (List[ErrorCode]): 可重试的错误码列表
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    retryable_codes: List[ErrorCode] = field(
        default_factory=lambda: [
            ErrorCode.LLM_TIMEOUT,
            ErrorCode.LLM_RATE_LIMIT,
            ErrorCode.LLM_CONNECTION,
            ErrorCode.TOOL_TIMEOUT,
            ErrorCode.ROOM_LOCK_TIMEOUT,
        ]
    )

    def get_delay(self, attempt: int) -> float:
        """计算第 N 次重试的延迟时间

        Args:
            attempt: 当前重试次数(从 1 开始)

        Returns:
            float: 延迟时间(秒)
        """
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        return min(delay, self.max_delay)

    def is_retryable(self, error: AIEngineError) -> bool:
        """判断错误是否可重试

        Args:
            error: 异常实例

        Returns:
            bool: 是否可重试
        """
        return error.code in self.retryable_codes


# 默认重试配置
DEFAULT_RETRY_CONFIG = RetryConfig()


# ==================== 错误处理装饰器 ====================

F = TypeVar("F", bound=Callable[..., Any])


def handle_agent_errors(
    default_agent_name: str = "unknown",
    reraise: bool = True,
    log_errors: bool = True,
) -> Callable[[F], F]:
    """Agent 错误处理装饰器

    自动捕获和转换常见异常为 AIEngineError 子类。

    Args:
        default_agent_name: 默认 Agent 名称
        reraise: 是否重新抛出异常
        log_errors: 是否记录错误日志

    Returns:
        装饰后的函数

    Example:
        @handle_agent_errors("PlannerAgent")
        async def run_agent(context):
            ...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except AIEngineError:
                # 已处理的错误直接抛出
                raise
            except asyncio.TimeoutError as e:
                error = LLMError("请求超时", code=ErrorCode.TIMEOUT, cause=e)
                if log_errors:
                    logger.error("Agent 超时: %s", error)
                if reraise:
                    raise error from e
                return None
            except asyncio.CancelledError:
                error = AgentError(
                    "操作被取消",
                    agent_name=default_agent_name,
                    code=ErrorCode.CANCELLED,
                )
                if log_errors:
                    logger.warning("Agent 取消: %s", error)
                raise
            except Exception as e:  # pylint: disable=broad-except
                error = AgentError(
                    str(e),
                    agent_name=default_agent_name,
                    code=ErrorCode.UNKNOWN,
                    cause=e,
                )
                if log_errors:
                    logger.error("Agent 未知错误: %s", error, exc_info=True)
                if reraise:
                    raise error from e
                return None

        return wrapper  # type: ignore

    return decorator


# ==================== 错误上下文管理器 ====================


@asynccontextmanager
async def error_context(
    operation: str, error_class: Type[AIEngineError] = AIEngineError, **context_data
):
    """错误上下文管理器

    为捕获的异常添加操作上下文信息。

    Args:
        operation: 操作描述
        error_class: 异常类型
        **context_data: 附加到异常详情的数据

    Yields:
        None

    Example:
        async with error_context("创建流程图", room_id="room_123"):
            await create_flowchart(...)
    """
    try:
        yield
    except AIEngineError as e:
        e.details["operation"] = operation
        e.details.update(context_data)
        raise
    except Exception as e:
        raise error_class(
            f"{operation}失败: {e}",
            details={"operation": operation, **context_data},
            cause=e,
        ) from e


# ==================== 异常工厂函数 ====================


def create_tool_not_found_error(tool_name: str) -> ToolError:
    """创建工具不存在异常"""
    return ToolError(
        f"工具不存在: {tool_name}", tool_name=tool_name, code=ErrorCode.TOOL_NOT_FOUND
    )


def create_room_not_found_error(room_id: str) -> RoomError:
    """创建房间不存在异常"""
    return RoomError(
        f"房间不存在: {room_id}", room_id=room_id, code=ErrorCode.ROOM_NOT_FOUND
    )


def create_validation_error(
    field_name: str, message: str, value: Any = None
) -> ValidationError:
    """创建参数验证异常"""
    return ValidationError(message, field_name=field_name, value=value)


def create_llm_timeout_error(provider: str, model: str, timeout: float) -> LLMError:
    """创建 LLM 超时异常"""
    return LLMError(
        f"LLM 请求超时 ({timeout}s)",
        code=ErrorCode.LLM_TIMEOUT,
        provider=provider,
        model=model,
        details={"timeout": timeout},
    )
