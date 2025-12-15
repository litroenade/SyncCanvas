"""模块名称: canvas_model
主要功能: 画布元素模型 (类似 DrawIO 的 mxCell)

提供画布元素的统一数据结构:
- CanvasElement: 单个元素
- Geometry: 几何信息
- CanvasModel: 画布整体模型
- 支持从 Excalidraw/Yjs 解析和序列化
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

from src.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


# ==================== 元素类型 ====================


class ElementType(Enum):
    """元素类型"""

    RECTANGLE = "rectangle"
    ELLIPSE = "ellipse"
    DIAMOND = "diamond"
    ARROW = "arrow"
    LINE = "line"
    TEXT = "text"
    FREEDRAW = "freedraw"
    IMAGE = "image"
    FRAME = "frame"
    GROUP = "group"


# ==================== 几何信息 ====================


@dataclass
class Geometry:
    """元素几何信息"""

    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 100.0
    angle: float = 0.0

    @property
    def center(self) -> tuple[float, float]:
        """中心点坐标"""
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """边界框 (min_x, min_y, max_x, max_y)"""
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    def contains_point(self, px: float, py: float) -> bool:
        """判断点是否在元素内"""
        return (
            self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height
        )

    def intersects(self, other: "Geometry") -> bool:
        """判断是否与另一个几何相交"""
        return not (
            self.x + self.width < other.x
            or other.x + other.width < self.x
            or self.y + self.height < other.y
            or other.y + other.height < self.y
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "angle": self.angle,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Geometry":
        return cls(
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            width=data.get("width", 100.0),
            height=data.get("height", 100.0),
            angle=data.get("angle", 0.0),
        )


# ==================== 样式信息 ====================


@dataclass
class Style:
    """元素样式"""

    stroke_color: str = "#1e1e1e"
    background_color: str = "#a5d8ff"
    fill_style: str = "solid"  # solid, hachure, cross-hatch
    stroke_width: int = 2
    stroke_style: str = "solid"  # solid, dashed, dotted
    opacity: int = 100
    font_size: int = 16
    font_family: int = 1
    text_align: str = "center"
    roughness: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strokeColor": self.stroke_color,
            "backgroundColor": self.background_color,
            "fillStyle": self.fill_style,
            "strokeWidth": self.stroke_width,
            "strokeStyle": self.stroke_style,
            "opacity": self.opacity,
            "fontSize": self.font_size,
            "fontFamily": self.font_family,
            "textAlign": self.text_align,
            "roughness": self.roughness,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Style":
        return cls(
            stroke_color=data.get("strokeColor", "#1e1e1e"),
            background_color=data.get("backgroundColor", "#a5d8ff"),
            fill_style=data.get("fillStyle", "solid"),
            stroke_width=data.get("strokeWidth", 2),
            stroke_style=data.get("strokeStyle", "solid"),
            opacity=data.get("opacity", 100),
            font_size=data.get("fontSize", 16),
            font_family=data.get("fontFamily", 1),
            text_align=data.get("textAlign", "center"),
            roughness=data.get("roughness", 1),
        )


# ==================== 连接信息 ====================


@dataclass
class Binding:
    """元素绑定/连接信息"""

    element_id: str
    focus: float = 0.0
    gap: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "elementId": self.element_id,
            "focus": self.focus,
            "gap": self.gap,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["Binding"]:
        if not data:
            return None
        return cls(
            element_id=data.get("elementId", ""),
            focus=data.get("focus", 0.0),
            gap=data.get("gap", 1.0),
        )


# ==================== 画布元素 ====================


@dataclass
class CanvasElement:
    """画布元素 (类似 mxCell)

    统一的元素数据结构，支持所有 Excalidraw 元素类型。

    Attributes:
        id: 元素唯一标识
        type: 元素类型
        geometry: 几何信息 (位置、大小)
        style: 样式信息
        value: 文本内容 (对于有文字的元素)
        parent_id: 父元素 ID (用于分组)
        bound_elements: 绑定的元素列表
        start_binding: 箭头起始绑定
        end_binding: 箭头结束绑定
    """

    id: str
    type: ElementType
    geometry: Geometry = field(default_factory=Geometry)
    style: Style = field(default_factory=Style)
    value: str = ""  # 文本内容
    parent_id: Optional[str] = None
    group_ids: List[str] = field(default_factory=list)
    bound_elements: List[Dict[str, str]] = field(default_factory=list)
    start_binding: Optional[Binding] = None
    end_binding: Optional[Binding] = None
    is_deleted: bool = False
    locked: bool = False
    version: int = 1

    @property
    def is_shape(self) -> bool:
        """是否为形状元素"""
        return self.type in (
            ElementType.RECTANGLE,
            ElementType.ELLIPSE,
            ElementType.DIAMOND,
        )

    @property
    def is_connector(self) -> bool:
        """是否为连接器"""
        return self.type in (ElementType.ARROW, ElementType.LINE)

    @property
    def is_text(self) -> bool:
        """是否为文本"""
        return self.type == ElementType.TEXT

    @property
    def connected_to(self) -> List[str]:
        """获取连接到的元素 ID 列表"""
        ids = []
        if self.start_binding:
            ids.append(self.start_binding.element_id)
        if self.end_binding:
            ids.append(self.end_binding.element_id)
        return ids

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 (Excalidraw 格式)"""
        result = {
            "id": self.id,
            "type": self.type.value,
            **self.geometry.to_dict(),
            **self.style.to_dict(),
            "isDeleted": self.is_deleted,
            "locked": self.locked,
            "version": self.version,
            "groupIds": self.group_ids,
            "boundElements": self.bound_elements,
        }

        if self.value:
            result["text"] = self.value
            result["originalText"] = self.value

        if self.start_binding:
            result["startBinding"] = self.start_binding.to_dict()
        if self.end_binding:
            result["endBinding"] = self.end_binding.to_dict()

        return result

    @classmethod
    def from_excalidraw(cls, data: Dict[str, Any]) -> "CanvasElement":
        """从 Excalidraw 元素创建"""
        elem_type_str = data.get("type", "rectangle")
        try:
            elem_type = ElementType(elem_type_str)
        except ValueError:
            elem_type = ElementType.RECTANGLE

        return cls(
            id=data.get("id", ""),
            type=elem_type,
            geometry=Geometry.from_dict(data),
            style=Style.from_dict(data),
            value=data.get("text", data.get("originalText", "")),
            parent_id=data.get("frameId"),
            group_ids=data.get("groupIds", []),
            bound_elements=data.get("boundElements", []) or [],
            start_binding=Binding.from_dict(data.get("startBinding")),
            end_binding=Binding.from_dict(data.get("endBinding")),
            is_deleted=data.get("isDeleted", False),
            locked=data.get("locked", False),
            version=data.get("version", 1),
        )


