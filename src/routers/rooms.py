"""模块名称: rooms
主要功能: 房间管理 REST API 路由
"""

import uuid
import hashlib
import secrets
import time
from datetime import datetime
from typing import Optional, List

from pycrdt import Doc
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select, delete

from src.db.database import get_session
from src.db.models import Room, RoomMember, Snapshot, Update, Commit
from src.db import crud
from src.auth.utils import get_current_user_optional, get_current_user
from src.models.user import User
from src.logger import get_logger
from src.ws.sync import websocket_server

router = APIRouter(prefix="/rooms", tags=["Rooms"])
logger = get_logger(__name__)


def hash_password(password: str) -> str:
    """使用 SHA-256 + salt 哈希密码"""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    try:
        salt, stored_hash = password_hash.split('$')
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
    """
    id: str
    name: str
    owner_id: Optional[int]
    is_public: bool
    max_users: int
    created_at: int
    has_password: bool
    member_count: int = 0


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
    current_user: Optional[User] = Depends(get_current_user_optional)
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
        room_responses.append(RoomResponse(
            id=room.id,
            name=room.name,
            owner_id=room.owner_id,
            is_public=room.is_public,
            max_users=room.max_users,
            created_at=room.created_at,
            has_password=room.password_hash is not None,
            member_count=len(members)
        ))

    return RoomListResponse(rooms=room_responses, total=len(room_responses))


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    request: RoomCreate,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
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
        max_users=request.max_users
    )

    room = crud.create_room(session, room)
    logger.info("创建房间: %s (%s)", room.name, room.id)

    # 如果有用户，自动加入房间
    if current_user:
        member = RoomMember(
            room_id=room.id,
            user_id=current_user.id,
            role="owner"
        )
        crud.add_room_member(session, member)

    return RoomResponse(
        id=room.id,
        name=room.name,
        owner_id=room.owner_id,
        is_public=room.is_public,
        max_users=room.max_users,
        created_at=room.created_at,
        has_password=room.password_hash is not None,
        member_count=1 if current_user else 0
    )


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: str,
    session: Session = Depends(get_session)
):
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )

    members = crud.get_room_members(session, room.id)

    return RoomResponse(
        id=room.id,
        name=room.name,
        owner_id=room.owner_id,
        is_public=room.is_public,
        max_users=room.max_users,
        created_at=room.created_at,
        has_password=room.password_hash is not None,
        member_count=len(members)
    )


@router.post("/{room_id}/join")
async def join_room(
    room_id: str,
    request: RoomJoin,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )

    # 检查是否已是成员
    if crud.is_room_member(session, room_id, current_user.id):
        return {"status": "already_member", "room_id": room_id}

    # 验证密码
    if room.password_hash:
        if not request.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="需要房间密码"
            )
        if not verify_password(request.password, room.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="密码错误"
            )

    # 检查人数限制
    members = crud.get_room_members(session, room_id)
    if len(members) >= room.max_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="房间已满员"
        )

    # 加入房间
    member = RoomMember(
        room_id=room_id,
        user_id=current_user.id,
        role="editor"
    )
    crud.add_room_member(session, member)
    logger.info("用户 %s 加入房间 %s", current_user.username, room_id)

    return {"status": "joined", "room_id": room_id}


@router.delete("/{room_id}")
async def delete_room(
    room_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """删除房间

    Args:
        room_id: 房间 ID
        session: 数据库会话
        current_user: 当前用户

    Returns:
        dict: 删除结果

    Raises:
        HTTPException: 房间不存在或无权限
    """
    room = crud.get_room(session, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )

    # 检查权限
    if room.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除此房间"
        )

    crud.delete_room(session, room_id)
    logger.info("删除房间: %s", room_id)

    return {"status": "deleted", "room_id": room_id}


@router.post("/{room_id}/leave")
async def leave_room(
    room_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )

    # 房主不能离开
    if room.owner_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="房主不能离开房间，请删除房间"
        )

    removed = crud.remove_room_member(session, room_id, current_user.id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="您不是此房间成员"
        )

    logger.info("用户 %s 离开房间 %s", current_user.username, room_id)
    return {"status": "left", "room_id": room_id}


@router.get("/{room_id}/invite", response_model=InviteLinkResponse)
async def get_invite_link(
    room_id: str,
    session: Session = Depends(get_session)
):
    """获取房间邀请链接

    Args:
        room_id: 房间 ID
        session: 数据库会话

    Returns:
        InviteLinkResponse: 邀请链接信息
    """
    room = crud.get_room(session, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )

    # 生成邀请 URL (前端处理)
    invite_url = f"/join/{room_id}"

    return InviteLinkResponse(room_id=room_id, invite_url=invite_url)


@router.get("/my/rooms", response_model=RoomListResponse)
async def get_my_rooms(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
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
        room_responses.append(RoomResponse(
            id=room.id,
            name=room.name,
            owner_id=room.owner_id,
            is_public=room.is_public,
            max_users=room.max_users,
            created_at=room.created_at,
            has_password=room.password_hash is not None,
            member_count=len(members)
        ))

    return RoomListResponse(rooms=room_responses, total=len(room_responses))


# ==================== 版本历史 API ====================

def generate_commit_hash(commit_id: int, timestamp: int) -> str:
    """生成提交哈希
    
    Args:
        commit_id: 提交 ID
        timestamp: 时间戳
        
    Returns:
        7 位短哈希
    """
    data = f"{commit_id}-{timestamp}"
    full_hash = hashlib.sha1(data.encode()).hexdigest()
    return full_hash[:7]


class CommitInfo(BaseModel):
    """提交信息

    Attributes:
        id (int): 提交 ID
        hash (str): 提交哈希 (7位)
        parent_id (int): 父提交 ID
        author_id (int): 作者 ID
        author_name (str): 作者名称
        message (str): 提交消息
        timestamp (int): 时间戳 (毫秒)
        size (int): 数据大小 (字节)
    """
    id: int
    hash: str
    parent_id: Optional[int]
    author_id: Optional[int]
    author_name: str
    message: str
    timestamp: int
    size: int


class HistoryResponse(BaseModel):
    """历史响应

    Attributes:
        room_id (str): 房间 ID
        head_commit_id (int): 当前 HEAD 指向的提交 ID
        commits (List[CommitInfo]): 提交列表 (从新到旧)
        pending_changes (int): 待提交的更改数量
        total_size (int): 总数据大小
    """
    room_id: str
    head_commit_id: Optional[int]
    commits: List[CommitInfo]
    pending_changes: int
    total_size: int


class CreateCommitRequest(BaseModel):
    """创建提交请求

    Attributes:
        message (str): 提交消息
        author_name (str): 作者名称 (可选，默认使用登录用户名)
    """
    message: str = Field(default="手动保存", max_length=500)
    author_name: Optional[str] = Field(default=None, max_length=100)


class SnapshotInfo(BaseModel):
    """快照信息 (兼容旧 API)

    Attributes:
        id (int): 快照 ID
        timestamp (int): 时间戳 (毫秒)
        size (int): 数据大小 (字节)
    """
    id: int
    timestamp: int
    size: int


@router.get("/{room_id}/history", response_model=HistoryResponse)
async def get_room_history(
    room_id: str,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """获取房间版本历史

    类似 Git log，返回房间的提交列表。

    Args:
        room_id: 房间 ID
        limit: 返回的提交数量限制
        session: 数据库会话

    Returns:
        HistoryResponse: 历史信息
    """
    room = crud.get_room(session, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )

    # 获取所有提交
    commits_stmt = (
        select(Commit)
        .where(Commit.room_id == room_id)
        .order_by(Commit.timestamp.desc())
        .limit(limit)
    )
    commits = session.exec(commits_stmt).all()

    commit_infos = [
        CommitInfo(
            id=c.id,
            hash=c.hash or generate_commit_hash(c.id, c.timestamp),
            parent_id=c.parent_id,
            author_id=c.author_id,
            author_name=c.author_name,
            message=c.message,
            timestamp=c.timestamp,
            size=len(c.data) if c.data else 0
        )
        for c in commits
    ]

    # 获取待提交的更改数量 (Update 表中的记录数)
    updates_stmt = select(Update).where(Update.room_id == room_id)
    updates = session.exec(updates_stmt).all()
    pending_changes = len(updates)

    # 计算总大小
    total_size = sum(c.size for c in commit_infos)
    total_size += sum(len(u.data) if u.data else 0 for u in updates)

    return HistoryResponse(
        room_id=room_id,
        head_commit_id=room.head_commit_id,
        commits=commit_infos,
        pending_changes=pending_changes,
        total_size=total_size
    )


@router.post("/{room_id}/commit")
async def create_commit(
    room_id: str,
    request: CreateCommitRequest,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """创建新提交

    类似 Git commit，将当前状态保存为一个新提交。

    Args:
        room_id: 房间 ID
        request: 提交请求
        session: 数据库会话
        current_user: 当前用户 (可选)

    Returns:
        dict: 创建的提交信息
    """
    room = crud.get_room(session, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )



    ws_path = f"/ws/{room_id}"

    # 构建完整文档状态
    ydoc = Doc()

    # 从 Snapshot 和 Update 中恢复状态
    snapshot_stmt = (
        select(Snapshot)
        .where(Snapshot.room_id == room_id)
        .order_by(Snapshot.timestamp.desc())
        .limit(1)
    )
    snapshot = session.exec(snapshot_stmt).first()

    if snapshot:
        ydoc.apply_update(snapshot.data)

    # 获取增量更新
    if snapshot:
        updates_stmt = (
            select(Update)
            .where(Update.room_id == room_id)
            .where(Update.timestamp > snapshot.timestamp)
            .order_by(Update.timestamp)
        )
    else:
        updates_stmt = (
            select(Update)
            .where(Update.room_id == room_id)
            .order_by(Update.timestamp)
        )

    updates = session.exec(updates_stmt).all()
    for update in updates:
        ydoc.apply_update(update.data)

    # 如果没有数据，返回错误
    doc_data = ydoc.get_update()
    if not doc_data or len(doc_data) <= 2:  # 空 Yjs 文档大约 2 字节
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有数据可提交"
        )

    # 确定作者信息
    author_id = current_user.id if current_user else None
    author_name = request.author_name or (current_user.username if current_user else "Anonymous")

    # 创建提交
    current_time = int(time.time() * 1000)
    commit = Commit(
        room_id=room_id,
        parent_id=room.head_commit_id,
        author_id=author_id,
        author_name=author_name,
        message=request.message,
        data=doc_data,
        timestamp=current_time,
    )
    session.add(commit)
    session.flush()  # 获取 commit.id

    # 生成哈希
    commit.hash = generate_commit_hash(commit.id, current_time)

    # 更新房间的 HEAD
    room.head_commit_id = commit.id
    session.add(room)

    # 清理 Update 表 (已经合并到 Commit 中了)
    delete_stmt = delete(Update).where(Update.room_id == room_id)
    session.exec(delete_stmt)

    # 更新 Snapshot (保持 YStore 的状态)
    # 删除旧快照，创建新快照
    delete_snapshot_stmt = delete(Snapshot).where(Snapshot.room_id == room_id)
    session.exec(delete_snapshot_stmt)

    new_snapshot = Snapshot(
        room_id=room_id,
        data=doc_data,
        timestamp=current_time
    )
    session.add(new_snapshot)

    session.commit()

    logger.info("创建提交: 房间 %s, 哈希 %s, 消息: %s", room_id, commit.hash, request.message)

    return {
        "status": "created",
        "commit": {
            "id": commit.id,
            "hash": commit.hash,
            "message": commit.message,
            "author_name": author_name,
            "timestamp": current_time
        }
    }


@router.post("/{room_id}/checkout/{commit_id}")
async def checkout_commit(
    room_id: str,
    commit_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """检出指定提交

    类似 Git checkout，将房间状态恢复到指定提交。

    Args:
        room_id: 房间 ID
        commit_id: 提交 ID
        session: 数据库会话
        current_user: 当前用户

    Returns:
        dict: 检出结果
    """
    room = crud.get_room(session, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )

    # 获取指定提交
    commit = session.get(Commit, commit_id)
    if not commit or commit.room_id != room_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提交不存在"
        )

    # 更新 Snapshot 为该提交的状态
    delete_snapshot_stmt = delete(Snapshot).where(Snapshot.room_id == room_id)
    session.exec(delete_snapshot_stmt)

    delete_update_stmt = delete(Update).where(Update.room_id == room_id)
    session.exec(delete_update_stmt)

    new_snapshot = Snapshot(
        room_id=room_id,
        data=commit.data,
        timestamp=int(time.time() * 1000)
    )
    session.add(new_snapshot)

    # 更新 HEAD
    room.head_commit_id = commit_id
    session.add(room)

    session.commit()

    # 通知 WebSocket 客户端重新加载
    # TODO: 实现 WebSocket 通知机制

    logger.info("检出提交: 房间 %s, 提交 %s (%s)", room_id, commit_id, commit.hash)

    return {
        "status": "checked_out",
        "commit_id": commit_id,
        "commit_hash": commit.hash,
        "message": f"已检出到提交 {commit.hash}"
    }


@router.post("/{room_id}/revert/{commit_id}")
async def revert_commit(
    room_id: str,
    commit_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """回滚到指定提交并创建新提交

    类似 Git revert，创建一个新提交来撤销更改。

    Args:
        room_id: 房间 ID
        commit_id: 要回滚到的提交 ID
        session: 数据库会话
        current_user: 当前用户

    Returns:
        dict: 回滚结果
    """
    room = crud.get_room(session, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )

    # 获取指定提交
    commit = session.get(Commit, commit_id)
    if not commit or commit.room_id != room_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提交不存在"
        )

    # 创建回滚提交
    current_time = int(time.time() * 1000)
    revert_commit = Commit(
        room_id=room_id,
        parent_id=room.head_commit_id,
        author_id=current_user.id,
        author_name=current_user.username,
        message=f"Revert to {commit.hash}: {commit.message}",
        data=commit.data,
        timestamp=current_time,
    )
    session.add(revert_commit)
    session.flush()

    revert_commit.hash = generate_commit_hash(revert_commit.id, current_time)

    # 更新 Snapshot
    delete_snapshot_stmt = delete(Snapshot).where(Snapshot.room_id == room_id)
    session.exec(delete_snapshot_stmt)

    delete_update_stmt = delete(Update).where(Update.room_id == room_id)
    session.exec(delete_update_stmt)

    new_snapshot = Snapshot(
        room_id=room_id,
        data=commit.data,
        timestamp=current_time
    )
    session.add(new_snapshot)

    # 更新 HEAD
    room.head_commit_id = revert_commit.id
    session.add(room)

    session.commit()

    logger.info("回滚提交: 房间 %s, 从 %s 回滚到 %s", room_id, room.head_commit_id, commit.hash)

    return {
        "status": "reverted",
        "new_commit": {
            "id": revert_commit.id,
            "hash": revert_commit.hash,
            "message": revert_commit.message
        },
        "reverted_to": {
            "id": commit.id,
            "hash": commit.hash
        }
    }


# ==================== 兼容旧 API ====================

@router.get("/{room_id}/snapshots", response_model=List[SnapshotInfo])
async def get_room_snapshots(
    room_id: str,
    session: Session = Depends(get_session)
):
    """获取房间快照列表 (兼容旧 API)

    Args:
        room_id: 房间 ID
        session: 数据库会话

    Returns:
        List[SnapshotInfo]: 快照列表
    """
    room = crud.get_room(session, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )

    snapshots_stmt = (
        select(Snapshot)
        .where(Snapshot.room_id == room_id)
        .order_by(Snapshot.timestamp.desc())
    )
    snapshots = session.exec(snapshots_stmt).all()

    return [
        SnapshotInfo(
            id=s.id,
            timestamp=s.timestamp,
            size=len(s.data) if s.data else 0
        )
        for s in snapshots
    ]


@router.post("/{room_id}/snapshot")
async def create_room_snapshot(
    room_id: str,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """手动创建房间快照 (兼容旧 API，内部调用 commit)

    Args:
        room_id: 房间 ID
        session: 数据库会话
        current_user: 当前用户

    Returns:
        dict: 创建结果
    """
    # 调用新的 commit API
    request = CreateCommitRequest(message="Auto save")
    return await create_commit(room_id, request, session, current_user)
