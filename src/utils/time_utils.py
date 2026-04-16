"""Shared time helpers used by agent-side utilities."""

from src.utils.time import format_timestamp as format_utc_timestamp
from src.utils.time import timestamp_ms as current_timestamp_ms


def timestamp_ms() -> int:
    """Return the current Unix timestamp in milliseconds."""

    return current_timestamp_ms()


def format_timestamp(ts: int, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format a millisecond timestamp for display."""

    try:
        return format_utc_timestamp(ts, fmt=fmt, is_ms=True)
    except (ValueError, OSError):
        return "Invalid timestamp"


def relative_time(ts: int) -> str:
    """Return a short relative label for a millisecond timestamp."""

    now = timestamp_ms()
    diff_seconds = (now - ts) // 1000

    if diff_seconds < 0:
        return "Future"
    if diff_seconds < 60:
        return "Just now"
    if diff_seconds < 3600:
        minutes = diff_seconds // 60
        return f"{minutes}m ago"
    if diff_seconds < 86400:
        hours = diff_seconds // 3600
        return f"{hours}h ago"
    if diff_seconds < 2592000:
        days = diff_seconds // 86400
        return f"{days}d ago"
    return format_timestamp(ts, "%Y-%m-%d")


def parse_timestamp(
    time_str: str,
    fmt: str = "%Y-%m-%d %H:%M:%S",
) -> int | None:
    """Parse a formatted timestamp string into milliseconds."""

    from datetime import datetime

    try:
        return int(datetime.strptime(time_str, fmt).timestamp() * 1000)
    except ValueError:
        return None
