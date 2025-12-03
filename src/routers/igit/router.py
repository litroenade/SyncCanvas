"""模块名称: router
主要功能: iGit 版本控制系统的 API 路由
"""

import time
from typing import Optional

from pycrdt import Doc
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, delete
from sqlalchemy import desc

from src.db.database import get_session
from src.db.models import Update, Commit
from src.db import crud
from src.auth.utils import get_current_user_optional
from src.models.user import User
from src.logger import get_logger

from .models import (
    CommitInfo,
    HistoryResponse,
    CreateCommitRequest,
    CommitDetailResponse,
    CommitDiffResponse,
)
from .utils import generate_commit_hash, parse_yjs_strokes, compute_strokes_diff


router = APIRouter(tags=["iGit"])
logger = get_logger(__name__)


# ==================== 版本历史 API ====================

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
        .order_by(desc(Commit.timestamp))
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

    # 构建完整文档状态
    ydoc = Doc()

    # 从最新 Commit 和 Update 中恢复状态
    commit_stmt = (
        select(Commit)
        .where(Commit.room_id == room_id)
        .order_by(desc(Commit.timestamp))
        .limit(1)
    )
    latest_commit = session.exec(commit_stmt).first()

    if latest_commit:
        ydoc.apply_update(latest_commit.data)

    # 获取增量更新
    if latest_commit:
        updates_stmt = (
            select(Update)
            .where(Update.room_id == room_id)
            .where(Update.timestamp > latest_commit.timestamp)
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

    # 检查是否有新的更改
    if not updates and latest_commit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有新的更改可提交"
        )

    # 确定作者信息
    # 优先使用请求中的 author_name，其次用用户名，最后用 "Anonymous"
    author_id = current_user.id if current_user else None
    if request.author_name:
        author_name = request.author_name
    elif current_user:
        author_name = current_user.username
    else:
        author_name = "Anonymous"

    logger.debug("创建提交 - 用户: %s, author_name: %s", current_user, author_name)

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
    # 注意：不再删除所有 Update，而是保留最新状态
    # 这样 Yjs 客户端可以继续正常工作
    delete_stmt = delete(Update).where(Update.room_id == room_id)
    session.exec(delete_stmt)

    # 将完整文档状态写回 Update 表，保持 Yjs 客户端同步
    # 这是关键：确保客户端刷新后能读取到正确的数据
    restore_update = Update(
        room_id=room_id,
        data=doc_data,
        timestamp=current_time + 1  # 确保时间戳在 commit 之后
    )
    session.add(restore_update)

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
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """检出指定提交

    类似 Git checkout，将房间状态恢复到指定提交。
    注意：这会清空当前未提交的更改！

    Args:
        room_id: 房间 ID
        commit_id: 提交 ID
        session: 数据库会话
        current_user: 当前用户（可选）

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

    # 清理所有 Update (未提交的更改会丢失)
    delete_update_stmt = delete(Update).where(Update.room_id == room_id)
    session.exec(delete_update_stmt)

    # 将 Commit 数据写入 Update 表，让 YStore 能够读取
    new_update = Update(
        room_id=room_id,
        data=commit.data,
        timestamp=int(time.time() * 1000)
    )
    session.add(new_update)

    # 更新 HEAD
    room.head_commit_id = commit_id
    session.add(room)

    session.commit()

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
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """回滚到指定提交并创建新提交

    类似 Git revert，创建一个新提交来撤销更改。

    Args:
        room_id: 房间 ID
        commit_id: 要回滚到的提交 ID
        session: 数据库会话
        current_user: 当前用户（可选）

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
    author_id = current_user.id if current_user else None
    author_name = current_user.username if current_user else "Anonymous"

    new_revert_commit = Commit(
        room_id=room_id,
        parent_id=room.head_commit_id,
        author_id=author_id,
        author_name=author_name,
        message=f"Revert to {commit.hash}: {commit.message}",
        data=commit.data,
        timestamp=current_time,
    )
    session.add(new_revert_commit)
    session.flush()

    new_revert_commit.hash = generate_commit_hash(new_revert_commit.id, current_time)

    # 清理 Update 表
    delete_update_stmt = delete(Update).where(Update.room_id == room_id)
    session.exec(delete_update_stmt)

    # 将回滚后的状态写入 Update 表，保持 Yjs 客户端同步
    restore_update = Update(
        room_id=room_id,
        data=commit.data,
        timestamp=current_time + 1
    )
    session.add(restore_update)

    # 更新 HEAD
    room.head_commit_id = new_revert_commit.id
    session.add(room)

    session.commit()

    logger.info("回滚提交: 房间 %s, 回滚到 %s", room_id, commit.hash)

    return {
        "status": "reverted",
        "new_commit": {
            "id": new_revert_commit.id,
            "hash": new_revert_commit.hash,
            "message": new_revert_commit.message
        },
        "reverted_to": {
            "id": commit.id,
            "hash": commit.hash
        }
    }


