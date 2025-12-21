"""模块名称: retry
主要功能: 重试策略和错误恢复
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Callable, Optional, TypeVar
from src.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class RetryPolicy:
    """重试策略"""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True

    def get_delay(self, attempt: int) -> float:
        delay = min(self.base_delay * (self.exponential_base**attempt), self.max_delay)
        if self.jitter:
            delay = delay * (1 + random.random() * 0.5)
        return delay


class ErrorRecoveryManager:
    """错误恢复管理器"""

    def __init__(self, default_policy: Optional[RetryPolicy] = None):
        self.default_policy = default_policy or RetryPolicy()

    async def execute_with_recovery(
        self,
        func: Callable[..., T],
        *args,
        policy: Optional[RetryPolicy] = None,
        **kwargs,
    ) -> T:
        policy = policy or self.default_policy
        last_error: Optional[Exception] = None
        for attempt in range(policy.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)  # type: ignore[return-value]
            except Exception as e:  # pylint: disable=broad-except
                last_error = e
                if attempt < policy.max_retries:
                    delay = policy.get_delay(attempt)
                    logger.info(
                        "重试 %d/%d, 延迟 %.1fs", attempt + 1, policy.max_retries, delay
                    )
                    await asyncio.sleep(delay)
        raise last_error or Exception("未知错误")
