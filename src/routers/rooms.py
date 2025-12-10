"""模块名称: rooms
主要功能: 房间管理 REST API 路由
"""

import uuid
import hashlib
import secrets
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from src.config import config
from src.db.database import get_session
from src.db.models import Room, RoomMember
from src.db import crud
from src.auth.utils import get_current_user_optional, get_current_user
from src.db.user import User
from src.logger import get_logger
from src.ws.sync import websocket_server


router = APIRouter(prefix="/rooms", tags=["Rooms"])
logger = get_logger(__name__)


def hash_password(password: str) -> str:
    """使用 SHA-256 + salt 哈希密码

    Args:
        password: 明文密码

    Returns:
        str: 哈希后的密码 (格式: salt$hash)
    """
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码

    Args:
        password: 明文密码
        password_hash: 哈希后的密码

    Returns:
        bool: 密码是否正确
    """
    try:
        salt, stored_hash = password_hash.split("$")
        computed_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        return secrets.compare_digest(computed_hash, stored_hash)
    except ValueError:
        return False


# ==================== 请求/响应模型 ====================


class RoomCreate(BaseModel):
    """创建房间请求

    Attributes:
        name (str): 房间名称
        password (str): 房间密码，可选
        is_public (bool): 是否公开
        max_users (int): 最大用户数
    """

    name: str = Field(..., min_length=1, max_length=100)
    password: Optional[str] = Field(default=None, max_length=100)
    is_public: bool = Field(default=True)
    max_users: int = Field(default=10, ge=1, le=100)


class RoomJoin(BaseModel):
    """加入房间请求

    Attributes:
        password (str): 房间密码，可选
    """

    password: Optional[str] = Field(default=None)


class RoomResponse(BaseModel):
    """房间响应

    Attributes:
        id (str): 房间 ID
        name (str): 房间名称
        owner_id (int): 创建者 ID
        is_public (bool): 是否公开
        max_users (int): 最大用户数
        created_at (int): 创建时间戳
        has_password (bool): 是否有密码
        member_count (int): 当前成员数
        elements_count (int): 画布元素数量
        total_contributors (int): 历史贡献者数量
        last_active_at (int): 最后活跃时间
        online_count (int): 当前在线人数
    """

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


class RoomListResponse(BaseModel):
    """房间列表响应

    Attributes:
        rooms (List[RoomResponse]): 房间列表
        total (int): 总数
    """

    rooms: List[RoomResponse]
    total: int


class InviteLinkResponse(BaseModel):
    """邀请链接响应

    Attributes:
        room_id (str): 房间 ID
        invite_url (str): 邀请 URL
    """

    room_id: str
    invite_url: str


# ==================== API 路由 ====================


@router.get("", response_model=RoomListResponse)
async def list_rooms(
    is_public: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """获取房间列表

    Args:
        is_public: 筛选公开/私有房间
        limit: 返回数量限制
        offset: 偏移量
        session: 数据库会话
        current_user: 当前用户 (可选)

    Returns:
        RoomListResponse: 房间列表响应
    """
    # 未登录用户只能看公开房间
    if current_user is None:
        is_public = True

    rooms = crud.get_rooms(session, is_public=is_public, limit=limit, offset=offset)

    room_responses = []
    for room in rooms:
        members = crud.get_room_members(session, room.id)

        # 获取在线人数 (WebSocket 路径格式: /ws/{room_id})
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
            )
        )

    return RoomListResponse(rooms=room_responses, total=len(room_responses))


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    request: RoomCreate,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """创建新房间

    Args:
        request: 创建房间请求
        session: 数据库会话
        current_user: 当前用户 (可选)

    Returns:
        RoomResponse: 创建的房间信息
    """
    room_id = str(uuid.uuid4())

    # 密码哈希
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
    logger.info("创建房间: %s (%s)", room.name, room.id)

    # 如果有用户，自动加入房间
    if current_user:
        member = RoomMember(room_id=room.id, user_id=current_user.id, role="owner")
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
    )


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(room_id: str, session: Session = Depends(get_session)):
    """获取房间详情

    Args:
        room_id: 房间 ID
        session: 数据库会话

    Returns:
        RoomResponse: 房间详情

    Raises:
        HTTPException: 房间不存在时抛出 404
    """
    room = crud.get_room(session, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="房间不存在")

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
    )


@router.post("/{room_id}/join")
async def join_room(
    room_id: str,
    request: RoomJoin,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """加入房间

    Args:
        room_id: 房间 ID
        request: 加入房间请求
        session: 数据库会话
        current_user: 当前用户

    Returns:
        dict: 加入结果

    Raises:
        HTTPException: 房间不存在、密码错误、已满员等
    """
    room = crud.get_room(session, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="房间不存在")

    # 检查权限: 管理员密钥
    is_admin_login = config.admin_key and request.password == config.admin_key

    # 检查是否已是成员
    existing_member = crud.get_room_member(session, room_id, current_user.id)
    if existing_member:
        # 如果用管理员密钥加入，升级为 owner
        if is_admin_login and existing_member.role != "owner":
            existing_member.role = "owner"
            session.add(existing_member)
            session.commit()
            logger.info(
                "用户 %s 使用管理员密钥升级为房间 %s 的 Owner",
                current_user.username,
                room_id,
            )
            return {"status": "upgraded_to_owner", "room_id": room_id}
        return {"status": "already_member", "room_id": room_id}

    # 设置角色
    role = "owner" if is_admin_login else "editor"
    if is_admin_login:
        logger.info(
            "用户 %s 使用管理员密钥加入房间 %s (Owner)", current_user.username, room_id
        )

    # 验证密码 (如果不是管理员登录)
    if not is_admin_login and room.password_hash:
        if not request.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="需要房间密码"
            )
        if not verify_password(request.password, room.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="密码错误"
            )

    # 检查人数限制 (管理员可忽略?)
    members = crud.get_room_members(session, room_id)
    if not is_admin_login and len(members) >= room.max_users:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="房间已满员")

    # 加入房间
    member = RoomMember(room_id=room_id, user_id=current_user.id, role=role)
    crud.add_room_member(session, member)
    logger.info("用户 %s 加入房间 %s", current_user.username, room_id)

    return {"status": "joined", "room_id": room_id}


class RoomDelete(BaseModel):
    """删除房间请求"""

    password: Optional[str] = Field(default=None)


@router.delete("/{room_id}")
async def delete_room(
    room_id: str,
    request: Optional[RoomDelete] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """删除房间

    只有登录用户才能删除房间。如果房间有密码，需要提供密码。

    Args:
        room_id: 房间 ID
        request: 删除请求 (包含密码)
        session: 数据库会话
        current_user: 当前用户 (必须登录)

    Returns:
        dict: 删除结果

    Raises:
        HTTPException: 房间不存在或密码错误
    """
    room = crud.get_room(session, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="房间不存在")

    # 如果房间有密码，需要验证
    if room.password_hash:
        password = request.password if request else None
        if not password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="此房间需要密码才能删除",
            )
        if not verify_password(password, room.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="密码错误"
            )

    crud.delete_room(session, room_id)
    logger.info("删除房间: %s (操作者: %s)", room_id, current_user.username)

    return {"status": "deleted", "room_id": room_id}


@router.post("/{room_id}/leave")
async def leave_room(
    room_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """离开房间

    Args:
        room_id: 房间 ID
        session: 数据库会话
        current_user: 当前用户

    Returns:
        dict: 离开结果
    """
    room = crud.get_room(session, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="房间不存在")

    # 房主不能离开
    if room.owner_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="房主不能离开房间，请删除房间"
        )

    removed = crud.remove_room_member(session, room_id, current_user.id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="您不是此房间成员"
        )

    logger.info("用户 %s 离开房间 %s", current_user.username, room_id)
    return {"status": "left", "room_id": room_id}


@router.get("/{room_id}/invite", response_model=InviteLinkResponse)
async def get_invite_link(room_id: str, session: Session = Depends(get_session)):
    """获取房间邀请链接

    Args:
        room_id: 房间 ID
        session: 数据库会话

    Returns:
        InviteLinkResponse: 邀请链接信息
    """
    room = crud.get_room(session, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="房间不存在")

    # 生成邀请 URL (前端处理)
    invite_url = f"/join/{room_id}"

    return InviteLinkResponse(room_id=room_id, invite_url=invite_url)


@router.get("/my/rooms", response_model=RoomListResponse)
async def get_my_rooms(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户加入的所有房间

    Args:
        session: 数据库会话
        current_user: 当前用户

    Returns:
        RoomListResponse: 房间列表响应
    """
    rooms = crud.get_user_rooms(session, current_user.id)

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
            )
        )

    return RoomListResponse(rooms=room_responses, total=len(room_responses))
