
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SemanticNode:
    id: str
    label: str
    kind: str
    family: str
    row_hint: int = 0
    col_hint: int = 0
    attrs: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    group: Optional[str] = None
    style_role: str = "default"
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticEdge:
    id: str
    src: str
    dst: str
    kind: str = "assoc"
    label: str = ""
    dashed: bool = False
    preferred_dir: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticGroup:
    id: str
    label: str
    kind: str
    members: List[str]
    row_hint: int = 0
    col_hint: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticDiagram:
    id: str
    title: str
    family: str
    nodes: List[SemanticNode]
    edges: List[SemanticEdge]
    groups: List[SemanticGroup] = field(default_factory=list)
    keepouts: List[Tuple[float, float, float, float]] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeomNode:
    id: str
    label: str
    kind: str
    family: str
    x: float
    y: float
    w: float
    h: float
    row: int
    col: int
    attrs: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    group: Optional[str] = None
    style_role: str = "default"
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    def bbox(self, pad: float = 0.0) -> Tuple[float, float, float, float]:
        return (self.x - pad, self.y - pad, self.x + self.w + pad, self.y + self.h + pad)


@dataclass
class LabelBox:
    text: str
    x: float
    y: float
    w: float
    h: float
    edge_id: str

    def bbox(self, pad: float = 0.0) -> Tuple[float, float, float, float]:
        return (self.x - pad, self.y - pad, self.x + self.w + pad, self.y + self.h + pad)


@dataclass
class Route:
    edge_id: str
    points: List[Tuple[float, float]]
    label: Optional[LabelBox] = None
