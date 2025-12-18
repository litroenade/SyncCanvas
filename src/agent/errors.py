"""模块名称: errors
主要功能: Agent 模块异常定义和工具函数
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from json_repair import repair_json

from src.logger import get_logger

logger = get_logger(__name__)


class AIEngineError(Exception):
    """AI Engine 基础异常类

    Attributes:
        message: 错误消息
        details: 详细信息
        cause: 原始异常
        is_retryable: 是否可重试
        user_message: 用户可见消息
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        is_retryable: bool = False,
        user_message: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause
        self.is_retryable = is_retryable
        self.user_message = user_message or message

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r})"


class LLMError(AIEngineError):
    """LLM 调用异常

    Attributes:
        provider: LLM 提供商
        model: 模型名称
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.pop("details", {})
        if provider:
            details["provider"] = provider
        if model:
            details["model"] = model
        super().__init__(message, details=details, **kwargs)
        self.provider = provider
        self.model = model


class ToolError(AIEngineError):
    """工具执行异常

    Attributes:
        tool_name: 工具名称
        tool_args: 调用参数
    """

    def __init__(
        self,
        message: str,
        tool_name: str,
        tool_args: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        details = kwargs.pop("details", {})
        details["tool_name"] = tool_name
        if tool_args:
            details["args"] = {k: str(v)[:100] for k, v in tool_args.items()}
        super().__init__(message, details=details, **kwargs)
        self.tool_name = tool_name
        self.tool_args = tool_args


class AgentError(AIEngineError):
    """Agent 执行异常

    Attributes:
        agent_name: Agent 名称
        run_id: 运行记录 ID
    """

    def __init__(
        self,
        message: str,
        agent_name: str,
        run_id: Optional[int] = None,
        **kwargs,
    ):
        details = kwargs.pop("details", {})
        details["agent_name"] = agent_name
        if run_id is not None:
            details["run_id"] = run_id
        super().__init__(message, details=details, **kwargs)
        self.agent_name = agent_name
        self.run_id = run_id


class TransactionError(AIEngineError):
    """事务提交异常 (CRDT 操作失败)

    Attributes:
        operation: 失败的操作类型
        affected_ids: 受影响的元素 ID
    """

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        affected_ids: Optional[list] = None,
        **kwargs,
    ):
        # 事务冲突通常可重试
        kwargs.setdefault("is_retryable", True)
        kwargs.setdefault("user_message", "操作冲突，请稍后重试")
        details = kwargs.pop("details", {})
        if operation:
            details["operation"] = operation
        if affected_ids:
            details["affected_ids"] = affected_ids
        super().__init__(message, details=details, **kwargs)
        self.operation = operation
        self.affected_ids = affected_ids or []


def extract_json_from_text(text: str) -> Optional[str]:
    """从文本中提取 JSON 块"""
    if not text:
        return None

    # 尝试提取 markdown 代码块
    code_block_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
    matches = re.findall(code_block_pattern, text, re.IGNORECASE)
    if matches:
        return max(matches, key=len).strip()

    # 尝试提取 JSON 对象
    obj_pattern = r"\{[\s\S]*\}"
    obj_matches = re.findall(obj_pattern, text)
    if obj_matches:
        return max(obj_matches, key=len).strip()

    # 尝试提取 JSON 数组
    arr_pattern = r"\[[\s\S]*\]"
    arr_matches = re.findall(arr_pattern, text)
    if arr_matches:
        return max(arr_matches, key=len).strip()

    return None


def parse_json_safe(text: str, default: Any = None) -> Any:
    """安全解析 JSON (带 json_repair 容错)"""
    if not text:
        return default

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    try:
        repaired = repair_json(text, return_objects=True)
        return repaired
    except Exception as e:  # pylint: disable=broad-except
        logger.warning("JSON 修复失败: %s", e)
        return default


def parse_tool_call_args(args_str: str) -> Dict[str, Any]:
    """解析工具调用参数"""
    if not args_str:
        return {}

    parsed = parse_json_safe(args_str, default={})
    return parsed if isinstance(parsed, dict) else {}
