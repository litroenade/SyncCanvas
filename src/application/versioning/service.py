"""Version-control application service."""

import time
from typing import Optional, Tuple, Any
from sqlmodel import Session, delete
from pycrdt import Doc
from src.domain.versioning.models import (
    CommitInfo,
    HistoryResponse,
    CommitDetailResponse,
    CommitDiffResponse,
)
from src.domain.versioning.utils import (
    compute_diagrams_diff,
    generate_commit_hash,
    compute_elements_diff,
    parse_yjs_diagrams,
    parse_yjs_elements,
    summarize_diagrams,
)
from src.infra.logging import get_logger
from src.persistence.db.engine import sqlite_write_transaction
from src.persistence.db.models.rooms import Commit, Update
from src.persistence.db.repositories import rooms as crud

logger = get_logger(__name__)


def _count_active_elements(data: bytes) -> int:
    elements = parse_yjs_elements(data)
    return sum(
        1
        for element in elements.values()
        if isinstance(element, dict) and not element.get("isDeleted")
    )


class IGitService:
    """IGit 鐗堟湰鎺у埗鏈嶅姟"""

    def __init__(self, session: Session):
        self.session = session

    def _get_contributor_ids(self, room_id: str) -> set:
        """鑾峰彇鎴块棿鐨勬墍鏈夎础鐚€?ID"""
        commits = crud.get_commits_by_room(self.session, room_id, limit=1000)
        return {c.author_id for c in commits if c.author_id is not None}

    async def create_commit(
        self,
        room_id: str,
        message: str,
        author_id: Optional[int] = None,
        author_name: str = "Anonymous",
        websocket_server: Any = None,
    ) -> Commit:
        """鍒涘缓鏂版彁浜?

        Args:
            room_id: 鎴块棿 ID
            message: 鎻愪氦娑堟伅
            author_id: 浣滆€?ID
            author_name: 浣滆€呭悕绉?
            websocket_server: WebSocket 鏈嶅姟鍣ㄥ疄渚?(鐢ㄤ簬鍒锋柊缂撳啿鍖?

        Returns:
            Commit: 鍒涘缓鐨勬彁浜ゅ璞?
        """
        if websocket_server and hasattr(websocket_server, "flush_room"):
            await websocket_server.flush_room(room_id)

        # 2. 鑾峰彇鎴块棿淇℃伅
        room = crud.get_room(self.session, room_id)
        if not room:
            raise ValueError("room_not_found")

        base_commit = None
        if room.head_commit_id:
            base_commit = self.session.get(Commit, room.head_commit_id)
        if not base_commit:
            base_commit = crud.get_latest_commit(self.session, room_id)

        contributor_ids = self._get_contributor_ids(room_id)

        try:
            # Build the full document state in memory before writing a commit.
            ydoc = Doc()

            # Restore the current room head first.
            if base_commit:
                ydoc.apply_update(base_commit.data)

            # Collect persisted incremental updates after the current head.
            if base_commit:
                db_updates = crud.get_updates_since(
                    self.session, room_id, base_commit.timestamp
                )
            else:
                db_updates = crud.get_all_updates(self.session, room_id)

            # Apply persisted database updates.
            for update in db_updates:
                ydoc.apply_update(update.data)

            # Compute the current Yjs payload that will be committed.
            doc_data = ydoc.get_update()
            if not doc_data or len(doc_data) <= 2:
                if not db_updates and not base_commit:
                    raise ValueError("no_data_to_commit")

            # 妫€鏌ユ槸鍚︽湁鏂扮殑鏇存敼
            if not db_updates and base_commit:
                raise ValueError("no_new_changes_to_commit")

            with sqlite_write_transaction():
                # 鍒涘缓鎻愪氦
                current_time = int(time.time() * 1000)
                commit = Commit(
                    room_id=room_id,
                    parent_id=base_commit.id if base_commit else None,
                    author_id=author_id,
                    author_name=author_name,
                    message=message,
                    data=doc_data,
                    timestamp=current_time,
                )
                self.session.add(commit)
                self.session.flush()  # 鑾峰彇 commit.id
                assert commit.id is not None

                # 鐢熸垚鍝堝笇
                commit.hash = generate_commit_hash(commit.id, current_time)

                # Update room metadata to point at the new head commit.
                room.head_commit_id = commit.id
                room.last_active_at = current_time

                # Recompute room element statistics from the committed document.
                room.elements_count = _count_active_elements(doc_data)

                # 鏇存柊璐＄尞鑰呮暟閲忥紙绠€鍖栭€昏緫锛氭瘡娆℃彁浜ゆ鏌ユ槸鍚︽槸鏂拌础鐚€咃級
                if author_id and author_id not in contributor_ids:
                    room.total_contributors = (room.total_contributors or 0) + 1

                self.session.add(room)

                # 娓呯悊 Update 琛?(宸茬粡鍚堝苟鍒?Commit 涓簡)
                # 娉ㄦ剰锛氬彧娓呯悊鏈鍚堝苟鍒?Commit 涓殑鏁版嵁锛岄伩鍏嶅垹鎺夊苟鍙戞柊鏇存敼
                for update in db_updates:
                    self.session.delete(update)

                self.session.commit()
                self.session.refresh(commit)

            logger.info(
                "鍒涘缓鎻愪氦: 鎴块棿 %s, 鍝堝笇 %s, 娑堟伅: %s", room_id, commit.hash, message
            )
            return commit
        except Exception as exc:
            self.session.rollback()
            logger.error("鍒涘缓鎻愪氦澶辫触: room=%s error=%s", room_id, str(exc))
            raise

    async def checkout_commit(
        self, room_id: str, commit_id: int, websocket_server: Any = None
    ) -> Commit:
        """妫€鍑烘寚瀹氭彁浜?

        Args:
            room_id: 鎴块棿 ID
            commit_id: 鎻愪氦 ID
            websocket_server: WebSocket 鏈嶅姟鍣ㄥ疄渚?(鐢ㄤ簬娓呯悊鍐呭瓨鐘舵€?

        Returns:
            Commit: 妫€鍑虹殑鎻愪氦瀵硅薄
        """
        room = crud.get_room(self.session, room_id)
        if not room:
            raise ValueError("room_not_found")

        # 鑾峰彇鎸囧畾鎻愪氦
        commit = self.session.get(Commit, commit_id)
        if not commit or commit.room_id != room_id:
            raise ValueError("commit_not_found")

        try:
            with sqlite_write_transaction():
                # 娓呯悊鎵€鏈?Update (鏈彁浜ょ殑鏇存敼浼氫涪澶?
                delete_update_stmt = delete(Update).where(Update.room_id == room_id)  # type: ignore[arg-type]
                self.session.exec(delete_update_stmt)

                # 鏇存柊 HEAD
                current_time = int(time.time() * 1000)
                room.head_commit_id = commit_id
                room.last_active_at = current_time
                room.elements_count = _count_active_elements(commit.data)
                self.session.add(room)

                # Commit before evicting websocket state so readers see durable data.
                self.session.commit()
                self.session.refresh(commit)

            logger.info(
                "妫€鍑烘彁浜? 鎴块棿 %s, 鎻愪氦 %d (%s)", room_id, commit_id, commit.hash
            )
        except Exception as exc:
            self.session.rollback()
            logger.error("妫€鍑烘彁浜ゅけ璐? room=%s error=%s", room_id, str(exc))
            raise

        # 閲嶈锛氬湪鏁版嵁搴撲簨鍔℃彁浜や箣鍚庡啀娓呯悊鍐呭瓨涓殑鎴块棿
        # 杩欐牱褰撳鎴风閲嶈繛鏃讹紝YStore 鑳借鍙栧埌鏈€鏂扮殑鏁版嵁
        if websocket_server:
            try:
                await websocket_server.evict_room(room_id, discard_changes=True)
            except Exception as err:  # pragma: no cover - best effort cache invalidation
                logger.warning("妫€鍑烘竻鐞嗗け璐?room=%s: %s", room_id, err)

        return commit

    async def revert_commit(
        self,
        room_id: str,
        commit_id: int,
        author_id: int,
        author_name: str,
        websocket_server: Any = None,
    ) -> Tuple[Commit, Commit]:
        """鍥炴粴鍒版寚瀹氭彁浜?

        Args:
            room_id: 鎴块棿 ID
            commit_id: 瑕佸洖婊氬埌鐨勬彁浜?ID
            author_id: 鎿嶄綔鑰?ID
            author_name: 鎿嶄綔鑰呭悕绉?
            websocket_server: WebSocket 鏈嶅姟鍣ㄥ疄渚?

        Returns:
            (new_commit, reverted_to_commit): 鏂板垱寤虹殑鎻愪氦鍜屽洖婊氬埌鐨勭洰鏍囨彁浜?
        """
        room = crud.get_room(self.session, room_id)
        if not room:
            raise ValueError("room_not_found")

        # 鑾峰彇鎸囧畾鎻愪氦
        target_commit = self.session.get(Commit, commit_id)
        if not target_commit or target_commit.room_id != room_id:
            raise ValueError("commit_not_found")

        contributor_ids = self._get_contributor_ids(room_id)

        try:
            with sqlite_write_transaction():
                # 鍒涘缓鍥炴粴鎻愪氦
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
                assert new_commit.id is not None

                new_commit.hash = generate_commit_hash(new_commit.id, current_time)

                # Clear Update rows because the revert commit supersedes them.
                delete_update_stmt = delete(Update).where(Update.room_id == room_id)  # type: ignore[arg-type]
                self.session.exec(delete_update_stmt)

                # 鏇存柊 HEAD
                room.head_commit_id = new_commit.id
                room.last_active_at = current_time
                room.elements_count = _count_active_elements(target_commit.data)
                if author_id and author_id not in contributor_ids:
                    room.total_contributors = (room.total_contributors or 0) + 1
                self.session.add(room)

                # Commit before evicting websocket state so readers see durable data.
                self.session.commit()
                self.session.refresh(new_commit)

            logger.info("鍥炴粴鎻愪氦: 鎴块棿 %s, 鍥炴粴鍒?%s", room_id, target_commit.hash)
            logger.info("鍥炴粴鏁版嵁澶у皬: %d bytes", len(target_commit.data))
        except Exception as exc:
            self.session.rollback()
            logger.error("鍥炴粴鎻愪氦澶辫触: room=%s error=%s", room_id, str(exc))
            raise

        # 閲嶈锛氬湪鏁版嵁搴撲簨鍔℃彁浜や箣鍚庡啀娓呯悊鍐呭瓨涓殑鎴块棿
        # 杩欐牱褰撳鎴风閲嶈繛鏃讹紝YStore 鑳借鍙栧埌鏈€鏂扮殑鍥炴粴鏁版嵁
        if websocket_server:
            try:
                await websocket_server.evict_room(room_id, discard_changes=True)
            except Exception as err:  # pragma: no cover - best effort cache invalidation
                logger.warning("鍥炴粴娓呯悊澶辫触 room=%s: %s", room_id, err)

        return new_commit, target_commit

    def get_history(
        self, room_id: str, limit: int = 50, websocket_server: Any = None
    ) -> HistoryResponse:
        """鑾峰彇鎴块棿鍘嗗彶"""
        room = crud.get_room(self.session, room_id)
        if not room:
            raise ValueError("room_not_found")

        commits = crud.get_commits_by_room(self.session, room_id, limit)

        commit_infos = [
            CommitInfo(
                id=c.id,  # type: ignore[arg-type]
                hash=c.hash or generate_commit_hash(c.id, c.timestamp),  # type: ignore[arg-type]
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

        # 鍔犱笂鍐呭瓨涓殑鏇存柊
        mem_updates_count = 0
        if websocket_server and hasattr(websocket_server, "get_ystore"):
            ystore = websocket_server.get_ystore(room_id)
            if ystore:
                mem_updates_count = ystore.get_buffer_stats()["buffer_size"]

        pending_changes += mem_updates_count

        total_size = sum(c.size for c in commit_infos)
        total_size += sum(len(u.data) if u.data else 0 for u in updates)
        # 浼扮畻鍐呭瓨鏇存柊澶у皬 (鍋囪骞冲潎 100 瀛楄妭锛屾垨鑰呭拷鐣ュぇ灏忕粺璁＄殑绮剧‘鎬?
        total_size += mem_updates_count * 100

        return HistoryResponse(
            room_id=room_id,
            head_commit_id=room.head_commit_id,
            commits=commit_infos,
            pending_changes=pending_changes,
            total_size=total_size,
        )

    def get_commit_detail(self, room_id: str, commit_id: int) -> CommitDetailResponse:
        """鑾峰彇鎻愪氦璇︽儏"""
        commit = crud.get_commit_by_id(self.session, commit_id)
        if not commit or commit.room_id != room_id:
            raise ValueError("commit_not_found")

        elements = parse_yjs_elements(commit.data)

        element_types = {}
        for element in elements.values():
            if isinstance(element, dict):
                # 璺宠繃宸插垹闄ょ殑鍏冪礌
                if element.get("isDeleted"):
                    continue
                element_type = element.get("type", "unknown")
                element_types[element_type] = element_types.get(element_type, 0) + 1

        # 璁＄畻鏈夋晥鍏冪礌鏁伴噺锛堟帓闄ゅ凡鍒犻櫎鐨勶級
        valid_elements_count = sum(
            1
            for el in elements.values()
            if isinstance(el, dict) and not el.get("isDeleted")
        )
        diagrams = parse_yjs_diagrams(commit.data)
        diagram_items, diagram_families, managed_states = summarize_diagrams(diagrams)

        commit_info = CommitInfo(
            id=commit.id,  # type: ignore[arg-type]
            hash=commit.hash or generate_commit_hash(commit.id, commit.timestamp),  # type: ignore[arg-type]
            parent_id=commit.parent_id,
            author_id=commit.author_id,
            author_name=commit.author_name,
            message=commit.message,
            timestamp=commit.timestamp,
            size=len(commit.data) if commit.data else 0,
        )

        return CommitDetailResponse(
            commit=commit_info,
            elements_count=valid_elements_count,
            element_types=element_types,
            diagrams_count=len(diagrams),
            diagram_families=diagram_families,
            managed_states=managed_states,
            diagrams=diagram_items,
        )

    def get_commit_diff(
        self, room_id: str, commit_id: int, base_commit_id: Optional[int] = None
    ) -> CommitDiffResponse:
        """鑾峰彇鎻愪氦宸紓"""
        to_commit = crud.get_commit_by_id(self.session, commit_id)
        if not to_commit or to_commit.room_id != room_id:
            raise ValueError("target_commit_not_found")

        from_commit = None
        if base_commit_id is not None:
            from_commit = crud.get_commit_by_id(self.session, base_commit_id)
            if not from_commit or from_commit.room_id != room_id:
                raise ValueError("base_commit_not_found")
        elif to_commit.parent_id:
            from_commit = crud.get_commit_by_id(self.session, to_commit.parent_id)

        old_elements = parse_yjs_elements(from_commit.data) if from_commit else {}
        new_elements = parse_yjs_elements(to_commit.data)
        old_diagrams = parse_yjs_diagrams(from_commit.data) if from_commit else {}
        new_diagrams = parse_yjs_diagrams(to_commit.data)

        added, removed, modified, changes = compute_elements_diff(
            old_elements, new_elements
        )
        diagrams_added, diagrams_removed, diagrams_modified, diagram_changes = (
            compute_diagrams_diff(old_diagrams, new_diagrams)
        )

        from_commit_info = None
        if from_commit:
            from_commit_info = CommitInfo(
                id=from_commit.id,  # type: ignore[arg-type]
                hash=from_commit.hash
                or generate_commit_hash(from_commit.id, from_commit.timestamp),  # type: ignore[arg-type]
                parent_id=from_commit.parent_id,
                author_id=from_commit.author_id,
                author_name=from_commit.author_name,
                message=from_commit.message,
                timestamp=from_commit.timestamp,
                size=len(from_commit.data) if from_commit.data else 0,
            )

        to_commit_info = CommitInfo(
            id=to_commit.id,  # type: ignore[arg-type]
            hash=to_commit.hash
            or generate_commit_hash(to_commit.id, to_commit.timestamp),  # type: ignore[arg-type]
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
            elements_added=added,
            elements_removed=removed,
            elements_modified=modified,
            changes=changes,
            diagrams_added=diagrams_added,
            diagrams_removed=diagrams_removed,
            diagrams_modified=diagrams_modified,
            diagram_changes=diagram_changes,
            size_diff=to_size - from_size,
        )


class VersionControlService(IGitService):
    """Application-layer facade for version-control workflows."""


def get_version_control_service(session: Session) -> VersionControlService:
    return VersionControlService(session)


def get_git_service(session: Session) -> VersionControlService:
    return get_version_control_service(session)


def load_history(
    session: Session,
    room_id: str,
    limit: int,
    *,
    websocket_server: Any = None,
) -> HistoryResponse:
    return get_version_control_service(session).get_history(
        room_id,
        limit,
        websocket_server=websocket_server,
    )

