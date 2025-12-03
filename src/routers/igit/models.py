"""模块名称: models
主要功能: iGit 版本控制系统的数据模型定义
"""

from typing import Optional, List

from pydantic import BaseModel, Field


class CommitInfo(BaseModel):
    """提交信息

    Attributes:
        id (int): 提交 ID
        hash (str): 提交哈希 (7位)
        parent_id (int): 父提交 ID
        author_id (int): 作者 ID
        author_name (str): 作者名称
        message (str): 提交消息
        timestamp (int): 时间戳 (毫秒)
        size (int): 数据大小 (字节)
    """
    id: int
    hash: str
    parent_id: Optional[int]
    author_id: Optional[int]
    author_name: str
    message: str
    timestamp: int
    size: int


class HistoryResponse(BaseModel):
    """历史响应

    Attributes:
        room_id (str): 房间 ID
        head_commit_id (int): 当前 HEAD 指向的提交 ID
        commits (List[CommitInfo]): 提交列表 (从新到旧)
        pending_changes (int): 待提交的更改数量
        total_size (int): 总数据大小
    """
    room_id: str
    head_commit_id: Optional[int]
    commits: List[CommitInfo]
    pending_changes: int
    total_size: int


class CreateCommitRequest(BaseModel):
    """创建提交请求

    Attributes:
        message (str): 提交消息
        author_name (str): 作者名称 (可选，默认使用登录用户名)
    """
    message: str = Field(default="手动保存", max_length=500)
    author_name: Optional[str] = Field(default=None, max_length=100)


class StrokeChange(BaseModel):
    """笔画变更信息

    Attributes:
        shape_id (str): 图形 ID
        action (str): 变更类型 (added, removed, modified)
        stroke_type (str): 笔画类型
        points_count (int): 点数量
    """
    shape_id: str
    action: str  # "added", "removed", "modified"
    stroke_type: Optional[str] = None
    points_count: Optional[int] = None


class CommitDiffResponse(BaseModel):
    """Commit 差异响应

    Attributes:
        room_id (str): 房间 ID
        from_commit (CommitInfo): 基准提交
        to_commit (CommitInfo): 目标提交
        strokes_added (int): 新增笔画数
        strokes_removed (int): 删除笔画数
        strokes_modified (int): 修改笔画数
        changes (List[StrokeChange]): 变更详情列表
        size_diff (int): 大小差异 (字节)
    """
    room_id: str
    from_commit: Optional[CommitInfo]
    to_commit: CommitInfo
    strokes_added: int
    strokes_removed: int
    strokes_modified: int
    changes: List[StrokeChange]
    size_diff: int


class CommitDetailResponse(BaseModel):
    """Commit 详情响应

    Attributes:
        commit (CommitInfo): 提交信息
        strokes_count (int): 笔画总数
        stroke_types (dict): 笔画类型统计
    """
    commit: CommitInfo
    strokes_count: int
    stroke_types: dict  # stroke_type -> count
