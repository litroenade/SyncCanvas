"""Policy and policy error helpers.

Provides a light-weight policy abstraction used by HTTP/WS entrypoints to align
error codes and optional legacy reason mapping.
"""


from dataclasses import dataclass
from typing import Any, Dict, Optional
from fastapi import HTTPException, status

from src.infra.logging import get_logger

logger = get_logger(__name__)


class PolicyErrorCode:
    """Centralized error code constants."""

    AUTHZ_DENIED = "AUTHZ_DENIED"
    ROOM_NOT_FOUND = "ROOM_NOT_FOUND"
    ROOM_MEMBERSHIP_REQUIRED = "ROOM_MEMBERSHIP_REQUIRED"
    RECONNECT_REQUIRES_SNAPSHOT = "RECONNECT_REQUIRES_SNAPSHOT"
    AI_CIRCUIT_OPEN = "AI_CIRCUIT_OPEN"
    TXN_ROLLBACK = "TXN_ROLLBACK"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"


_LEGACY_ROOM_REASON_BY_HTTP_CODE = {
    status.HTTP_401_UNAUTHORIZED: "authentication_required",
    status.HTTP_404_NOT_FOUND: "room_not_found",
    status.HTTP_403_FORBIDDEN: "room_membership_required",
}


@dataclass
class PolicyError(Exception):
    """Structured policy error."""

    code: str
    message: str
    status_code: int
    actor_id: Optional[int] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None
    trace_id: Optional[str] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "status_code": self.status_code,
            "actor_id": self.actor_id,
            "resource_id": self.resource_id,
            "action": self.action,
            "trace_id": self.trace_id,
            "reason": self.reason,
        }


def build_error_payload(
    code: str,
    *,
    message: Optional[str] = None,
    actor_id: Optional[int] = None,
    resource_id: Optional[str] = None,
    action: Optional[str] = None,
    trace_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a normalized policy response payload."""
    return {
        "code": code,
        "message": message or code,
        "actor_id": actor_id,
        "resource_id": resource_id,
        "action": action,
        "trace_id": trace_id,
        "reason": reason,
    }


def policy_error(
    *,
    code: str,
    status_code: int,
    message: Optional[str] = None,
    actor_id: Optional[int] = None,
    resource_id: Optional[str] = None,
    action: Optional[str] = None,
    trace_id: Optional[str] = None,
    reason: Optional[str] = None,
    use_legacy_detail: bool = False,
) -> HTTPException:
    """Alias for creating policy errors with structured payload."""
    return policy_error_http_exception(
        code=code,
        status_code=status_code,
        message=message,
        actor_id=actor_id,
        resource_id=resource_id,
        action=action,
        trace_id=trace_id,
        reason=reason,
        use_legacy_detail=use_legacy_detail,
    )


def policy_forbid(
    *,
    actor_id: Optional[int],
    resource_id: Optional[str] = None,
    action: str = "",
    detail: str = "forbidden",
    trace_id: Optional[str] = None,
) -> HTTPException:
    """Shortcut helper for deny conditions."""
    return policy_error(
        code=PolicyErrorCode.AUTHZ_DENIED,
        status_code=status.HTTP_403_FORBIDDEN,
        message=detail,
        actor_id=actor_id,
        resource_id=resource_id,
        action=action,
        trace_id=trace_id,
        reason=detail,
        use_legacy_detail=False,
    )


def _legacy_reason_from_http_error(exc: HTTPException) -> str:
    detail = str(exc.detail)
    if exc.status_code in _LEGACY_ROOM_REASON_BY_HTTP_CODE:
        mapped = _LEGACY_ROOM_REASON_BY_HTTP_CODE[exc.status_code]
        if isinstance(detail, str) and "room" in detail:
            return detail
        return mapped
    return str(exc.detail)


def normalize_http_exception(
    exc: HTTPException,
    *,
    use_legacy_detail: bool = False,
) -> HTTPException:
    """Normalize fastapi HTTP exceptions into standard policy detail shape.

    Args:
        exc: Original HTTP exception.
        use_legacy_detail: Keep old room-access error detail for backward
            compatibility.
    """
    detail = exc.detail
    if isinstance(detail, dict):
        if "code" in detail:
            return exc

    if not isinstance(detail, str):
        return exc

    if detail in {
        "room_not_found",
        "room_membership_required",
        "room_owner_required",
        "room_not_accessible",
        "AI_CIRCUIT_OPEN",
    }:
        return exc

    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        code = PolicyErrorCode.AUTHZ_DENIED
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        code = PolicyErrorCode.AUTHZ_DENIED
    elif exc.status_code == status.HTTP_404_NOT_FOUND:
        code = PolicyErrorCode.ROOM_NOT_FOUND
    else:
        code = str(detail)

    if use_legacy_detail:
        message = _legacy_reason_from_http_error(exc)
    else:
        message = code
    return HTTPException(status_code=exc.status_code, detail=message)


def policy_error_http_exception(
    *,
    code: str,
    status_code: int,
    message: Optional[str] = None,
    actor_id: Optional[int] = None,
    resource_id: Optional[str] = None,
    action: Optional[str] = None,
    trace_id: Optional[str] = None,
    reason: Optional[str] = None,
    use_legacy_detail: bool = False,
) -> HTTPException:
    """Create standardized HTTPException payload."""
    if message is None:
        message = code

    payload: str | Dict[str, Any]
    if use_legacy_detail:
        if code == PolicyErrorCode.ROOM_NOT_FOUND:
            payload = "room_not_found"
        elif code == PolicyErrorCode.ROOM_MEMBERSHIP_REQUIRED:
            payload = "room_membership_required"
        elif code == PolicyErrorCode.AUTHZ_DENIED:
            payload = "authentication_required"
        else:
            payload = code
    else:
        payload = {
            "code": code,
            "message": message,
            "actor_id": actor_id,
            "resource_id": resource_id,
            "action": action,
            "trace_id": trace_id,
            "reason": reason,
        }

    logger.warning(
        "Policy denied",
        extra={
            "code": code,
            "status_code": status_code,
            "actor_id": actor_id,
            "resource_id": resource_id,
            "action": action,
            "trace_id": trace_id,
            "reason": reason,
        },
    )

    return HTTPException(status_code=status_code, detail=payload)

