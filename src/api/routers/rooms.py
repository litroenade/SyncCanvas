import uuid
import hashlib
import secrets
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session
from src.application.diagrams import DiagramPatch, apply_diagram_patch, diagram_service
from src.auth.utils import get_current_user_optional, get_current_user
from src.infra.logging import get_logger
from src.persistence.db.engine import get_session
from src.persistence.db.models import Room, RoomMember
from src.persistence.db.models.users import User
from src.persistence.db.repositories import rooms as crud
from src.api.policy import PolicyErrorCode, policy_error
from src.realtime.yjs.server import websocket_server
from src.application.rooms.access import ensure_room_member_access, ensure_room_owner_access


router = APIRouter(prefix="/rooms", tags=["Rooms"])
logger = get_logger(__name__)


def _room_not_found_error(room_id: str) -> HTTPException:
    return policy_error(
        code=PolicyErrorCode.ROOM_NOT_FOUND,
        status_code=status.HTTP_404_NOT_FOUND,
        resource_id=room_id,
        action="room_access",
        message="room not found",
        reason="room_not_found",
    )


def _room_auth_error(
    room_id: str,
    *,
    message: str,
    status_code: int = status.HTTP_403_FORBIDDEN,
) -> HTTPException:
    return policy_error(
        code=PolicyErrorCode.AUTHZ_DENIED,
        status_code=status_code,
        resource_id=room_id,
        action="room_access",
        message=message,
        reason="room_membership_required",
    )


def _bad_request_error(message: str) -> HTTPException:
    return policy_error(
        code=message,
        status_code=status.HTTP_400_BAD_REQUEST,
        message=message,
        action="request_validation",
        reason=message,
    )


def _diagram_not_found_error(room_id: str, diagram_id: str) -> HTTPException:
    return policy_error(
        code="diagram_not_found",
        status_code=status.HTTP_404_NOT_FOUND,
        resource_id=room_id,
        action="diagram_access",
        message="diagram_not_found",
        reason=diagram_id,
    )


def hash_password(password: str) -> str:
    """Hash a room password with SHA-256 and a random salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plain-text room password against the stored hash."""
    try:
        salt, stored_hash = password_hash.split("$")
        computed_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        return secrets.compare_digest(computed_hash, stored_hash)
    except ValueError:
        return False

class RoomCreate(BaseModel):
    """Payload for creating a room."""

    name: str = Field(..., min_length=1, max_length=100)
    password: Optional[str] = Field(default=None, max_length=100)
    is_public: bool = Field(default=True)
    max_users: int = Field(default=10, ge=1, le=100)


class RoomJoin(BaseModel):
    """Payload for joining a room."""

    password: Optional[str] = Field(default=None)


class RoomResponse(BaseModel):
    """Room metadata returned by room APIs."""

    id: str
    name: str
    owner_id: Optional[int]
    is_public: bool
    max_users: int
    created_at: int
    has_password: bool
    member_count: int = 0
    elements_count: int = 0
    total_contributors: int = 0
    last_active_at: Optional[int] = None
    online_count: int = 0
    is_owner: bool = False


class RoomListResponse(BaseModel):
    """Room list response."""

    rooms: List[RoomResponse]
    total: int


class InviteLinkResponse(BaseModel):
    """Invite link payload."""

    room_id: str
    invite_url: str


class DiagramUpdateRequest(BaseModel):
    prompt: Optional[str] = None
    patch: Optional[dict] = None