# ==================== 画布模型 ====================


@dataclass
class CanvasModel:
    """画布模型

    管理画布上所有元素，提供查询和操作接口。
    """

    elements: Dict[str, CanvasElement] = field(default_factory=dict)
    _selection: Set[str] = field(default_factory=set)

    @property
    def element_count(self) -> int:
        return len(self.elements)

    @property
    def is_empty(self) -> bool:
        return len(self.elements) == 0

    @property
    def selection(self) -> List[CanvasElement]:
        """获取当前选中的元素"""
        return [self.elements[eid] for eid in self._selection if eid in self.elements]

    def add_element(self, element: CanvasElement) -> None:
        """添加元素"""
        self.elements[element.id] = element

    def remove_element(self, element_id: str) -> Optional[CanvasElement]:
        """移除元素"""
        return self.elements.pop(element_id, None)

    def get_element(self, element_id: str) -> Optional[CanvasElement]:
        """获取元素"""
        return self.elements.get(element_id)

    def get_elements_by_type(self, elem_type: ElementType) -> List[CanvasElement]:
        """根据类型获取元素"""
        return [e for e in self.elements.values() if e.type == elem_type]

    def get_shapes(self) -> List[CanvasElement]:
        """获取所有形状"""
        return [e for e in self.elements.values() if e.is_shape]

    def get_connectors(self) -> List[CanvasElement]:
        """获取所有连接器"""
        return [e for e in self.elements.values() if e.is_connector]

    def find_by_text(self, text: str) -> List[CanvasElement]:
        """根据文本内容查找元素"""
        text_lower = text.lower()
        return [
            e
            for e in self.elements.values()
            if e.value and text_lower in e.value.lower()
        ]

    def find_at_position(self, x: float, y: float) -> List[CanvasElement]:
        """查找指定位置的元素"""
        return [e for e in self.elements.values() if e.geometry.contains_point(x, y)]

    def find_in_region(
        self, min_x: float, min_y: float, max_x: float, max_y: float
    ) -> List[CanvasElement]:
        """查找指定区域内的元素"""
        region = Geometry(x=min_x, y=min_y, width=max_x - min_x, height=max_y - min_y)
        return [e for e in self.elements.values() if e.geometry.intersects(region)]

    def get_connections(self, element_id: str) -> List[CanvasElement]:
        """获取与指定元素相连的连接器"""
        result = []
        for elem in self.elements.values():
            if elem.is_connector:
                if (
                    elem.start_binding and elem.start_binding.element_id == element_id
                ) or (elem.end_binding and elem.end_binding.element_id == element_id):
                    result.append(elem)
        return result

    def select(self, element_ids: List[str]) -> None:
        """选择元素"""
        self._selection = set(eid for eid in element_ids if eid in self.elements)

    def clear_selection(self) -> None:
        """清除选择"""
        self._selection.clear()

    def to_summary(self) -> str:
        """生成画布摘要 (用于 LLM 上下文)"""
        if self.is_empty:
            return "画布为空"

        # 统计
        type_counts: Dict[str, int] = {}
        texts: List[str] = []

        for elem in self.elements.values():
            if elem.is_deleted:
                continue
            type_counts[elem.type.value] = type_counts.get(elem.type.value, 0) + 1
            if elem.value:
                texts.append(
                    f'"{elem.value[:15]}..."'
                    if len(elem.value) > 15
                    else f'"{elem.value}"'
                )

        # 构建摘要
        parts = [f"画布包含 {self.element_count} 个元素"]
        type_desc = ", ".join(f"{count}个 {t}" for t, count in type_counts.items())
        parts.append(f"类型: {type_desc}")

        if texts:
            parts.append(f"内容: {', '.join(texts[:5])}")

        return "; ".join(parts)

    @classmethod
    def from_yjs(cls, ydoc: Any) -> "CanvasModel":
        """从 Yjs 文档创建"""
        model = cls()

        try:
            elements_array = ydoc.get("elements", type="Array")
            for elem_data in elements_array:
                if isinstance(elem_data, dict):
                    elem = CanvasElement.from_excalidraw(elem_data)
                    model.add_element(elem)
        except Exception as e:
            logger.warning("[CanvasModel] 从 Yjs 解析失败: %s", e)

        return model


# ==================== 工厂函数 ====================


def create_element(
    element_type: ElementType,
    x: float = 0,
    y: float = 0,
    width: float = 100,
    height: float = 100,
    value: str = "",
    **style_kwargs: Any,
) -> CanvasElement:
    """创建新元素"""
    import uuid

    return CanvasElement(
        id=str(uuid.uuid4()),
        type=element_type,
        geometry=Geometry(x=x, y=y, width=width, height=height),
        style=Style(**style_kwargs) if style_kwargs else Style(),
        value=value,
    )
