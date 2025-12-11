"""包名称: version_control
功能说明: 类 Git 版本控制系统，提供提交、回滚、差异对比等功能
"""

from .router import router as version_control_router
from .models import (
    CommitInfo,
    HistoryResponse,
    CreateCommitRequest,
    CommitDetailResponse,
    CommitDiffResponse,
    StrokeChange,
)

__all__ = [
    "version_control_router",
    "CommitInfo",
    "HistoryResponse",
    "CreateCommitRequest",
    "CommitDetailResponse",
    "CommitDiffResponse",
    "StrokeChange",
]
