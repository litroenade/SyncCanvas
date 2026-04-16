"""Simple in-memory rate limiting middleware and WebSocket helper."""


import hashlib
import time
from collections import deque
from dataclasses import dataclass
from threading import RLock
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.infra.metrics import inc_counter
from src.api.policy import PolicyErrorCode, policy_error_http_exception


@dataclass(frozen=True)
class _BucketRule:
    name: str
    limit: int
    window_seconds: int


@dataclass
class _BucketState:
    hits: deque[float]


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_seconds: int
    limit: int


def _to_user_bucket_key(raw_token: Optional[str], room_id: Optional[str] = None) -> str:
    if not raw_token:
        return "anon"
    digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()[:12]
    return f"{digest}:{room_id}" if room_id else digest


def _to_limit_headers(limit: int, remaining: int, reset_seconds: int) -> dict[str, str]:
    return {
        "RateLimit-Limit": str(limit),
        "RateLimit-Remaining": str(max(0, remaining)),
        "RateLimit-Reset": str(max(0, reset_seconds)),
    }


class _WindowLimiter:
    def __init__(self) -> None:
        self._state: dict[str, _BucketState] = {}
        self._lock = RLock()

    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        now = time.monotonic()
        cutoff = now - window_seconds

        with self._lock:
            state = self._state.setdefault(key, _BucketState(hits=deque()))
            while state.hits and state.hits[0] < cutoff:
                state.hits.popleft()

            if len(state.hits) >= limit:
                retry_after = int(max(0.0, state.hits[0] + window_seconds - now))
                return RateLimitResult(False, 0, retry_after, limit)

            state.hits.append(now)
            remaining = max(0, limit - len(state.hits))
            return RateLimitResult(True, remaining, 0, limit)


_DEFAULT_RULES = [
    _BucketRule(name="ip", limit=120, window_seconds=60),
    _BucketRule(name="user", limit=300, window_seconds=60),
    _BucketRule(name="room", limit=200, window_seconds=60),
    _BucketRule(name="ai", limit=120, window_seconds=60),
]

_limiter = _WindowLimiter()


def _extract_room_id_from_path(path: str) -> Optional[str]:
    if path.startswith("/api/ai/stream/"):
        room_id = path.split("/api/ai/stream/", 1)[-1]
        return room_id.split("/")[0] or None

    if path.startswith("/api/rooms/"):
        suffix = path[len("/api/rooms/") :]
        return suffix.split("/")[0] or None

    if path.startswith("/api/version_control/"):
        suffix = path[len("/api/version_control/") :]
        return suffix.split("/")[0] or None

    if path.startswith("/api/ai/runs/") or path.startswith("/api/ai/status/"):
        suffix = path.rsplit("/", 1)[-1]
        return suffix or None

    return None


def _extract_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token.strip()
    return ""


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit HTTP API requests by IP/user/room and AI endpoint."""

    def __init__(
        self,
        app,
        *,
        enabled: bool = True,
        rules: Optional[list[_BucketRule]] = None,
    ) -> None:
        super().__init__(app)
        self.enabled = enabled
        self._rules = rules or _DEFAULT_RULES

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        path = request.url.path or ""
        if not path.startswith("/api"):
            return await call_next(request)

        room_id = _extract_room_id_from_path(path)
        token = _extract_token(request)
        ip = request.client.host if request.client and request.client.host else "anon"

        checks: list[tuple[str, RateLimitResult]] = []
        planned_checks = [
            ("ip", f"ip:{ip}", self._rules[0]),
            ("user", f"user:{_to_user_bucket_key(token)}", self._rules[1]),
        ]
        if room_id:
            planned_checks.append(("room", f"room:{room_id}", self._rules[2]))
        if path.startswith("/api/ai"):
            planned_checks.append(
                ("ai", f"ai:{ip}:{_to_user_bucket_key(token, room_id)}", self._rules[3]),
            )

        for _, key, rule in planned_checks:
            result = _limiter.check(key, rule.limit, rule.window_seconds)
            checks.append((rule.name, result))
            if not result.allowed:
                inc_counter(
                    "rate_limit_block_total",
                    labels={"bucket": rule.name, "path": path},
                )
                headers = _to_limit_headers(
                    result.limit,
                    result.remaining,
                    result.reset_seconds,
                )
                payload = policy_error_http_exception(
                    code=PolicyErrorCode.RATE_LIMIT_EXCEEDED,
                    status_code=429,
                    message="rate limit exceeded",
                    action=rule.name,
                    reason="rate_limit",
                ).detail
                request.state.rate_limit_headers = headers
                return JSONResponse(status_code=429, content=payload, headers=headers)

        # Use the most restrictive remaining quota as the response header snapshot.
        if checks:
            selected = min(checks, key=lambda item: item[1].remaining)
            response_headers = _to_limit_headers(
                selected[1].limit,
                selected[1].remaining,
                selected[1].reset_seconds,
            )
        else:
            response_headers = {"RateLimit-Limit": "0", "RateLimit-Remaining": "0", "RateLimit-Reset": "0"}

        response = await call_next(request)
        response.headers.update(response_headers)
        request.state.rate_limit_headers = response_headers
        return response


def check_rate_limit_for_room(
    *,
    path: str,
    room_id: Optional[str],
    token: Optional[str],
    client_host: Optional[str],
    rules: Optional[dict[str, int]] = None,
) -> tuple[bool, dict[str, str]]:
    """Share limiter helper for websocket handlers."""
    token = token or ""
    ip = client_host or "anon"
    rule_map = {
        "ip": 120,
        "user": 300,
        "room": 200,
        "ai": 120,
    }
    if rules:
        rule_map.update(rules)

    checks = [
        ("ip", f"ip:{ip}", rule_map["ip"]),
        ("user", f"user:{_to_user_bucket_key(token)}", rule_map["user"]),
    ]
    if room_id:
        checks.append(("room", f"room:{room_id}", rule_map["room"]))
    if path.startswith("/api/ai"):
        checks.append(("ai", f"ai:{ip}:{_to_user_bucket_key(token, room_id)}", rule_map["ai"]))

    results: list[tuple[str, RateLimitResult]] = []
    for name, key, limit in checks:
        result = _limiter.check(key, limit, 60)
        results.append((name, result))
        if not result.allowed:
            return False, _to_limit_headers(limit, result.remaining, result.reset_seconds)

    selected = min(results, key=lambda item: item[1].remaining)
    selected_state = selected[1]
    return (
        True,
        _to_limit_headers(
            selected_state.limit,
            selected_state.remaining,
            selected_state.reset_seconds,
        ),
    )

