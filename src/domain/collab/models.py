"""Collaboration domain models."""

from dataclasses import dataclass


@dataclass(slots=True)
class RoomActivityState:
    room_id: str
    online_connections: int = 0
    last_activity_ts: float = 0.0
