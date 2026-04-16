"""Versioning domain models."""

from typing import List, Optional

from pydantic import BaseModel, Field


class CommitInfo(BaseModel):
    """Basic commit metadata."""

    id: int
    hash: str
    parent_id: Optional[int]
    author_id: Optional[int]
    author_name: str
    message: str
    timestamp: int
    size: int


class HistoryResponse(BaseModel):
    """History list payload for a room."""

    room_id: str
    head_commit_id: Optional[int]
    commits: List[CommitInfo]
    pending_changes: int
    total_size: int


class ElementChange(BaseModel):
    """Element-level diff item."""

    element_id: str
    action: str
    element_type: Optional[str] = None
    text: Optional[str] = None


class DiagramSummaryItem(BaseModel):
    """Compact diagram snapshot stored in commit detail/diff payloads."""

    diagram_id: str
    title: str
    family: str
    managed_state: str
    component_count: int
    connector_count: int
    version: int = 1


class DiagramChange(BaseModel):
    """Diagram-level diff item."""

    diagram_id: str
    action: str
    title: str = ""
    family: str = "layered_architecture"
    managed_state: Optional[str] = None
    component_count: Optional[int] = None
    connector_count: Optional[int] = None


class CommitDiffResponse(BaseModel):
    """Diff between two commits."""

    room_id: str
    from_commit: Optional[CommitInfo]
    to_commit: CommitInfo
    elements_added: int
    elements_removed: int
    elements_modified: int
    changes: List[ElementChange]
    diagrams_added: int = 0
    diagrams_removed: int = 0
    diagrams_modified: int = 0
    diagram_changes: List[DiagramChange] = Field(default_factory=list)
    size_diff: int


class CommitDetailResponse(BaseModel):
    """Commit detail payload."""

    commit: CommitInfo
    elements_count: int
    element_types: dict
    diagrams_count: int = 0
    diagram_families: dict = Field(default_factory=dict)
    managed_states: dict = Field(default_factory=dict)
    diagrams: List[DiagramSummaryItem] = Field(default_factory=list)
