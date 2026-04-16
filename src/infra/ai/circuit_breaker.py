"""Circuit breaker helpers for AI provider failover."""

import asyncio
from collections import deque
from dataclasses import dataclass
from time import monotonic
from typing import Deque

from src.infra.logging import get_logger

logger = get_logger(__name__)


class CircuitState:
    """Simple circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class _WindowPoint:
    ts: float
    success: bool


class CircuitBreaker:
    """Provider-level circuit breaker with sliding window metrics."""

    def __init__(
        self,
        name: str,
        *,
        failure_threshold: float = 0.4,
        min_requests: int = 10,
        window_seconds: float = 30.0,
        open_duration_seconds: float = 30.0,
        half_open_max_calls: int = 1,
        consecutive_success_to_close: int = 2,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.min_requests = min_requests
        self.window_seconds = window_seconds
        self.open_duration_seconds = open_duration_seconds
        self.half_open_max_calls = max(1, half_open_max_calls)
        self.consecutive_success_to_close = max(1, consecutive_success_to_close)
        self._lock = asyncio.Lock()
        self._state = CircuitState.CLOSED
        self._opened_until = 0.0
        self._window: Deque[_WindowPoint] = deque()
        self._half_open_calls = 0
        self._half_open_success = 0

    @property
    def state(self) -> str:
        return self._state

    async def before_request(self) -> bool:
        async with self._lock:
            now = monotonic()
            self._refresh(now)
            if self._state == CircuitState.OPEN and now < self._opened_until:
                return False
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    return False
                self._half_open_calls += 1
            return True

    async def on_success(self) -> None:
        async with self._lock:
            self._append_point(success=True)
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_success += 1
                if self._half_open_success >= self.consecutive_success_to_close:
                    self._transition_closed()
            elif self._state == CircuitState.CLOSED:
                self._ensure_closed()

    async def on_failure(self) -> None:
        async with self._lock:
            self._append_point(success=False)
            if self._state == CircuitState.HALF_OPEN:
                self._transition_open(reason="half-open-failed")
                return
            self._evaluate_state()

    def _refresh(self, now: float) -> None:
        while self._window and now - self._window[0].ts > self.window_seconds:
            self._window.popleft()
        if self._state == CircuitState.OPEN and now >= self._opened_until:
            self._transition_half_open()

    def _append_point(self, *, success: bool) -> None:
        now = monotonic()
        self._window.append(_WindowPoint(ts=now, success=success))
        self._refresh(now)

    def _evaluate_state(self) -> None:
        if len(self._window) < self.min_requests:
            return
        failures = len([point for point in self._window if not point.success])
        fail_rate = failures / len(self._window)
        if fail_rate >= self.failure_threshold:
            self._transition_open(reason=f"fail_rate={fail_rate:.2f}")

    def _transition_open(self, reason: str) -> None:
        now = monotonic()
        self._state = CircuitState.OPEN
        self._opened_until = now + self.open_duration_seconds
        self._half_open_calls = 0
        self._half_open_success = 0
        logger.warning(
            "Circuit breaker opened",
            extra={"name": self.name, "reason": reason, "state": self._state},
        )

    def _transition_half_open(self) -> None:
        self._state = CircuitState.HALF_OPEN
        self._half_open_calls = 0
        self._half_open_success = 0
        logger.info("Circuit breaker entering half-open", extra={"name": self.name})

    def _transition_closed(self) -> None:
        if self._state != CircuitState.CLOSED:
            logger.info("Circuit breaker closed", extra={"name": self.name})
        self._state = CircuitState.CLOSED
        self._half_open_calls = 0
        self._half_open_success = 0

    def _ensure_closed(self) -> None:
        self._half_open_calls = 0
        self._half_open_success = 0

    def snapshot(self) -> dict:
        return {
            "name": self.name,
            "state": self._state,
            "failure_rate": self._current_failure_rate(),
            "window_size": len(self._window),
            "opens_at": int(self._opened_until),
        }

    def _current_failure_rate(self) -> float:
        if not self._window:
            return 0.0
        failures = len([point for point in self._window if not point.success])
        return failures / len(self._window)


class AIProviderCircuitRegistry:
    """Cache circuit breakers per provider name."""

    def __init__(self) -> None:
        self._registry: dict[str, CircuitBreaker] = {}

    def get(self, name: str) -> CircuitBreaker:
        if name not in self._registry:
            self._registry[name] = CircuitBreaker(name)
        return self._registry[name]

    def snapshot(self) -> list[dict]:
        return [breaker.snapshot() for breaker in self._registry.values()]


ai_circuit_registry = AIProviderCircuitRegistry()

