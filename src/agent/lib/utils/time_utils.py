"""
时间处理工具
"""

from datetime import datetime
from typing import Optional


def timestamp_ms() -> int:
    """获取当前毫秒时间戳

    Returns:
        毫秒时间戳
    """
    return int(datetime.utcnow().timestamp() * 1000)


def format_timestamp(ts: int, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化毫秒时间戳

    Args:
        ts: 毫秒时间戳
        fmt: 格式字符串

    Returns:
        格式化的时间字符串
    """
    try:
        dt = datetime.fromtimestamp(ts / 1000)
        return dt.strftime(fmt)
    except (ValueError, OSError):
        return "Invalid timestamp"


def relative_time(ts: int) -> str:
    """将时间戳转为相对时间描述

    Args:
        ts: 毫秒时间戳

    Returns:
        相对时间描述 (如 "5分钟前", "2小时前")
    """
    now = timestamp_ms()
    diff_seconds = (now - ts) // 1000

    if diff_seconds < 0:
        return "未来"
    elif diff_seconds < 60:
        return "刚刚"
    elif diff_seconds < 3600:
        minutes = diff_seconds // 60
        return f"{minutes}分钟前"
    elif diff_seconds < 86400:
        hours = diff_seconds // 3600
        return f"{hours}小时前"
    elif diff_seconds < 2592000:  # 30 days
        days = diff_seconds // 86400
        return f"{days}天前"
    else:
        return format_timestamp(ts, "%Y-%m-%d")


def parse_timestamp(time_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> Optional[int]:
    """解析时间字符串为毫秒时间戳

    Args:
        time_str: 时间字符串
        fmt: 格式字符串

    Returns:
        毫秒时间戳，解析失败返回 None
    """
    try:
        dt = datetime.strptime(time_str, fmt)
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None
