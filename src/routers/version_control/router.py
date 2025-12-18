from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session
from src.db.models import Commit
from src.db.database import get_session
from src.auth.utils import get_current_user_optional
from src.db.user import User
from src.logger import get_logger
from src.services.version_control import IGitService
from src.ws.sync import websocket_server

from .models import (
    HistoryResponse,
    CreateCommitRequest,
    CommitDetailResponse,
    CommitDiffResponse,
)


router = APIRouter(tags=["iGit"])
logger = get_logger(__name__)

@router.get("/{room_id}/history", response_model=HistoryResponse)
async def get_room_history(
    room_id: str, limit: int = 50, session: Session = Depends(get_session)
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
    service = IGitService(session)
    try:
        return service.get_history(room_id, limit)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/{room_id}/commit")
async def create_commit(
    room_id: str,
    request: CreateCommitRequest,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
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
    service = IGitService(session)

    # 确定作者信息
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
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/{room_id}/checkout/{commit_id}")
async def checkout_commit(
    room_id: str,
    commit_id: int,
    session: Session = Depends(get_session),
    _current_user: Optional[User] = Depends(get_current_user_optional),
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
    service = IGitService(session)
    try:
        commit = await service.checkout_commit(
            room_id=room_id, commit_id=commit_id, websocket_server=websocket_server
        )

        return {
            "status": "checked_out",
            "commit_id": commit.id,
            "commit_hash": commit.hash,
            "message": f"已检出到提交 {commit.hash}",
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/{room_id}/revert/{commit_id}")
async def revert_commit(
    room_id: str,
    commit_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
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
    service = IGitService(session)

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
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/{room_id}/commits", response_model=HistoryResponse)
async def get_commits(
    room_id: str, limit: int = 50, session: Session = Depends(get_session)
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

@router.get("/{room_id}/commits/{commit_id}", response_model=CommitDetailResponse)
async def get_commit_detail(
    room_id: str, commit_id: int, session: Session = Depends(get_session)
):
    """获取单个提交的详情

    Args:
        room_id: 房间 ID
        commit_id: 提交 ID
        session: 数据库会话

    Returns:
        CommitDetailResponse: 提交详情
    """
    service = IGitService(session)
    try:
        return service.get_commit_detail(room_id, commit_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/{room_id}/commits/{commit_id}/data")
async def get_commit_data(
    room_id: str, commit_id: int, session: Session = Depends(get_session)
):
    """获取提交的原始数据 (用于预览)

    Args:
        room_id: 房间 ID
        commit_id: 提交 ID
        session: 数据库会话

    Returns:
        bytes: Yjs 更新数据
    """

    commit = session.get(Commit, commit_id)
    if not commit or commit.room_id != room_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交不存在")

    return Response(content=commit.data, media_type="application/octet-stream")


@router.get("/{room_id}/diff/{commit_id}", response_model=CommitDiffResponse)
async def get_commit_diff(
    room_id: str,
    commit_id: int,
    base_commit_id: Optional[int] = None,
    session: Session = Depends(get_session),
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
    service = IGitService(session)
    try:
        return service.get_commit_diff(room_id, commit_id, base_commit_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
