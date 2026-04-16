
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select, desc

from src.auth.utils import get_current_user
from src.infra.config import config
from src.infra.logging import get_logger
from src.infra.metrics import inc_counter, snapshot as get_metrics_snapshot
from src.persistence.db.engine import get_session
from src.persistence.db.models import Commit, Room, Update
from src.persistence.db.models.users import User
from src.realtime.yjs.server import websocket_server

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

DEFAULT_KEEP_LATEST_COMMITS = 20
DEFAULT_KEEP_UPDATES_DAYS = 30
MS_PER_DAY = 24 * 3600 * 1000


def _require_admin(current_user: User) -> None:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")


class CleanupRequest(BaseModel):
    """Cleanup operation request."""

    keep_rooms: Optional[list[str]] = Field(default=None)
    keep_latest_commits: int = Field(default=20, ge=1, le=200)
    keep_updates_days: int = Field(default=30, ge=1)


@router.get("/cleanup/status")
async def admin_cleanup_status(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Return storage cleanup posture."""

    _require_admin(current_user)

    rooms = session.exec(select(Room)).all()
    commits = session.exec(select(Commit)).all()
    updates = session.exec(select(Update)).all()

    by_room_commits: dict[str, list[Commit]] = {}
    by_room_updates: dict[str, list[Update]] = {}
    for commit in commits:
        by_room_commits.setdefault(commit.room_id, []).append(commit)
    for update in updates:
        by_room_updates.setdefault(update.room_id, []).append(update)

    now_ms = int(datetime.now().timestamp() * 1000)
    update_cutoff = now_ms - DEFAULT_KEEP_UPDATES_DAYS * MS_PER_DAY
    cleanup_risk_rooms = 0
    cleanup_stale_commits = 0
    cleanup_stale_updates = 0
    cleanup_health: list[dict[str, object]] = []

    room_stats = {}
    for room in rooms:
        room_updates = by_room_updates.get(room.id, [])
        room_commits = by_room_commits.get(room.id, [])
        stale_commits = max(0, len(room_commits) - DEFAULT_KEEP_LATEST_COMMITS)
        stale_updates = len([u for u in room_updates if u.timestamp < update_cutoff])
        needs_cleanup = stale_commits > 0 or stale_updates > 0
        if needs_cleanup:
            cleanup_risk_rooms += 1
            cleanup_stale_commits += stale_commits
            cleanup_stale_updates += stale_updates
            cleanup_health.append(
                {
                    "room_id": room.id,
                    "stale_commits": stale_commits,
                    "stale_updates": stale_updates,
                },
            )

        try:
            ystore = websocket_server.get_ystore(room.id)
            buffer_size = ystore.get_buffer_stats().get("buffer_size", 0) if ystore else 0
        except Exception:
            buffer_size = 0

        room_stats[room.id] = {
            "updates": len(room_updates),
            "commits": len(room_commits),
            "buffer_size": buffer_size,
            "online": websocket_server.get_room_connections(f"/ws/{room.id}"),
            "head_commit_id": room.head_commit_id,
            "stale_commits": stale_commits,
            "stale_updates": stale_updates,
            "needs_cleanup": needs_cleanup,
        }

    return {
        "status": "ok" if cleanup_risk_rooms == 0 else "warn",
        "summary": {
            "rooms": len(rooms),
            "commits": len(commits),
            "updates": len(updates),
            "cleanup_threshold": {
                "keep_latest_commits": DEFAULT_KEEP_LATEST_COMMITS,
                "keep_updates_days": DEFAULT_KEEP_UPDATES_DAYS,
            },
            "cleanup_risk_rooms": cleanup_risk_rooms,
            "cleanup_stale_commits": cleanup_stale_commits,
            "cleanup_stale_updates": cleanup_stale_updates,
        },
        "cleanup_health": cleanup_health,
        "rooms": room_stats,
        "metrics": get_metrics_snapshot(),
    }


@router.post("/cleanup/run")
async def admin_cleanup_run(
    req: CleanupRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Execute one cleanup task for DB retained history."""

    _require_admin(current_user)

    keep_rooms = set(req.keep_rooms or [])
    keep_latest_commits = req.keep_latest_commits
    keep_updates_days = req.keep_updates_days

    now_ms = int(datetime.now().timestamp() * 1000)
    update_cutoff = now_ms - keep_updates_days * 24 * 3600 * 1000

    affected_rooms = 0
    deleted_updates = 0
    deleted_commits = 0

    rooms = session.exec(select(Room)).all()
    for room in rooms:
        if room.id in keep_rooms:
            continue

        affected_rooms += 1

        room_commits = session.exec(
            select(Commit).where(Commit.room_id == room.id).order_by(desc(Commit.timestamp))
        ).all()

        # Keep the latest N commits per room.
        if len(room_commits) > keep_latest_commits:
            keep_ids = {c.id for c in room_commits[:keep_latest_commits] if c.id is not None}
            for commit in room_commits[keep_latest_commits:]:
                if commit.id is not None and commit.id not in keep_ids:
                    session.delete(commit)
                    deleted_commits += 1

        # Delete old updates.
        stale_updates = session.exec(
            select(Update).where(Update.room_id == room.id).where(Update.timestamp < update_cutoff)
        ).all()
        for stale_update in stale_updates:
            session.delete(stale_update)
            deleted_updates += 1

    session.commit()
    inc_counter(
        "admin_cleanup_runs_total",
        labels={
            "status": "ok",
            "keep_latest_commits": str(keep_latest_commits),
            "keep_updates_days": str(keep_updates_days),
        },
    )
    inc_counter(
        "admin_cleanup_deleted_items_total",
        value=deleted_updates + deleted_commits,
        labels={"scope": "room_cleanup"},
    )

    # Trigger compaction for all idle rooms (best effort).
    try:
        await websocket_server.check_idle_rooms(0)
    except Exception as err:  # pragma: no cover - best effort cleanup hook
        logger.warning("Cleanup async compaction hint failed: %s", err)

    return {
        "status": "ok",
        "affected_rooms": affected_rooms,
        "deleted_updates": deleted_updates,
        "deleted_commits": deleted_commits,
    }


@router.get("/healthz")
async def admin_healthz(current_user: User = Depends(get_current_user)):
    """Simple internal health endpoint."""

    _require_admin(current_user)
    return {
        "status": "ok",
        "version": config.version,
    }


