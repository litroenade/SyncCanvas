"""模块名称: json_parser
主要功能: LLM 响应 JSON 解析与修复

使用 json_repair 库处理 LLM 返回的不规范 JSON，
支持修复常见问题如：
- 尾随逗号
- 单引号
- 未转义字符
- 缺失引号
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from json_repair import repair_json

from src.logger import get_logger

logger = get_logger(__name__)


# ==================== JSON 提取 ====================


def extract_json_from_text(text: str) -> Optional[str]:
    """从文本中提取 JSON 块

    支持提取:
    - ```json ... ``` 代码块
    - { ... } 对象
    - [ ... ] 数组

    Args:
        text: 包含 JSON 的文本

    Returns:
        提取的 JSON 字符串，无法提取则返回 None
    """
    if not text:
        return None

    # 1. 尝试提取 markdown 代码块
    code_block_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
    matches = re.findall(code_block_pattern, text, re.IGNORECASE)
    if matches:
        # 返回最长的匹配（通常是主要内容）
        return max(matches, key=len).strip()

    # 2. 尝试提取 JSON 对象
    obj_pattern = r"\{[\s\S]*\}"
    obj_matches = re.findall(obj_pattern, text)
    if obj_matches:
        return max(obj_matches, key=len).strip()

    # 3. 尝试提取 JSON 数组
    arr_pattern = r"\[[\s\S]*\]"
    arr_matches = re.findall(arr_pattern, text)
    if arr_matches:
        return max(arr_matches, key=len).strip()

    return None


# ==================== JSON 解析 ====================


def parse_json_safe(text: str, default: Any = None) -> Any:
    """安全解析 JSON (带 json_repair 容错)

    Args:
        text: JSON 字符串
        default: 解析失败时的默认值

    Returns:
        解析结果，失败返回 default
    """
    if not text:
        return default

    try:
        # 先尝试标准解析
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    try:
        # 使用 json_repair 修复
        repaired = repair_json(text, return_objects=True)
        return repaired
    except Exception as e:
        logger.warning(f"JSON 修复失败: {e}")
        return default


def parse_llm_response(text: str) -> Dict[str, Any]:
    """解析 LLM 返回的响应

    尝试从 LLM 响应中提取结构化数据。

    Args:
        text: LLM 响应文本

    Returns:
        解析后的字典，始终包含:
        - type: "json" | "text"
        - content: 原始内容或解析结果
    """
    if not text:
        return {"type": "text", "content": ""}

    # 尝试提取 JSON
    json_str = extract_json_from_text(text)

    if json_str:
        parsed = parse_json_safe(json_str)
        if parsed is not None:
            return {"type": "json", "content": parsed, "raw": text}

    # 如果整个文本就是 JSON
    parsed = parse_json_safe(text)
    if parsed is not None and isinstance(parsed, (dict, list)):
        return {"type": "json", "content": parsed, "raw": text}

    # 无法解析为 JSON，返回文本
    return {"type": "text", "content": text}


# ==================== 响应类型判断 ====================


def is_action_response(parsed: Dict[str, Any]) -> bool:
    """判断是否为 action 响应

    Action 响应格式:
    {
        "thinking": "...",
        "actions": [{"tool": "xxx", "args": {...}}],
        "summary": "..."
    }
    """
    if parsed.get("type") != "json":
        return False

    content = parsed.get("content", {})
    if not isinstance(content, dict):
        return False

    return "actions" in content or "plan" in content


def extract_actions(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从解析结果中提取 actions

    Args:
        parsed: parse_llm_response 的返回值

    Returns:
        action 列表，每个 action 包含 tool 和 args
    """
    if parsed.get("type") != "json":
        return []

    content = parsed.get("content", {})
    if not isinstance(content, dict):
        return []

    # 支持 actions 或 plan 字段
    actions = content.get("actions") or content.get("plan") or []

    if not isinstance(actions, list):
        return []

    # 规范化 action 格式
    normalized = []
    for action in actions:
        if isinstance(action, dict):
            tool = action.get("tool") or action.get("action") or action.get("name")
            args = (
                action.get("args")
                or action.get("arguments")
                or action.get("params")
                or {}
            )

            if tool:
                normalized.append(
                    {"tool": tool, "args": args if isinstance(args, dict) else {}}
                )

    return normalized


# ==================== 工具调用解析 ====================


def parse_tool_call_args(args_str: str) -> Dict[str, Any]:
    """解析工具调用参数

    LLM 返回的工具调用参数可能格式不规范，使用 json_repair 修复。

    Args:
        args_str: 参数 JSON 字符串

    Returns:
        解析后的参数字典
    """
    if not args_str:
        return {}

    parsed = parse_json_safe(args_str, default={})
    return parsed if isinstance(parsed, dict) else {}
