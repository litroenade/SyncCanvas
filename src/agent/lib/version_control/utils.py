"""
版本控制工具函数
"""

import hashlib
from typing import Tuple, List
from pycrdt import Doc, Map, Array
from src.logger import get_logger
from src.agent.lib.version_control.models import ElementChange

logger = get_logger(__name__)


def generate_commit_hash(commit_id: int, timestamp: int) -> str:
    """生成提交哈希

    Args:
        commit_id: 提交 ID
        timestamp: 时间戳

    Returns:
        7 位短哈希
    """
    data = f"{commit_id}-{timestamp}"
    full_hash = hashlib.sha1(data.encode()).hexdigest()
    return full_hash[:7]


def parse_yjs_elements(data: bytes) -> dict:
    """解析 Yjs 数据中的 Excalidraw 元素

    Args:
        data: Yjs 文档的二进制数据

    Returns:
        dict: element_id -> element_data 的映射
    """
    if not data:
        return {}

    try:
        ydoc = Doc()
        ydoc.apply_update(data)

        result = {}
        elements_array = ydoc.get("elements", type=Array)

        if elements_array is not None:
            for el in elements_array:
                if isinstance(el, Map):
                    el_dict = dict(el)
                elif isinstance(el, dict):
                    el_dict = el
                else:
                    continue

                el_id = el_dict.get("id")
                if el_id:
                    result[el_id] = el_dict

        return result
    except Exception as e:  # pylint: disable=broad-except
        logger.warning("解析 Yjs 数据失败: %s", e)
        return {}


def compute_elements_diff(
    old_elements: dict, new_elements: dict
) -> Tuple[int, int, int, List[ElementChange]]:
    """计算两个元素集合之间的差异

    Args:
        old_elements: 旧的元素映射 (element_id -> element_data)
        new_elements: 新的元素映射

    Returns:
        (added, removed, modified, changes) 元组
    """
    old_ids = set(old_elements.keys())
    new_ids = set(new_elements.keys())

    added_ids = new_ids - old_ids
    removed_ids = old_ids - new_ids
    common_ids = old_ids & new_ids

    modified_ids = set()
    for el_id in common_ids:
        old_data = old_elements.get(el_id, {})
        new_data = new_elements.get(el_id, {})
        # 比较关键字段：位置、大小、内容等
        if _element_changed(old_data, new_data):
            modified_ids.add(el_id)

    changes = []

    for el_id in added_ids:
        element = new_elements.get(el_id, {})
        changes.append(
            ElementChange(
                element_id=el_id,
                action="added",
                element_type=element.get("type") if isinstance(element, dict) else None,
                text=element.get("text") if isinstance(element, dict) else None,
            )
        )

    for el_id in removed_ids:
        element = old_elements.get(el_id, {})
        changes.append(
            ElementChange(
                element_id=el_id,
                action="removed",
                element_type=element.get("type") if isinstance(element, dict) else None,
                text=element.get("text") if isinstance(element, dict) else None,
            )
        )

    for el_id in modified_ids:
        element = new_elements.get(el_id, {})
        changes.append(
            ElementChange(
                element_id=el_id,
                action="modified",
                element_type=element.get("type") if isinstance(element, dict) else None,
                text=element.get("text") if isinstance(element, dict) else None,
            )
        )

    return len(added_ids), len(removed_ids), len(modified_ids), changes


def _element_changed(old: dict, new: dict) -> bool:
    """检查元素是否有实质性变化"""
    if not isinstance(old, dict) or not isinstance(new, dict):
        return str(old) != str(new)

    # 检查关键字段
    key_fields = [
        "x",
        "y",
        "width",
        "height",
        "text",
        "strokeColor",
        "backgroundColor",
        "isDeleted",
    ]
    for field in key_fields:
        if old.get(field) != new.get(field):
            return True

    if old.get("version") != new.get("version"):
        return True

    return False
