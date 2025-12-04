"""模块名称: igit
主要功能: IGit 版本控制服务层
"""

import time
from typing import Optional, Tuple, Any

from sqlmodel import Session, delete
from pycrdt import Doc

from src.db.models import Update, Commit
from src.db import crud
from src.logger import get_logger
from src.routers.igit.models import (
    CommitInfo,
    HistoryResponse,
    CommitDetailResponse,
    CommitDiffResponse,
)
from src.routers.igit.utils import (
    generate_commit_hash,
    parse_yjs_strokes,
    compute_strokes_diff,
)

logger = get_logger(__name__)


class IGitService:
    """IGit 版本控制服务"""

    def __init__(self, session: Session):
        self.session = session

    async def create_commit(
        self,
        room_id: str,
        message: str,
        author_id: Optional[int] = None,
        author_name: str = "Anonymous",
        websocket_server: Any = None,
    ) -> Commit:
        """创建新提交

        Args:
            room_id: 房间 ID
            message: 提交消息
            author_id: 作者 ID
            author_name: 作者名称
            websocket_server: WebSocket 服务器实例 (用于刷新缓冲区)

        Returns:
            Commit: 创建的提交对象
        """
        # 1. 获取内存中的更新 (避免死锁，不调用 flush_room)
        mem_updates = []
        if websocket_server:
            # 尝试获取 YStore
            # 注意：这里假设 websocket_server 是 PersistentWebsocketServer 实例
            if hasattr(websocket_server, "get_ystore"):
                ystore = websocket_server.get_ystore(room_id)
                if ystore:
                    # 获取并清空缓冲区，这些数据将直接合并到 Commit 中，不需要写入 Update 表
                    mem_updates = ystore.get_buffer_data()

        # 2. 获取房间信息
        room = crud.get_room(self.session, room_id)
        if not room:
            raise ValueError("房间不存在")

        # 构建完整文档状态
        ydoc = Doc()

        # 从最新 Commit 恢复状态
        latest_commit = crud.get_latest_commit(self.session, room_id)
        if latest_commit:
            ydoc.apply_update(latest_commit.data)

        # 获取数据库中的增量更新
        if latest_commit:
            db_updates = crud.get_updates_since(
                self.session, room_id, latest_commit.timestamp
            )
        else:
            db_updates = crud.get_all_updates(self.session, room_id)

        # 应用数据库更新
        for update in db_updates:
            ydoc.apply_update(update.data)

        # 应用内存更新
        for data, _ in mem_updates:
            ydoc.apply_update(data)

        # 检查是否有数据可提交
        doc_data = ydoc.get_update()
        if not doc_data or len(doc_data) <= 2:
            if not db_updates and not mem_updates and not latest_commit:
                raise ValueError("没有数据可提交")

        # 检查是否有新的更改
        if not db_updates and not mem_updates and latest_commit:
            raise ValueError("没有新的更改可提交")

        # 创建提交
        current_time = int(time.time() * 1000)
        commit = Commit(
            room_id=room_id,
            parent_id=room.head_commit_id,
            author_id=author_id,
            author_name=author_name,
            message=message,
            data=doc_data,
            timestamp=current_time,
        )
        self.session.add(commit)
        self.session.flush()  # 获取 commit.id

        # 生成哈希
        commit.hash = generate_commit_hash(commit.id, current_time)

        # 更新房间的 HEAD
        room.head_commit_id = commit.id
        self.session.add(room)

        # 清理 Update 表 (已经合并到 Commit 中了)
        # 注意：只清理数据库中已有的 Update，内存中的 mem_updates 已经被清空且合并
        delete_stmt = delete(Update).where(Update.room_id == room_id)
        self.session.exec(delete_stmt)

        self.session.commit()
        self.session.refresh(commit)

        logger.info(f"创建提交: 房间 {room_id}, 哈希 {commit.hash}, 消息: {message}")
        return commit

    async def checkout_commit(
        self, room_id: str, commit_id: int, websocket_server: Any = None
    ) -> Commit:
        """检出指定提交

        Args:
            room_id: 房间 ID
            commit_id: 提交 ID
            websocket_server: WebSocket 服务器实例 (用于清理内存状态)

        Returns:
            Commit: 检出的提交对象
        """
        room = crud.get_room(self.session, room_id)
        if not room:
            raise ValueError("房间不存在")

        # 从内存中移除房间，丢弃未保存的更改
        if websocket_server:
            await websocket_server.evict_room(room_id, discard_changes=True)

        # 获取指定提交
        commit = self.session.get(Commit, commit_id)
        if not commit or commit.room_id != room_id:
            raise ValueError("提交不存在")

        # 清理所有 Update (未提交的更改会丢失)
        delete_update_stmt = delete(Update).where(Update.room_id == room_id)
        self.session.exec(delete_update_stmt)

        # 将 Commit 数据写入 Update 表，让 YStore 能够读取
        # 这是关键一步，YStore 初始化时会读取 Update 表
        new_update = Update(
            room_id=room_id, data=commit.data, timestamp=int(time.time() * 1000)
        )
        self.session.add(new_update)

        # 更新 HEAD
        room.head_commit_id = commit_id
        self.session.add(room)

        self.session.commit()
        self.session.refresh(commit)

        logger.info(f"检出提交: 房间 {room_id}, 提交 {commit_id} ({commit.hash})")
        return commit

    async def revert_commit(
        self,
        room_id: str,
        commit_id: int,
        author_id: int,
        author_name: str,
        websocket_server: Any = None,
    ) -> Tuple[Commit, Commit]:
        """回滚到指定提交

        Args:
            room_id: 房间 ID
            commit_id: 要回滚到的提交 ID
            author_id: 操作者 ID
            author_name: 操作者名称
            websocket_server: WebSocket 服务器实例

        Returns:
            (new_commit, reverted_to_commit): 新创建的提交和回滚到的目标提交
        """
        room = crud.get_room(self.session, room_id)
        if not room:
            raise ValueError("房间不存在")

        # 从内存中移除房间，丢弃未保存的更改
        if websocket_server:
            await websocket_server.evict_room(room_id, discard_changes=True)

        # 获取指定提交
        target_commit = self.session.get(Commit, commit_id)
        if not target_commit or target_commit.room_id != room_id:
            raise ValueError("提交不存在")

        # 创建回滚提交
        current_time = int(time.time() * 1000)
        new_commit = Commit(
            room_id=room_id,
            parent_id=room.head_commit_id,
            author_id=author_id,
            author_name=author_name,
            message=f"Revert to {target_commit.hash}: {target_commit.message}",
            data=target_commit.data,
            timestamp=current_time,
        )
        self.session.add(new_commit)
        self.session.flush()

        new_commit.hash = generate_commit_hash(new_commit.id, current_time)

        # 清理 Update 表
        delete_update_stmt = delete(Update).where(Update.room_id == room_id)
        self.session.exec(delete_update_stmt)

        # 写入新的 Update 确保 YStore 读取正确状态
        new_update = Update(
            room_id=room_id, data=target_commit.data, timestamp=current_time
        )
        self.session.add(new_update)

        # 更新 HEAD
        room.head_commit_id = new_commit.id
        self.session.add(room)

        self.session.commit()
        self.session.refresh(new_commit)

        logger.info(f"回滚提交: 房间 {room_id}, 回滚到 {target_commit.hash}")
        logger.info(f"回滚数据大小: {len(target_commit.data)} bytes")
        return new_commit, target_commit

    def get_history(
        self, room_id: str, limit: int = 50, websocket_server: Any = None
    ) -> HistoryResponse:
        """获取房间历史"""
        room = crud.get_room(self.session, room_id)
        if not room:
            raise ValueError("房间不存在")

        commits = crud.get_commits_by_room(self.session, room_id, limit)

        commit_infos = [
            CommitInfo(
                id=c.id,
                hash=c.hash or generate_commit_hash(c.id, c.timestamp),
                parent_id=c.parent_id,
                author_id=c.author_id,
                author_name=c.author_name,
                message=c.message,
                timestamp=c.timestamp,
                size=len(c.data) if c.data else 0,
            )
            for c in commits
        ]

        updates = crud.get_all_updates(self.session, room_id)
        pending_changes = len(updates)

        # 加上内存中的更新
        mem_updates_count = 0
        if websocket_server and hasattr(websocket_server, "get_ystore"):
            ystore = websocket_server.get_ystore(room_id)
            if ystore:
                mem_updates_count = ystore._buffer.size()

        pending_changes += mem_updates_count

        total_size = sum(c.size for c in commit_infos)
        total_size += sum(len(u.data) if u.data else 0 for u in updates)
        # 估算内存更新大小 (假设平均 100 字节，或者忽略大小统计的精确性)
        total_size += mem_updates_count * 100

        return HistoryResponse(
            room_id=room_id,
            head_commit_id=room.head_commit_id,
            commits=commit_infos,
            pending_changes=pending_changes,
            total_size=total_size,
        )

    def get_commit_detail(self, room_id: str, commit_id: int) -> CommitDetailResponse:
        """获取提交详情"""
        commit = crud.get_commit_by_id(self.session, commit_id)
        if not commit or commit.room_id != room_id:
            raise ValueError("提交不存在")

        strokes = parse_yjs_strokes(commit.data)

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
            size=len(commit.data) if commit.data else 0,
        )

        return CommitDetailResponse(
            commit=commit_info, strokes_count=len(strokes), stroke_types=stroke_types
        )

    def get_commit_diff(
        self, room_id: str, commit_id: int, base_commit_id: Optional[int] = None
    ) -> CommitDiffResponse:
        """获取提交差异"""
        to_commit = crud.get_commit_by_id(self.session, commit_id)
        if not to_commit or to_commit.room_id != room_id:
            raise ValueError("目标提交不存在")

        from_commit = None
        if base_commit_id is not None:
            from_commit = crud.get_commit_by_id(self.session, base_commit_id)
            if not from_commit or from_commit.room_id != room_id:
                raise ValueError("基准提交不存在")
        elif to_commit.parent_id:
            from_commit = crud.get_commit_by_id(self.session, to_commit.parent_id)

        old_strokes = parse_yjs_strokes(from_commit.data) if from_commit else {}
        new_strokes = parse_yjs_strokes(to_commit.data)

        added, removed, modified, changes = compute_strokes_diff(
            old_strokes, new_strokes
        )

        from_commit_info = None
        if from_commit:
            from_commit_info = CommitInfo(
                id=from_commit.id,
                hash=from_commit.hash
                or generate_commit_hash(from_commit.id, from_commit.timestamp),
                parent_id=from_commit.parent_id,
                author_id=from_commit.author_id,
                author_name=from_commit.author_name,
                message=from_commit.message,
                timestamp=from_commit.timestamp,
                size=len(from_commit.data) if from_commit.data else 0,
            )

        to_commit_info = CommitInfo(
            id=to_commit.id,
            hash=to_commit.hash
            or generate_commit_hash(to_commit.id, to_commit.timestamp),
            parent_id=to_commit.parent_id,
            author_id=to_commit.author_id,
            author_name=to_commit.author_name,
            message=to_commit.message,
            timestamp=to_commit.timestamp,
            size=len(to_commit.data) if to_commit.data else 0,
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
            size_diff=to_size - from_size,
        )
