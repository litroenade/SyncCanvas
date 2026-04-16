"""Shared room-scoped authorization helpers."""

from typing import Optional
import re

from fastapi import HTTPException, status
from sqlmodel import Session

from src.auth.utils import extract_bearer_token, get_user_from_token
from src.infra.singleton_canvas import (
    SINGLETON_CANVAS_ID,
    ensure_singleton_room,
    ensure_singleton_user,
)
from src.persistence.db.engine import engine
from src.persistence.db.models import AgentRun, Conversation, Room, RoomMember
from src.persistence.db.models.users import User
from src.persistence.db.repositories import rooms as room_repo
from src.api.policy import PolicyErrorCode, policy_forbid, policy_error

WS_AUTHENTICATION_REQUIRED = "authentication_required"
WS_INVALID_TOKEN = "invalid_token"
WS_ROOM_NOT_FOUND = "room_not_found"
WS_ROOM_MEMBERSHIP_REQUIRED = "room_membership_required"
_ROOM_NOT_FOUND_REASON_RE = re.compile(r"涓嶅瓨鍦▅not\\s+found", re.IGNORECASE)


def get_room_or_404(session: Session, room_id: str) -> Room:
    room = room_repo.get_room(session, room_id)
    if not room:
        raise policy_error(
            code=PolicyErrorCode.ROOM_NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            resource_id=room_id,
            action="read_room",
            message="room not found",
            reason=WS_ROOM_NOT_FOUND,
        )
    return room


def ensure_room_member_access(session: Session, room_id: str, current_user: User) -> Room:
    if room_id == SINGLETON_CANVAS_ID:
        return ensure_singleton_room(session, ensure_singleton_user(session))
    room = get_room_or_404(session, room_id)
    user_id = current_user.id
    if current_user.is_admin:
        return room
    if user_id is None:
        raise policy_forbid(
            actor_id=user_id,
            resource_id=room_id,
            action="room_access",
            detail=PolicyErrorCode.ROOM_MEMBERSHIP_REQUIRED,
        )
    if room.owner_id == user_id:
        return room
    member = room_repo.get_room_member(session, room_id, user_id)
    if member is None:
        raise policy_forbid(
            actor_id=user_id,
            resource_id=room_id,
            action="room_access",
            detail=PolicyErrorCode.ROOM_MEMBERSHIP_REQUIRED,
        )
    return room


def ensure_room_owner_access(session: Session, room_id: str, current_user: User) -> Room:
    if room_id == SINGLETON_CANVAS_ID:
        return ensure_singleton_room(session, ensure_singleton_user(session))
    room = get_room_or_404(session, room_id)
    if current_user.is_admin:
        return room

    user_id = current_user.id
    if user_id is None:
        raise policy_forbid(
            actor_id=user_id,
            resource_id=room_id,
            action="room_owner_access",
            detail=PolicyErrorCode.ROOM_MEMBERSHIP_REQUIRED,
        )

    if room.owner_id == user_id:
        return room

    member = room_repo.get_room_member(session, room_id, user_id)
    if member and member.role == "owner":
        return room

    raise policy_forbid(
        actor_id=user_id,
        resource_id=room_id,
        action="room_owner_access",
        detail="room_owner_required",
    )


def ensure_run_room_access(session: Session, run_id: int, current_user: User) -> AgentRun:
    run = session.get(AgentRun, run_id)
    if not run:
        raise policy_error(
            code="run_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
            resource_id=str(run_id),
            action="run_access",
            message="run_not_found",
            reason="run_not_found",
        )
    ensure_room_member_access(session, run.room_id, current_user)
    return run


def ensure_conversation_room_access(
    session: Session,
    room_id: str,
    conversation_id: int,
    current_user: User,
) -> Conversation:
    conversation = session.get(Conversation, conversation_id)
    if not conversation or conversation.room_id != room_id:
        raise policy_error(
            code="conversation_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
            resource_id=str(conversation_id),
            action="conversation_access",
            message="conversation_not_found",
            reason="conversation_not_found",
        )
    ensure_room_member_access(session, room_id, current_user)
    return conversation


def _websocket_access_exception(status_code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


def _normalize_websocket_access_error(exc: HTTPException) -> HTTPException:
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code") if isinstance(detail, dict) else None
        action = str(detail.get("action", ""))
        resource = detail.get("resource_id")
        if code == PolicyErrorCode.ROOM_NOT_FOUND:
            return policy_error(
                code=PolicyErrorCode.ROOM_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND,
                message=PolicyErrorCode.ROOM_NOT_FOUND,
                action=action,
                resource_id=str(resource) if resource else None,
                reason=WS_ROOM_NOT_FOUND,
            )
        if code == PolicyErrorCode.ROOM_MEMBERSHIP_REQUIRED:
            return policy_error(
                code=PolicyErrorCode.AUTHZ_DENIED,
                status_code=status.HTTP_403_FORBIDDEN,
                message=PolicyErrorCode.ROOM_MEMBERSHIP_REQUIRED,
                action=action,
                resource_id=str(resource) if resource else None,
                reason=WS_ROOM_MEMBERSHIP_REQUIRED,
            )

    if detail == WS_ROOM_NOT_FOUND:
        return _websocket_access_exception(status.HTTP_404_NOT_FOUND, WS_ROOM_NOT_FOUND)
    if detail == WS_ROOM_MEMBERSHIP_REQUIRED:
        return _websocket_access_exception(
            status.HTTP_403_FORBIDDEN,
            WS_ROOM_MEMBERSHIP_REQUIRED,
        )
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        return _websocket_access_exception(status.HTTP_404_NOT_FOUND, WS_ROOM_NOT_FOUND)
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return _websocket_access_exception(status.HTTP_401_UNAUTHORIZED, WS_INVALID_TOKEN)
    if exc.status_code == status.HTTP_403_FORBIDDEN:
        return _websocket_access_exception(
            status.HTTP_403_FORBIDDEN,
            WS_ROOM_MEMBERSHIP_REQUIRED,
        )
    return _websocket_access_exception(
        status.HTTP_403_FORBIDDEN,
        WS_ROOM_MEMBERSHIP_REQUIRED,
    )


def resolve_websocket_room_user(
    room_id: str,
    *,
    token: Optional[str] = None,
    authorization: Optional[str] = None,
) -> User:
    raw_token = token or extract_bearer_token(authorization)
    with Session(engine) as session:
        current_user = get_user_from_token(raw_token, session, raise_on_error=False)
        if current_user is None:
            current_user = ensure_singleton_user(session)

        try:
            ensure_room_member_access(session, room_id, current_user)
        except HTTPException as exc:
            raise _normalize_websocket_access_error(exc) from exc
        return current_user

