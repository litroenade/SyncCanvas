"""模块名称: commands
主要功能: 元素控制命令系统
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from src.agent.canvas.model import (
    CanvasModel,
    ElementType,
)
from src.logger import get_logger

from src.agent.canvas.model import create_element

logger = get_logger(__name__)


# ==================== 命令类型 ====================


class CommandType(Enum):
    """命令类型"""

    # 选择
    SELECT = "select"
    DESELECT = "deselect"
    SELECT_ALL = "select_all"

    # 变换
    MOVE = "move"
    RESIZE = "resize"
    ROTATE = "rotate"

    # 连接
    CONNECT = "connect"
    DISCONNECT = "disconnect"

    # 修改
    UPDATE = "update"
    DELETE = "delete"
    DUPLICATE = "duplicate"

    # 分组
    GROUP = "group"
    UNGROUP = "ungroup"

    # 对齐
    ALIGN = "align"
    DISTRIBUTE = "distribute"

    # 创建 (保留生成能力)
    CREATE = "create"

    # 画布操作
    CLEAR = "clear"
    UNDO = "undo"
    REDO = "redo"


# ==================== 命令基类 ====================


@dataclass
class Command(ABC):
    """命令基类"""

    type: CommandType

    @abstractmethod
    def execute(self, model: CanvasModel) -> CommandResult:
        """执行命令"""

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Command":
        """从字典创建命令"""
        cmd_type = data.get("cmd", data.get("type", ""))

        try:
            command_type = CommandType(cmd_type)
        except ValueError:
            raise ValueError(f"未知命令类型: {cmd_type}")

        # 根据类型创建具体命令
        command_classes = {
            CommandType.SELECT: SelectCommand,
            CommandType.DESELECT: DeselectCommand,
            CommandType.MOVE: MoveCommand,
            CommandType.RESIZE: ResizeCommand,
            CommandType.CONNECT: ConnectCommand,
            CommandType.UPDATE: UpdateCommand,
            CommandType.DELETE: DeleteCommand,
            CommandType.CREATE: CreateCommand,
            CommandType.GROUP: GroupCommand,
            CommandType.ALIGN: AlignCommand,
        }

        cmd_class = command_classes.get(command_type)
        if cmd_class:
            return cmd_class.from_dict(data)

        raise ValueError(f"不支持的命令类型: {cmd_type}")


@dataclass
class CommandResult:
    """命令执行结果"""

    success: bool
    message: str = ""
    affected_ids: List[str] = field(default_factory=list)
    changes: Dict[str, Any] = field(default_factory=dict)


# ==================== 选择命令 ====================


@dataclass
class SelectCommand(Command):
    """选择元素命令"""

    type: CommandType = field(default=CommandType.SELECT)
    target_ids: List[str] = field(default_factory=list)
    by_text: Optional[str] = None  # 根据文本内容选择
    by_type: Optional[str] = None  # 根据类型选择
    in_region: Optional[Dict[str, float]] = None  # 区域选择

    def execute(self, model: CanvasModel) -> CommandResult:
        elements = []

        # 根据 ID 选择
        if self.target_ids:
            elements = [model.get_element(eid) for eid in self.target_ids]
            elements = [e for e in elements if e]

        # 根据文本选择
        elif self.by_text:
            elements = model.find_by_text(self.by_text)

        # 根据类型选择
        elif self.by_type:
            try:
                elem_type = ElementType(self.by_type)
                elements = model.get_elements_by_type(elem_type)
            except ValueError:
                pass

        # 区域选择
        elif self.in_region:
            elements = model.find_in_region(
                self.in_region.get("min_x", 0),
                self.in_region.get("min_y", 0),
                self.in_region.get("max_x", 1000),
                self.in_region.get("max_y", 1000),
            )

        selected_ids = [e.id for e in elements]
        model.select(selected_ids)

        return CommandResult(
            success=True,
            message=f"选中 {len(selected_ids)} 个元素",
            affected_ids=selected_ids,
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {"cmd": self.type.value}
        if self.target_ids:
            result["target_ids"] = self.target_ids
        if self.by_text:
            result["by_text"] = self.by_text
        if self.by_type:
            result["by_type"] = self.by_type
        if self.in_region:
            result["in_region"] = self.in_region
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SelectCommand":
        return cls(
            target_ids=data.get("target_ids", data.get("targets", [])),
            by_text=data.get("by_text"),
            by_type=data.get("by_type"),
            in_region=data.get("in_region"),
        )


@dataclass
class DeselectCommand(Command):
    """取消选择命令"""

    type: CommandType = field(default=CommandType.DESELECT)

    def execute(self, model: CanvasModel) -> CommandResult:
        model.clear_selection()
        return CommandResult(success=True, message="取消所有选择")

    def to_dict(self) -> Dict[str, Any]:
        return {"cmd": self.type.value}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeselectCommand":
        return cls()


# ==================== 变换命令 ====================


@dataclass
class MoveCommand(Command):
    """移动元素命令"""

    type: CommandType = field(default=CommandType.MOVE)
    target_ids: List[str] = field(default_factory=list)
    dx: float = 0.0  # X 方向偏移
    dy: float = 0.0  # Y 方向偏移
    to_x: Optional[float] = None  # 移动到绝对位置
    to_y: Optional[float] = None

    def execute(self, model: CanvasModel) -> CommandResult:
        moved = []

        for eid in self.target_ids:
            elem = model.get_element(eid)
            if not elem:
                continue

            if self.to_x is not None:
                elem.geometry.x = self.to_x
            else:
                elem.geometry.x += self.dx

            if self.to_y is not None:
                elem.geometry.y = self.to_y
            else:
                elem.geometry.y += self.dy

            moved.append(eid)

        return CommandResult(
            success=True,
            message=f"移动了 {len(moved)} 个元素",
            affected_ids=moved,
            changes={"dx": self.dx, "dy": self.dy},
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {"cmd": self.type.value, "target_ids": self.target_ids}
        if self.dx != 0:
            result["dx"] = self.dx
        if self.dy != 0:
            result["dy"] = self.dy
        if self.to_x is not None:
            result["to_x"] = self.to_x
        if self.to_y is not None:
            result["to_y"] = self.to_y
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MoveCommand":
        return cls(
            target_ids=data.get("target_ids", data.get("targets", [])),
            dx=data.get("dx", 0.0),
            dy=data.get("dy", 0.0),
            to_x=data.get("to_x"),
            to_y=data.get("to_y"),
        )


@dataclass
class ResizeCommand(Command):
    """调整大小命令"""

    type: CommandType = field(default=CommandType.RESIZE)
    target_ids: List[str] = field(default_factory=list)
    width: Optional[float] = None
    height: Optional[float] = None
    scale: Optional[float] = None  # 缩放比例

    def execute(self, model: CanvasModel) -> CommandResult:
        resized = []

        for eid in self.target_ids:
            elem = model.get_element(eid)
            if not elem:
                continue

            if self.scale:
                elem.geometry.width *= self.scale
                elem.geometry.height *= self.scale
            else:
                if self.width is not None:
                    elem.geometry.width = self.width
                if self.height is not None:
                    elem.geometry.height = self.height

            resized.append(eid)

        return CommandResult(
            success=True,
            message=f"调整了 {len(resized)} 个元素大小",
            affected_ids=resized,
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {"cmd": self.type.value, "target_ids": self.target_ids}
        if self.width is not None:
            result["width"] = self.width
        if self.height is not None:
            result["height"] = self.height
        if self.scale is not None:
            result["scale"] = self.scale
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResizeCommand":
        return cls(
            target_ids=data.get("target_ids", data.get("targets", [])),
            width=data.get("width"),
            height=data.get("height"),
            scale=data.get("scale"),
        )


# ==================== 连接命令 ====================


@dataclass
class ConnectCommand(Command):
    """连接元素命令"""

    type: CommandType = field(default=CommandType.CONNECT)
    from_id: str = ""
    to_id: str = ""
    label: str = ""

    def execute(self, model: CanvasModel) -> CommandResult:
        from_elem = model.get_element(self.from_id)
        to_elem = model.get_element(self.to_id)

        if not from_elem or not to_elem:
            return CommandResult(
                success=False,
                message="源或目标元素不存在",
            )

        # 创建箭头连接 (需要后续由 Transaction 处理)
        return CommandResult(
            success=True,
            message=f"连接 {self.from_id[:8]} → {self.to_id[:8]}",
            affected_ids=[self.from_id, self.to_id],
            changes={
                "connection": {
                    "from": self.from_id,
                    "to": self.to_id,
                    "label": self.label,
                }
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cmd": self.type.value,
            "from_id": self.from_id,
            "to_id": self.to_id,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConnectCommand":
        return cls(
            from_id=data.get("from_id", data.get("from", "")),
            to_id=data.get("to_id", data.get("to", "")),
            label=data.get("label", ""),
        )


# ==================== 修改命令 ====================


@dataclass
class UpdateCommand(Command):
    """更新元素属性命令"""

    type: CommandType = field(default=CommandType.UPDATE)
    target_ids: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)  # 要更新的属性

    def execute(self, model: CanvasModel) -> CommandResult:
        updated = []

        for eid in self.target_ids:
            elem = model.get_element(eid)
            if not elem:
                continue

            # 更新属性
            if "text" in self.properties or "value" in self.properties:
                elem.value = self.properties.get(
                    "text", self.properties.get("value", elem.value)
                )

            if "strokeColor" in self.properties:
                elem.style.stroke_color = self.properties["strokeColor"]

            if "backgroundColor" in self.properties:
                elem.style.background_color = self.properties["backgroundColor"]

            updated.append(eid)

        return CommandResult(
            success=True,
            message=f"更新了 {len(updated)} 个元素",
            affected_ids=updated,
            changes={"properties": self.properties},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cmd": self.type.value,
            "target_ids": self.target_ids,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UpdateCommand":
        return cls(
            target_ids=data.get("target_ids", data.get("targets", [])),
            properties=data.get("properties", {}),
        )


@dataclass
class DeleteCommand(Command):
    """删除元素命令"""

    type: CommandType = field(default=CommandType.DELETE)
    target_ids: List[str] = field(default_factory=list)

    def execute(self, model: CanvasModel) -> CommandResult:
        deleted = []

        for eid in self.target_ids:
            elem = model.remove_element(eid)
            if elem:
                deleted.append(eid)

        return CommandResult(
            success=True,
            message=f"删除了 {len(deleted)} 个元素",
            affected_ids=deleted,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cmd": self.type.value,
            "target_ids": self.target_ids,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeleteCommand":
        return cls(
            target_ids=data.get("target_ids", data.get("targets", [])),
        )


# ==================== 创建命令 (保留生成能力) ====================


@dataclass
class CreateCommand(Command):
    """创建元素命令"""

    type: CommandType = field(default=CommandType.CREATE)
    element_type: str = "rectangle"
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 100.0
    value: str = ""
    style: Dict[str, Any] = field(default_factory=dict)

    def execute(self, model: CanvasModel) -> CommandResult:

        try:
            elem_type = ElementType(self.element_type)
        except ValueError:
            elem_type = ElementType.RECTANGLE


        element = create_element(
            element_type=elem_type,
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            value=self.value,
            **self.style,
        )

        model.add_element(element)

        return CommandResult(
            success=True,
            message=f"创建了 {self.element_type} 元素",
            affected_ids=[element.id],
            changes={"created": element.to_dict()},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cmd": self.type.value,
            "element_type": self.element_type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "value": self.value,
            "style": self.style,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CreateCommand":
        return cls(
            element_type=data.get("element_type", data.get("type", "rectangle")),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            width=data.get("width", 100.0),
            height=data.get("height", 100.0),
            value=data.get("value", data.get("text", data.get("label", ""))),
            style=data.get("style", {}),
        )


# ==================== 分组命令 ====================


@dataclass
class GroupCommand(Command):
    """分组命令"""

    type: CommandType = field(default=CommandType.GROUP)
    target_ids: List[str] = field(default_factory=list)

    def execute(self, model: CanvasModel) -> CommandResult:
        import uuid

        group_id = str(uuid.uuid4())

        for eid in self.target_ids:
            elem = model.get_element(eid)
            if elem:
                elem.group_ids.append(group_id)

        return CommandResult(
            success=True,
            message=f"分组了 {len(self.target_ids)} 个元素",
            affected_ids=self.target_ids,
            changes={"group_id": group_id},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cmd": self.type.value,
            "target_ids": self.target_ids,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GroupCommand":
        return cls(
            target_ids=data.get("target_ids", data.get("targets", [])),
        )


# ==================== 对齐命令 ====================


@dataclass
class AlignCommand(Command):
    """对齐命令"""

    type: CommandType = field(default=CommandType.ALIGN)
    target_ids: List[str] = field(default_factory=list)
    alignment: str = "center"  # left, center, right, top, middle, bottom

    def execute(self, model: CanvasModel) -> CommandResult:
        elements = [model.get_element(eid) for eid in self.target_ids]
        elements = [e for e in elements if e]

        if len(elements) < 2:
            return CommandResult(success=False, message="需要至少 2 个元素进行对齐")

        # 计算对齐位置
        if self.alignment in ("left", "center", "right"):
            xs = [e.geometry.x for e in elements]
            widths = [e.geometry.width for e in elements]

            if self.alignment == "left":
                target_x = min(xs)
                for e in elements:
                    e.geometry.x = target_x
            elif self.alignment == "right":
                target_x = max(x + w for x, w in zip(xs, widths))
                for e in elements:
                    e.geometry.x = target_x - e.geometry.width
            else:  # center
                center_x = sum(x + w / 2 for x, w in zip(xs, widths)) / len(elements)
                for e in elements:
                    e.geometry.x = center_x - e.geometry.width / 2

        return CommandResult(
            success=True,
            message=f"对齐了 {len(elements)} 个元素 ({self.alignment})",
            affected_ids=self.target_ids,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cmd": self.type.value,
            "target_ids": self.target_ids,
            "alignment": self.alignment,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AlignCommand":
        return cls(
            target_ids=data.get("target_ids", data.get("targets", [])),
            alignment=data.get("alignment", "center"),
        )


# ==================== 命令解析器 ====================


def parse_commands(data: Union[Dict, List]) -> List[Command]:
    """解析命令列表"""
    if isinstance(data, dict):
        return [Command.from_dict(data)]

    commands = []
    for item in data:
        try:
            cmd = Command.from_dict(item)
            commands.append(cmd)
        except Exception as e:  # pylint: disable=broad-except
            logger.warning("[Commands] 解析命令失败: %s, %s", item, e)

    return commands


# ==================== 命令执行器 ====================


class CommandExecutor:
    """命令执行器"""

    def __init__(self, model: CanvasModel):
        self.model = model
        self.history: List[Command] = []

    def execute(self, command: Command) -> CommandResult:
        """执行单个命令"""
        result = command.execute(self.model)
        if result.success:
            self.history.append(command)
        return result

    def execute_batch(self, commands: List[Command]) -> List[CommandResult]:
        """批量执行命令"""
        results = []
        for cmd in commands:
            result = self.execute(cmd)
            results.append(result)
        return results
