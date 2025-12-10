"""模块名称: error_recovery
主要功能: Agent 错误恢复和重试策略

提供智能的错误恢复机制：
- 可重试错误分类
- 指数退避重试策略
- 错误上下文保存和恢复
- 优雅降级处理

@Time: 2025-12-10
@File: error_recovery.py
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar

from src.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class ErrorCategory(Enum):
    """错误类别"""

    # 可重试错误
    TRANSIENT = "transient"  # 临时性错误（网络波动等）
    RATE_LIMIT = "rate_limit"  # 限流错误
    TIMEOUT = "timeout"  # 超时错误

    # 不可重试错误
    VALIDATION = "validation"  # 参数验证错误
    PERMISSION = "permission"  # 权限错误
    NOT_FOUND = "not_found"  # 资源不存在

    # 需要人工干预
    FATAL = "fatal"  # 致命错误
    UNKNOWN = "unknown"  # 未知错误


@dataclass
class RetryPolicy:
    """重试策略"""

    max_retries: int = 3
    base_delay: float = 1.0  # 基础延迟（秒）
    max_delay: float = 60.0  # 最大延迟（秒）
    exponential_base: float = 2.0  # 指数基数
    jitter: bool = True  # 是否添加抖动

    def get_delay(self, attempt: int) -> float:
        """计算第 N 次重试的延迟时间

        Args:
            attempt: 当前重试次数 (从 0 开始)

        Returns:
            延迟时间（秒）
        """
        delay = min(self.base_delay * (self.exponential_base**attempt), self.max_delay)

        if self.jitter:
            # 添加 0-50% 的随机抖动
            delay = delay * (1 + random.random() * 0.5)

        return delay


@dataclass
class ErrorContext:
    """错误上下文"""

    error_type: str
    error_message: str
    category: ErrorCategory
    attempt: int = 0
    max_attempts: int = 3
    recoverable: bool = True
    context_data: Dict[str, Any] = field(default_factory=dict)
    recovery_hints: List[str] = field(default_factory=list)

    @property
    def can_retry(self) -> bool:
        """是否可以重试"""
        return (
            self.recoverable
            and self.attempt < self.max_attempts
            and self.category
            in {
                ErrorCategory.TRANSIENT,
                ErrorCategory.RATE_LIMIT,
                ErrorCategory.TIMEOUT,
            }
        )


class ErrorClassifier:
    """错误分类器"""

    # 错误关键词映射
    TRANSIENT_KEYWORDS = [
        "connection",
        "network",
        "socket",
        "reset",
        "temporary",
        "unavailable",
        "503",
        "502",
    ]

    RATE_LIMIT_KEYWORDS = [
        "rate limit",
        "too many requests",
        "429",
        "quota",
        "throttle",
        "slow down",
    ]

    TIMEOUT_KEYWORDS = [
        "timeout",
        "timed out",
        "deadline exceeded",
    ]

    VALIDATION_KEYWORDS = [
        "invalid",
        "validation",
        "required",
        "missing",
        "type error",
        "format",
    ]

    PERMISSION_KEYWORDS = [
        "permission",
        "forbidden",
        "403",
        "unauthorized",
        "401",
        "access denied",
    ]

    NOT_FOUND_KEYWORDS = [
        "not found",
        "404",
        "does not exist",
        "no such",
    ]

    @classmethod
    def classify(cls, error: Exception) -> ErrorCategory:
        """分类错误

        Args:
            error: 异常实例

        Returns:
            错误类别
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # 按优先级检查
        if any(kw in error_str for kw in cls.RATE_LIMIT_KEYWORDS):
            return ErrorCategory.RATE_LIMIT

        if any(kw in error_str for kw in cls.TIMEOUT_KEYWORDS):
            return ErrorCategory.TIMEOUT

        if any(kw in error_str for kw in cls.TRANSIENT_KEYWORDS):
            return ErrorCategory.TRANSIENT

        if any(kw in error_str for kw in cls.VALIDATION_KEYWORDS):
            return ErrorCategory.VALIDATION

        if any(kw in error_str for kw in cls.PERMISSION_KEYWORDS):
            return ErrorCategory.PERMISSION

        if any(kw in error_str for kw in cls.NOT_FOUND_KEYWORDS):
            return ErrorCategory.NOT_FOUND

        # 特殊异常类型
        if "timeout" in error_type:
            return ErrorCategory.TIMEOUT

        if "connection" in error_type:
            return ErrorCategory.TRANSIENT

        return ErrorCategory.UNKNOWN


