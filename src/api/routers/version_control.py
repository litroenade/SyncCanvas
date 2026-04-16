from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from src.api.policy import policy_error
from src.application.rooms.access import ensure_room_member_access
from src.application.versioning.service import get_version_control_service
from src.auth.utils import get_current_user
from src.domain.versioning.models import (
    CommitDetailResponse,
    CommitDiffResponse,
    HistoryResponse,
)
from src.infra.logging import get_logger
from src.persistence.db.engine import get_session
from src.persistence.db.models import Commit
from src.persistence.db.models.users import User
from src.realtime.yjs.server import websocket_server


ROOM_NOT_FOUND_MESSAGES = {"room_not_found"}
COMMIT_NOT_FOUND_MESSAGES = {
    "commit_not_found",
    "target_commit_not_found",
    "base_commit_not_found",
}


def _vc_not_found_error(message: str) -> HTTPException:
    normalized = message.strip()
    if normalized in ROOM_NOT_FOUND_MESSAGES:
        return policy_error(
            code="room_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
            message="room_not_found",
            action="version_control_access",
            reason="room_not_found",
        )
    if normalized in COMMIT_NOT_FOUND_MESSAGES:
        return policy_error(
            code="commit_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
            message="commit_not_found",
            action="version_control_access",
            reason="commit_not_found",
        )
    return policy_error(
        code="resource_not_found",
        status_code=status.HTTP_404_NOT_FOUND,
        message="resource_not_found",
        action="version_control_access",
        reason="resource_not_found",
    )


def _vc_commit_not_found_error(commit_id: int) -> HTTPException:
    return policy_error(
        code="commit_not_found",
        status_code=status.HTTP_404_NOT_FOUND,
        resource_id=str(commit_id),
        action="version_control_access",
        message="commit_not_found",
        reason="commit_not_found",
    )


class CreateCommitRequest(BaseModel):
    """Version-control commit payload."""

    message: str = Field(default="manual_save", max_length=500)
    author_name: Optional[str] = Field(default=None, max_length=100)


router = APIRouter(prefix="/rooms", tags=["version_control"])
logger = get_logger(__name__)


@router.get("/{room_id}/history", response_model=HistoryResponse)
async def get_room_history(
    room_id: str,
    limit: int = 50,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Return commit history for a room."""

    ensure_room_member_access(session, room_id, current_user)
    service = get_version_control_service(session)
    try:
        return service.get_history(room_id, limit, websocket_server=websocket_server)
    except ValueError as exc:
        raise _vc_not_found_error(str(exc)) from exc


@router.post("/{room_id}/commit")
async def create_commit(
    room_id: str,
    request: CreateCommitRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new commit snapshot for the room."""

    ensure_room_member_access(session, room_id, current_user)
    service = get_version_control_service(session)

    author_id = current_user.id if current_user else None
    if request.author_name:
        author_name = request.author_name
    elif current_user:
        author_name = current_user.username
    else:
        author_name = "Anonymous"

    try:
        commit = await service.create_commit(
            room_id=room_id,
            message=request.message,
            author_id=author_id,
            author_name=author_name,
            websocket_server=websocket_server,
        )
        return {
            "status": "created",
            "commit": {
                "id": commit.id,
                "hash": commit.hash,
                "message": commit.message,
                "author_name": commit.author_name,
                "timestamp": commit.timestamp,
            },
        }
    except ValueError as exc:
        raise policy_error(
            code="validation_error",
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(exc),
            action="version_commit",
            reason=str(exc),
        ) from exc


@router.post("/{room_id}/checkout/{commit_id}")
async def checkout_commit(
    room_id: str,
    commit_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Checkout the requested commit into the room."""

    ensure_room_member_access(session, room_id, current_user)
    service = get_version_control_service(session)
    try:
        commit = await service.checkout_commit(
            room_id=room_id,
            commit_id=commit_id,
            websocket_server=websocket_server,
        )
        return {
            "status": "checked_out",
            "commit_id": commit.id,
            "commit_hash": commit.hash,
            "message": f"checked_out:{commit.hash}",
        }
    except ValueError as exc:
        raise _vc_not_found_error(str(exc)) from exc


@router.post("/{room_id}/revert/{commit_id}")
async def revert_commit(
    room_id: str,
    commit_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a revert commit from a historical commit."""

    ensure_room_member_access(session, room_id, current_user)
    service = get_version_control_service(session)

    author_id = current_user.id if current_user else None
    author_name = current_user.username if current_user else "Anonymous"

    try:
        new_commit, target_commit = await service.revert_commit(
            room_id=room_id,
            commit_id=commit_id,
            author_id=author_id,  # type: ignore[arg-type]
            author_name=author_name,
            websocket_server=websocket_server,
        )
        return {
            "status": "reverted",
            "new_commit": {
                "id": new_commit.id,
                "hash": new_commit.hash,
                "message": new_commit.message,
            },
            "reverted_to": {"id": target_commit.id, "hash": target_commit.hash},
        }
    except ValueError as exc:
        raise _vc_not_found_error(str(exc)) from exc


@router.get("/{room_id}/commits", response_model=HistoryResponse)
async def get_commits(
    room_id: str,
    limit: int = 50,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Compatibility alias for the room history endpoint."""

    return await get_room_history(room_id, limit, session, current_user)


@router.get("/{room_id}/commits/{commit_id}", response_model=CommitDetailResponse)
async def get_commit_detail(
    room_id: str,
    commit_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Return metadata for a single commit."""

    ensure_room_member_access(session, room_id, current_user)
    service = get_version_control_service(session)
    try:
        return service.get_commit_detail(room_id, commit_id)
    except ValueError as exc:
        raise _vc_not_found_error(str(exc)) from exc


@router.get("/{room_id}/commits/{commit_id}/data")
async def get_commit_data(
    room_id: str,
    commit_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Return the raw Yjs payload for a commit."""

    ensure_room_member_access(session, room_id, current_user)

    commit = session.get(Commit, commit_id)
    if not commit or commit.room_id != room_id:
        raise _vc_commit_not_found_error(commit_id)

    return Response(content=commit.data, media_type="application/octet-stream")


@router.get("/{room_id}/diff/{commit_id}", response_model=CommitDiffResponse)
async def get_commit_diff(
    room_id: str,
    commit_id: int,
    base_commit_id: Optional[int] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Return the diff between two commits."""

    ensure_room_member_access(session, room_id, current_user)
    service = get_version_control_service(session)
    try:
        return service.get_commit_diff(room_id, commit_id, base_commit_id)
    except ValueError as exc:
        raise _vc_not_found_error(str(exc)) from exc
