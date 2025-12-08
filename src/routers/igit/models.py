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


class ElementChange(BaseModel):
    """元素变更信息

    Attributes:
        element_id (str): 元素 ID
        action (str): 变更类型 (added, removed, modified)
        element_type (str): 元素类型 (rectangle, ellipse, arrow, text 等)
        text (str): 文本内容（如果是文本元素）
    """
    element_id: str
    action: str  # "added", "removed", "modified"
    element_type: Optional[str] = None
    text: Optional[str] = None


# 别名，保持兼容
StrokeChange = ElementChange


class CommitDiffResponse(BaseModel):
    """Commit 差异响应

    Attributes:
        room_id (str): 房间 ID
        from_commit (CommitInfo): 基准提交
        to_commit (CommitInfo): 目标提交
        elements_added (int): 新增元素数
        elements_removed (int): 删除元素数
        elements_modified (int): 修改元素数
        changes (List[ElementChange]): 变更详情列表
        size_diff (int): 大小差异 (字节)
    """
    room_id: str
    from_commit: Optional[CommitInfo]
    to_commit: CommitInfo
    elements_added: int
    elements_removed: int
    elements_modified: int
    changes: List[ElementChange]
    size_diff: int
    
    # 别名字段，保持向后兼容
    @property
    def strokes_added(self) -> int:
        return self.elements_added
    
    @property
    def strokes_removed(self) -> int:
        return self.elements_removed
    
    @property
    def strokes_modified(self) -> int:
        return self.elements_modified


class CommitDetailResponse(BaseModel):
    """Commit 详情响应

    Attributes:
        commit (CommitInfo): 提交信息
        elements_count (int): 元素总数
        element_types (dict): 元素类型统计
    """
    commit: CommitInfo
    elements_count: int
    element_types: dict  # element_type -> count
    
    # 别名字段，保持向后兼容
    @property
    def strokes_count(self) -> int:
        return self.elements_count
    
    @property
    def stroke_types(self) -> dict:
        return self.element_types
