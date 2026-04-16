"""Internal scene graph used by the managed diagram engine."""

from dataclasses import dataclass, field
from typing import Any

RectTuple = tuple[float, float, float, float]


@dataclass(slots=True)
class EngineNode:
    id: str
    component_type: str
    label: str
    shape: str
    family: str
    x: float
    y: float
    width: float
    height: float
    row_hint: int
    col_hint: int
    style: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    layout_locked: bool = False

    @property
    def cx(self) -> float:
        return self.x + self.width / 2

    @property
    def cy(self) -> float:
        return self.y + self.height / 2

    def bbox(self, pad: float = 0.0) -> RectTuple:
        return (
            self.x - pad,
            self.y - pad,
            self.x + self.width + pad,
            self.y + self.height + pad,
        )


@dataclass(slots=True)
class EngineEdge:
    id: str
    source_id: str
    target_id: str
    connector_type: str
    label: str = ""
    style: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EngineLabel:
    text: str
    x: float
    y: float
    width: float
    height: float
    edge_id: str

    def bbox(self, pad: float = 0.0) -> RectTuple:
        return (
            self.x - pad,
            self.y - pad,
            self.x + self.width + pad,
            self.y + self.height + pad,
        )


@dataclass(slots=True)
class EngineRoute:
    edge_id: str
    source_id: str
    target_id: str
    points: list[tuple[float, float]]
    label: EngineLabel | None = None


@dataclass(slots=True)
class EngineGroupFrame:
    id: str
    label: str
    family: str
    x: float
    y: float
    width: float
    height: float
    style: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EngineScene:
    title: str
    family: str
    nodes: list[EngineNode]
    edges: list[EngineEdge]
    groups: dict[str, list[str]] = field(default_factory=dict)
    layout_constraints: dict[str, Any] = field(default_factory=dict)
    active_node_ids: frozenset[str] | None = None
