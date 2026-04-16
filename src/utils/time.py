"""Timezone-aware UTC time helpers."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""

    return datetime.now(UTC)


def timestamp_seconds() -> int:
    """Return the current Unix timestamp in seconds."""

    return int(utc_now().timestamp())


def timestamp_ms() -> int:
    """Return the current Unix timestamp in milliseconds."""

    return int(utc_now().timestamp() * 1000)


def datetime_from_timestamp(ts: int, *, is_ms: bool = False) -> datetime:
    """Convert a Unix timestamp into a timezone-aware UTC datetime."""

    seconds = ts / 1000 if is_ms else ts
    return datetime.fromtimestamp(seconds, UTC)


def format_timestamp(
    ts: int,
    fmt: str = "%Y-%m-%d %H:%M:%S",
    *,
    is_ms: bool = False,
) -> str:
    """Format a Unix timestamp using UTC time."""

    return datetime_from_timestamp(ts, is_ms=is_ms).strftime(fmt)
