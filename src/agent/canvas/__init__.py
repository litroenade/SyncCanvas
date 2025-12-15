"""包名称: canvas
功能说明: 画布模型和控制命令

提供画布元素的数据结构和操作命令:
- model: 元素模型 (类似 mxCell)
- commands: 控制命令 (select, move, resize 等)
"""

from src.agent.canvas.model import (
    CanvasModel,
    CanvasElement,
    ElementType,
    Geometry,
    Style,
    Binding,
    create_element,
)
from src.agent.canvas.commands import (
    Command,
    CommandType,
    CommandResult,
    CommandExecutor,
    SelectCommand,
    MoveCommand,
    ResizeCommand,
    ConnectCommand,
    UpdateCommand,
    DeleteCommand,
    CreateCommand,
    GroupCommand,
    AlignCommand,
    DeselectCommand,
    parse_commands,
)

__all__ = [
    # model
    "CanvasModel",
    "CanvasElement",
    "ElementType",
    "Geometry",
    "Style",
    "Binding",
    "create_element",
    # commands
    "Command",
    "CommandType",
    "CommandResult",
    "CommandExecutor",
    "SelectCommand",
    "DeselectCommand",
    "MoveCommand",
    "ResizeCommand",
    "ConnectCommand",
    "UpdateCommand",
    "DeleteCommand",
    "CreateCommand",
    "GroupCommand",
    "AlignCommand",
    "parse_commands",
]
