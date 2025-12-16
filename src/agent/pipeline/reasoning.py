"""模块名称: reasoning
主要功能: Agent 推理层
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from src.agent.pipeline.cognition import CanvasState, get_cognition
from src.agent.canvas import CanvasModel
from src.agent.canvas.commands import (
    Command,
    MoveCommand,
    ConnectCommand,
    CreateCommand,
    UpdateCommand,
    DeleteCommand,
)
from src.agent.errors import parse_json_safe
from src.config import ModelConfig
from src.logger import get_logger
from src.agent.prompts.controller import ControllerPrompt

if TYPE_CHECKING:
    from src.agent.llm import LLMClient

logger = get_logger(__name__)


class ReasoningMode(Enum):
    """推理模式"""

    CONTROL = "control"  # 控制已有元素
    CREATE = "create"  # 创建新元素
    HYBRID = "hybrid"  # 混合模式 (默认)

class OpType(Enum):
    """操作类型 (兼容旧版)"""

    ADD_NODE = "add_node"
    CONNECT = "connect"
    DELETE = "delete"
    UPDATE = "update"
    CLEAR = "clear"


@dataclass
class LogicalOp:
    """纯逻辑操作 (兼容旧版)"""

    type: OpType
    temp_id: str = ""
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type.value, "id": self.temp_id, **self.params}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogicalOp":
        op_type_str = data.get("type", "add_node")
        try:
            op_type = OpType(op_type_str)
        except ValueError:
            op_type = OpType.ADD_NODE
        temp_id = data.get("id", data.get("temp_id", ""))
        params = {k: v for k, v in data.items() if k not in ("type", "id", "temp_id")}
        return cls(type=op_type, temp_id=temp_id, params=params)

@dataclass
class ReasoningResult:
    """推理结果"""

    # 控制命令 (新模式)
    commands: List[Command] = field(default_factory=list)

    # 逻辑操作 (兼容旧模式)
    operations: List[LogicalOp] = field(default_factory=list)

    thought: str = ""  # LLM 的思考过程
    raw_response: str = ""
    mode: ReasoningMode = ReasoningMode.HYBRID
    success: bool = True
    error: Optional[str] = None

class CanvasReasoner:
    """画布推理器

    支持控制和创建两种模式:
    - 控制模式: 操作已有元素
    - 创建模式: 生成新元素
    - 混合模式: 自动判断
    """

    def __init__(self, llm_client: "LLMClient"):
        self.llm = llm_client
        self.cognition = get_cognition()

    async def reason(
        self,
        user_input: str,
        canvas_state: CanvasState,
        canvas_model: Optional[CanvasModel] = None,
        model: Optional[ModelConfig] = None,
        temperature: float = 0.2,
        mode: ReasoningMode = ReasoningMode.HYBRID,
    ) -> ReasoningResult:
        """执行推理

        Args:
            user_input: 用户输入
            canvas_state: 画布状态摘要
            canvas_model: 画布模型 (包含详细元素)
            model: 模型配置
            temperature: LLM 温度
            mode: 推理模式

        Returns:
            ReasoningResult: 推理结果
        """
        # 构建系统提示词
        system_prompt = self._build_prompt(canvas_state, canvas_model)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        try:
            response = await self.llm.chat_completion(
                messages=messages,
                tools=None,
                temperature=temperature,
            )

            raw_content = response.content or ""

            # 解析响应
            commands, thought = self._parse_response(raw_content, canvas_model)

            # 转换为旧版 LogicalOp (兼容)
            operations = self._commands_to_operations(commands)

            return ReasoningResult(
                commands=commands,
                operations=operations,
                thought=thought,
                raw_response=raw_content,
                mode=mode,
                success=True,
            )

        except Exception as e:  # pylint: disable=broad-except
            logger.error("[CanvasReasoner] 推理失败: %s", e)
            return ReasoningResult(success=False, error=str(e))

    def _build_prompt(
        self, canvas_state: CanvasState, canvas_model: Optional[CanvasModel]
    ) -> str:
        """构建系统提示词"""
        # 画布摘要
        canvas_summary = canvas_state.summary if canvas_state else "画布为空"

        # 元素列表
        element_list = "无元素"
        if canvas_model and not canvas_model.is_empty:
            elements = []
            for elem in list(canvas_model.elements.values())[:20]:  # 限制数量
                desc = f"- `{elem.id[:8]}...` [{elem.type.value}]"
                if elem.value:
                    desc += f' "{elem.value[:20]}"'
                desc += f" 位置:({elem.geometry.x:.0f},{elem.geometry.y:.0f})"
                elements.append(desc)
            element_list = "\n".join(elements)

        return ControllerPrompt(
            canvas_summary=canvas_summary,
            element_list=element_list,
        ).render()

    def _parse_response(
        self, content: str, canvas_model: Optional[CanvasModel]
    ) -> tuple[List[Command], str]:
        """解析 LLM 响应"""
        commands: List[Command] = []
        thought = ""

        try:
            # 提取 JSON
            json_match = None
            json_block = re.search(r"```json\s*([\s\S]*?)\s*```", content)
            if json_block:
                json_match = json_block.group(1)
            else:
                json_match = content

            data = parse_json_safe(json_match)

            if isinstance(data, dict):
                thought = data.get("thought", "")
                cmds_data = data.get("commands", [])

                for cmd_data in cmds_data:
                    if isinstance(cmd_data, dict):
                        try:
                            # 解析命令
                            cmd = self._parse_command(cmd_data, canvas_model)
                            if cmd:
                                commands.append(cmd)
                        except Exception as e:  # pylint: disable=broad-except
                            logger.warning("[CanvasReasoner] 解析命令失败: %s", e)

        except Exception as e:  # pylint: disable=broad-except
            logger.warning("[CanvasReasoner] JSON 解析失败: %s", e)
            thought = content[:500]

        return commands, thought

    def _parse_command(
        self, data: Dict[str, Any], canvas_model: Optional[CanvasModel]
    ) -> Optional[Command]:
        """解析单个命令"""
        cmd_type = data.get("cmd", data.get("type", ""))

        # 处理 by_text 选择
        if cmd_type == "select" and data.get("by_text") and canvas_model:
            # 根据文本查找元素
            text = data["by_text"]
            found = canvas_model.find_by_text(text)
            if found:
                data["target_ids"] = [e.id for e in found]

        # 处理 move 命令的 target_ids
        if cmd_type == "move" and not data.get("target_ids"):
            # 如果没有 target_ids,使用当前选择
            if canvas_model and canvas_model.selection:
                data["target_ids"] = [e.id for e in canvas_model.selection]

        try:
            return Command.from_dict(data)
        except ValueError:
            return None

    def _commands_to_operations(self, commands: List[Command]) -> List[LogicalOp]:
        """将命令转换为旧版 LogicalOp (兼容)"""
        operations = []

        for cmd in commands:
            if isinstance(cmd, CreateCommand):
                operations.append(
                    LogicalOp(
                        type=OpType.ADD_NODE,
                        temp_id="",
                        params={
                            "label": cmd.value,
                            "node_type": cmd.element_type,
                        },
                    )
                )
            elif isinstance(cmd, ConnectCommand):
                operations.append(
                    LogicalOp(
                        type=OpType.CONNECT,
                        params={
                            "from": cmd.from_id,
                            "to": cmd.to_id,
                            "label": cmd.label,
                        },
                    )
                )
            elif isinstance(cmd, DeleteCommand):
                for tid in cmd.target_ids:
                    operations.append(
                        LogicalOp(type=OpType.DELETE, params={"target_id": tid})
                    )
            elif isinstance(cmd, UpdateCommand):
                for tid in cmd.target_ids:
                    operations.append(
                        LogicalOp(
                            type=OpType.UPDATE,
                            params={"target_id": tid, **cmd.properties},
                        )
                    )

        return operations

    def validate_commands(self, commands: List[Command]) -> List[str]:
        """验证命令序列"""
        errors = []

        for cmd in commands:
            if isinstance(cmd, MoveCommand):
                if not cmd.target_ids:
                    errors.append("move 命令缺少 target_ids")
            elif isinstance(cmd, ConnectCommand):
                if not cmd.from_id or not cmd.to_id:
                    errors.append("connect 命令缺少 from_id 或 to_id")

        return errors

LogicalReasoner = CanvasReasoner