@router.get("", response_model=RoomListResponse)
async def list_rooms(
    is_public: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """List rooms visible to the current user."""
    # Unauthenticated users can only see public rooms.
    if current_user is None:
        is_public = True

    rooms = crud.get_rooms(session, is_public=is_public, limit=limit, offset=offset)

    room_responses = []
    for room in rooms:
        members = crud.get_room_members(session, room.id)

        # WebSocket room keys are stored as /ws/{room_id}.
        online_count = websocket_server.get_room_connections(f"/ws/{room.id}")

        room_responses.append(
            RoomResponse(
                id=room.id,
                name=room.name,
                owner_id=room.owner_id,
                is_public=room.is_public,
                max_users=room.max_users,
                created_at=room.created_at,
                has_password=room.password_hash is not None,
                member_count=len(members),
                elements_count=room.elements_count,
                total_contributors=room.total_contributors,
                last_active_at=room.last_active_at,
                online_count=online_count,
                is_owner=bool(current_user and room.owner_id == current_user.id),
            )
        )

    return RoomListResponse(rooms=room_responses, total=len(room_responses))


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    request: RoomCreate,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Create a new room."""
    room_id = str(uuid.uuid4())

    # Hash the password only when provided.
    password_hash = None
    if request.password:
        password_hash = hash_password(request.password)

    room = Room(
        id=room_id,
        name=request.name,
        owner_id=current_user.id if current_user else None,
        password_hash=password_hash,
        is_public=request.is_public,
        max_users=request.max_users,
    )

    room = crud.create_room(session, room)
    logger.info("Created room: %s (%s)", room.name, room.id)

    # Automatically add the creator as owner.
    if current_user:
        member = RoomMember(room_id=room.id, user_id=current_user.id, role="owner")  # type: ignore[arg-type]
        crud.add_room_member(session, member)

    return RoomResponse(
        id=room.id,
        name=room.name,
        owner_id=room.owner_id,
        is_public=room.is_public,
        max_users=room.max_users,
        created_at=room.created_at,
        has_password=room.password_hash is not None,
        member_count=1 if current_user else 0,
        is_owner=bool(current_user),
    )


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: str,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Return room details by room id."""
    room = crud.get_room(session, room_id)
    if not room:
        raise _room_not_found_error(room_id)

    members = crud.get_room_members(session, room.id)

    return RoomResponse(
        id=room.id,
        name=room.name,
        owner_id=room.owner_id,
        is_public=room.is_public,
        max_users=room.max_users,
        created_at=room.created_at,
        has_password=room.password_hash is not None,
        member_count=len(members),
        is_owner=bool(current_user and room.owner_id == current_user.id),
    )


@router.post("/{room_id}/join")
async def join_room(
    room_id: str,
    request: RoomJoin,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Join a room after membership and password checks."""
    room = crud.get_room(session, room_id)
    if not room:
        raise _room_not_found_error(room_id)

    # Short-circuit when the user is already a member.
    existing_member = crud.get_room_member(session, room_id, current_user.id)  # type: ignore[arg-type]
    if existing_member:
        return {"status": "already_member", "room_id": room_id}

    # Validate the room password when required.
    if room.password_hash:
        if not request.password:
            raise _room_auth_error(
                room_id,
                message="password_required",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        if not verify_password(request.password, room.password_hash):
            raise _room_auth_error(
                room_id,
                message="invalid_token",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

    # Enforce the maximum room size.
    members = crud.get_room_members(session, room_id)
    if len(members) >= room.max_users:
        raise _room_auth_error(room_id, message="room_full", status_code=status.HTTP_403_FORBIDDEN)

    # Persist the new membership.
    member = RoomMember(room_id=room_id, user_id=current_user.id, role="editor")  # type: ignore[arg-type]
    crud.add_room_member(session, member)
    logger.info("User %s joined room %s", current_user.username, room_id)

    return {"status": "joined", "room_id": room_id}


class RoomDelete(BaseModel):
    """Payload for deleting a room."""

    password: Optional[str] = Field(default=None)


@router.delete("/{room_id}")
async def delete_room(
    room_id: str,
    request: Optional[RoomDelete] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Delete a room owned by the current user."""
    room = ensure_room_owner_access(session, room_id, current_user)

    # 如果房间有密码且非管理员，需要验证
    if room.password_hash and not current_user.is_admin:
        password = request.password if request else None
        if not password:
            raise _room_auth_error(
                room_id,
                message="password_required",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        if not verify_password(password, room.password_hash):
            raise _room_auth_error(
                room_id,
                message="invalid_token",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

    crud.delete_room(session, room_id)
    logger.info("Deleted room: %s (operator: %s)", room_id, current_user.username)

    return {"status": "deleted", "room_id": room_id}


@router.post("/{room_id}/leave")
async def leave_room(
    room_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Leave a room if the current user is not the owner."""
    room = crud.get_room(session, room_id)
    if not room:
        raise _room_not_found_error(room_id)

    # Owners must keep their membership.
    if room.owner_id == current_user.id:
        raise _room_auth_error(
            room_id,
            message="owner_cannot_leave_room",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    removed = crud.remove_room_member(session, room_id, current_user.id)  # type: ignore[arg-type]
    if not removed:
        raise _room_auth_error(
            room_id,
            message="member_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    logger.info("User %s left room %s", current_user.username, room_id)
    return {"status": "left", "room_id": room_id}


@router.get("/{room_id}/invite", response_model=InviteLinkResponse)
async def get_invite_link(room_id: str, session: Session = Depends(get_session)):
    """Return the invite link for a room."""
    room = crud.get_room(session, room_id)
    if not room:
        raise _room_not_found_error(room_id)

    # The frontend resolves the invite URL into a full link.
    invite_url = f"/join/{room_id}"

    return InviteLinkResponse(room_id=room_id, invite_url=invite_url)


@router.get("/{room_id}/diagrams")
async def get_room_diagrams(
    room_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List managed diagrams stored in the room Y.Doc."""
    ensure_room_member_access(session, room_id, current_user)
    specs = await diagram_service.list_room_diagrams(room_id)
    return {
        "room_id": room_id,
        "total": len(specs),
        "diagrams": [
            {
                "diagram_id": spec.diagram_id,
                "title": spec.title,
                "family": spec.family,
                "component_count": len(spec.components),
                "connector_count": len(spec.connectors),
            }
            for spec in specs
        ],
    }


@router.get("/{room_id}/diagrams/{diagram_id}")
async def get_room_diagram(
    room_id: str,
    diagram_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Load one managed diagram bundle."""
    ensure_room_member_access(session, room_id, current_user)
    bundle = await diagram_service.get_room_bundle(room_id, diagram_id)
    if not bundle:
        raise _diagram_not_found_error(room_id, diagram_id)
    return bundle.model_dump(by_alias=True)


@router.patch("/{room_id}/diagrams/{diagram_id}")
async def update_room_diagram(
    room_id: str,
    diagram_id: str,
    request: DiagramUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update a managed diagram from a prompt or a structured patch."""
    ensure_room_member_access(session, room_id, current_user)
    if request.prompt:
        try:
            updated = await diagram_service.update_from_prompt(room_id, diagram_id, request.prompt)
        except ValueError as exc:
            raise _diagram_not_found_error(room_id, diagram_id) from exc
        return updated.model_dump(by_alias=True)

    if request.patch:
        patch = DiagramPatch.model_validate({"diagramId": diagram_id, **request.patch})
        try:
            updated = await apply_diagram_patch(
                room_id,
                diagram_id,
                patch,
                last_edit_source="api",
            )
        except ValueError as exc:
            raise _diagram_not_found_error(room_id, diagram_id) from exc
        return updated.model_dump(by_alias=True)

    raise _bad_request_error("prompt_or_patch_required")


@router.post("/{room_id}/diagrams/{diagram_id}/rebuild")
async def rebuild_room_diagram(
    room_id: str,
    diagram_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Rebuild rendered elements from the stored spec."""
    ensure_room_member_access(session, room_id, current_user)
    try:
        rebuilt = await diagram_service.rebuild_bundle(room_id, diagram_id)
    except ValueError as exc:
        raise _diagram_not_found_error(room_id, diagram_id) from exc
    return rebuilt.model_dump(by_alias=True)


@router.get("/my/rooms", response_model=RoomListResponse)
async def get_my_rooms(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List rooms joined by the current user."""
    rooms = crud.get_user_rooms(session, current_user.id)  # type: ignore[arg-type]

    room_responses = []
    for room in rooms:
        members = crud.get_room_members(session, room.id)
        room_responses.append(
            RoomResponse(
                id=room.id,
                name=room.name,
                owner_id=room.owner_id,
                is_public=room.is_public,
                max_users=room.max_users,
                created_at=room.created_at,
                has_password=room.password_hash is not None,
                member_count=len(members),
                is_owner=room.owner_id == current_user.id,
            )
        )

    return RoomListResponse(rooms=room_responses, total=len(room_responses))




