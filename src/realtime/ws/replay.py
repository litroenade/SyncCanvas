"""Realtime replay helper types."""

from typing import Any, Deque


def room_history_window(history: dict[str, Deque[dict[str, Any]]], room_id: str):
    return history.get(room_id)