class ErrorRecoveryManager:
    """错误恢复管理器

    提供统一的错误处理和恢复机制。

    Example:
        ```python
        manager = ErrorRecoveryManager()

        async def risky_operation():
            # 可能失败的操作
            pass

        result = await manager.execute_with_recovery(
            risky_operation,
            context_data={"operation": "create_element"},
        )
        ```
    """

    def __init__(self, default_policy: Optional[RetryPolicy] = None):
        """初始化管理器

        Args:
            default_policy: 默认重试策略
        """
        self.default_policy = default_policy or RetryPolicy()
        self._error_handlers: Dict[ErrorCategory, Callable] = {}

    def register_handler(
        self,
        category: ErrorCategory,
        handler: Callable[[ErrorContext], Optional[Any]],
    ) -> None:
        """注册错误处理器

        Args:
            category: 错误类别
            handler: 处理函数，返回恢复值或 None
        """
        self._error_handlers[category] = handler

    async def execute_with_recovery(
        self,
        func: Callable[..., T],
        *args,
        policy: Optional[RetryPolicy] = None,
        context_data: Optional[Dict[str, Any]] = None,
        on_retry: Optional[Callable[[ErrorContext], None]] = None,
        **kwargs,
    ) -> T:
        """带错误恢复的执行

        Args:
            func: 要执行的函数
            *args: 位置参数
            policy: 重试策略
            context_data: 上下文数据
            on_retry: 重试回调
            **kwargs: 关键字参数

        Returns:
            函数执行结果

        Raises:
            Exception: 所有重试都失败后抛出最后一个异常
        """
        policy = policy or self.default_policy
        last_error: Optional[Exception] = None

        for attempt in range(policy.max_retries + 1):
            try:
                # 判断是否是协程函数
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

            except Exception as e:
                last_error = e
                category = ErrorClassifier.classify(e)

                error_ctx = ErrorContext(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    category=category,
                    attempt=attempt,
                    max_attempts=policy.max_retries,
                    context_data=context_data or {},
                )

                # 检查是否可重试
                if not error_ctx.can_retry:
                    logger.warning(f"不可重试的错误: {category.value}, {e}")

                    # 尝试调用错误处理器
                    if category in self._error_handlers:
                        handler_result = self._error_handlers[category](error_ctx)
                        if handler_result is not None:
                            return handler_result

                    raise

                # 重试回调
                if on_retry:
                    on_retry(error_ctx)

                # 计算延迟
                delay = policy.get_delay(attempt)
                logger.info(
                    f"重试 {attempt + 1}/{policy.max_retries}: "
                    f"{category.value}, 延迟 {delay:.2f}s"
                )

                await asyncio.sleep(delay)

        # 所有重试都失败
        raise last_error


# 全局实例
error_recovery = ErrorRecoveryManager()


# 便捷装饰器
def with_retry(
    policy: Optional[RetryPolicy] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
):
    """重试装饰器

    Example:
        ```python
        @with_retry(policy=RetryPolicy(max_retries=5))
        async def fetch_data():
            # 可能失败的操作
            pass
        ```
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        async def wrapper(*args, **kwargs) -> T:
            return await error_recovery.execute_with_recovery(
                func,
                *args,
                policy=policy,
                on_retry=lambda ctx: on_error(Exception(ctx.error_message))
                if on_error
                else None,
                **kwargs,
            )

        return wrapper

    return decorator