@router.get("/{room_id}/commits", response_model=HistoryResponse)
async def get_commits(
    room_id: str,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """获取房间提交历史 (别名 API)

    Args:
        room_id: 房间 ID
        limit: 返回的提交数量限制
        session: 数据库会话

    Returns:
        HistoryResponse: 历史信息
    """
    return await get_room_history(room_id, limit, session)


# ==================== Diff 和详情 API ====================

@router.get("/{room_id}/commits/{commit_id}", response_model=CommitDetailResponse)
async def get_commit_detail(
    room_id: str,
    commit_id: int,
    session: Session = Depends(get_session)
):
    """获取单个提交的详情

    Args:
        room_id: 房间 ID
        commit_id: 提交 ID
        session: 数据库会话

    Returns:
        CommitDetailResponse: 提交详情
    """
    room = crud.get_room(session, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )

    commit = session.get(Commit, commit_id)
    if not commit or commit.room_id != room_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提交不存在"
        )

    # 解析笔画数据
    strokes = parse_yjs_strokes(commit.data)

    # 统计笔画类型
    stroke_types = {}
    for stroke in strokes.values():
        if isinstance(stroke, dict):
            stroke_type = stroke.get("type", "unknown")
            stroke_types[stroke_type] = stroke_types.get(stroke_type, 0) + 1

    commit_info = CommitInfo(
        id=commit.id,
        hash=commit.hash or generate_commit_hash(commit.id, commit.timestamp),
        parent_id=commit.parent_id,
        author_id=commit.author_id,
        author_name=commit.author_name,
        message=commit.message,
        timestamp=commit.timestamp,
        size=len(commit.data) if commit.data else 0
    )

    return CommitDetailResponse(
        commit=commit_info,
        strokes_count=len(strokes),
        stroke_types=stroke_types
    )


@router.get("/{room_id}/diff/{commit_id}", response_model=CommitDiffResponse)
async def get_commit_diff(
    room_id: str,
    commit_id: int,
    base_commit_id: Optional[int] = None,
    session: Session = Depends(get_session)
):
    """获取提交的差异

    比较指定提交与其父提交(或指定的基准提交)之间的差异。

    Args:
        room_id: 房间 ID
        commit_id: 目标提交 ID
        base_commit_id: 基准提交 ID (可选，默认为父提交)
        session: 数据库会话

    Returns:
        CommitDiffResponse: 差异信息
    """
    room = crud.get_room(session, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )

    # 获取目标提交
    to_commit = session.get(Commit, commit_id)
    if not to_commit or to_commit.room_id != room_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提交不存在"
        )

    # 获取基准提交
    from_commit = None
    from_commit_info = None

    if base_commit_id is not None:
        from_commit = session.get(Commit, base_commit_id)
        if not from_commit or from_commit.room_id != room_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="基准提交不存在"
            )
    elif to_commit.parent_id:
        from_commit = session.get(Commit, to_commit.parent_id)

    # 解析笔画数据
    old_strokes = parse_yjs_strokes(from_commit.data) if from_commit else {}
    new_strokes = parse_yjs_strokes(to_commit.data)

    # 计算差异
    added, removed, modified, changes = compute_strokes_diff(old_strokes, new_strokes)

    # 构建响应
    if from_commit:
        from_commit_info = CommitInfo(
            id=from_commit.id,
            hash=from_commit.hash or generate_commit_hash(from_commit.id, from_commit.timestamp),
            parent_id=from_commit.parent_id,
            author_id=from_commit.author_id,
            author_name=from_commit.author_name,
            message=from_commit.message,
            timestamp=from_commit.timestamp,
            size=len(from_commit.data) if from_commit.data else 0
        )

    to_commit_info = CommitInfo(
        id=to_commit.id,
        hash=to_commit.hash or generate_commit_hash(to_commit.id, to_commit.timestamp),
        parent_id=to_commit.parent_id,
        author_id=to_commit.author_id,
        author_name=to_commit.author_name,
        message=to_commit.message,
        timestamp=to_commit.timestamp,
        size=len(to_commit.data) if to_commit.data else 0
    )

    from_size = len(from_commit.data) if from_commit and from_commit.data else 0
    to_size = len(to_commit.data) if to_commit.data else 0

    return CommitDiffResponse(
        room_id=room_id,
        from_commit=from_commit_info,
        to_commit=to_commit_info,
        strokes_added=added,
        strokes_removed=removed,
        strokes_modified=modified,
        changes=changes,
        size_diff=to_size - from_size
    )
