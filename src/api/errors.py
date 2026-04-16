"""Shared API error helpers."""

from fastapi import HTTPException, status

from src.api.policy import PolicyErrorCode, build_error_payload


def policy_http_error(
    *,
    code: str,
    message: str,
    request_id: str | None = None,
) -> HTTPException:
    """Build a policy-shaped HTTPException for API routes."""

    payload = build_error_payload(
        code=code,
        message=message,
        trace_id=request_id,
        reason=message,
    )

    if code == PolicyErrorCode.AUTHZ_DENIED:
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=payload)
    if code == PolicyErrorCode.RATE_LIMIT_EXCEEDED:
        return HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=payload)
    if code == PolicyErrorCode.AI_CIRCUIT_OPEN:
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=payload)
    if code == PolicyErrorCode.ROOM_NOT_FOUND:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=payload)
    if code.endswith("_not_found"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=payload)
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=payload)


