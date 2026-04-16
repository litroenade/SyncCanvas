"""API-layer dependency wrappers."""

from src.auth.utils import get_current_user, get_current_user_optional
from src.persistence.db.engine import get_session
from src.application.rooms.access import ensure_room_member_access, ensure_room_owner_access

__all__ = [
    "get_current_user",
    "get_current_user_optional",
    "get_session",
    "ensure_room_member_access",
    "ensure_room_owner_access",
]

