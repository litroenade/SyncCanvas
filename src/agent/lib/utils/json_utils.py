"""
JSON 处理工具
"""

import json
from typing import Any, Optional


def safe_json_loads(text: str, default: Any = None) -> Any:
    """安全解析 JSON 字符串

    Args:
        text: JSON 字符串
        default: 解析失败时的默认值

    Returns:
        解析结果或默认值
    """
    if not text:
        return default
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """安全序列化为 JSON 字符串

    Args:
        obj: 要序列化的对象
        default: 序列化失败时的默认值

    Returns:
        JSON 字符串
    """
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return default


def extract_json_from_text(text: str) -> Optional[dict]:
    """从文本中提取 JSON 对象 (处理 LLM 输出)

    LLM 有时会在 JSON 前后加入额外文字，此函数尝试提取有效的 JSON。

    Args:
        text: 包含 JSON 的文本

    Returns:
        提取的 JSON 对象，失败返回 None
    """
    if not text:
        return None

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 查找 JSON 对象边界
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    # 查找 JSON 数组边界
    start = text.find("[")
    end = text.rfind("]")

    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None
