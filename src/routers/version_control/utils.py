"""模块名称: utils
主要功能: iGit 版本控制系统的工具函数
"""

import hashlib
from typing import Tuple, List
from pycrdt import Doc, Map, Array
from src.logger import get_logger
from .models import ElementChange

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
    """解析 Yjs 数据中的 Excalidraw 元素信息
    
    支持两种格式：
    1. Excalidraw 格式：elements Y.Array
    2. 旧格式：shapes Y.Map (兼容)
    
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

        # 优先尝试 Excalidraw elements Array 格式
        try:
            elements_array = ydoc.get("elements", type=Array)
            if elements_array is not None and len(elements_array) > 0:
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

                if result:
                    return result
        except Exception as e:  # pylint: disable=broad-except
            logger.debug("解析 elements Array 失败: %s", e)

        # 回退到旧的 shapes Map 格式
        try:
            shapes_map = ydoc.get("shapes", type=Map)
            if shapes_map is not None:
                shapes_dict = shapes_map.to_py()
                if isinstance(shapes_dict, dict):
                    for shape_id, stroke_data in shapes_dict.items():
                        if isinstance(stroke_data, dict):
                            result[shape_id] = stroke_data
                        else:
                            result[shape_id] = {"raw": str(stroke_data)}
        except Exception as e:  # pylint: disable=broad-except
            logger.debug("解析 shapes Map 失败: %s", e)

        return result
    except Exception as e:  # pylint: disable=broad-except
        logger.warning("解析 Yjs 数据失败: %s", e)
        return {}


# 别名，保持向后兼容
def parse_yjs_strokes(data: bytes) -> dict:
    """解析 Yjs 数据中的元素信息 (别名函数，保持兼容)"""
    return parse_yjs_elements(data)


def compute_elements_diff(
    old_elements: dict,
    new_elements: dict
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
        changes.append(ElementChange(
            element_id=el_id,
            action="added",
            element_type=element.get("type") if isinstance(element, dict) else None,
            text=element.get("text") if isinstance(element, dict) else None
        ))

    for el_id in removed_ids:
        element = old_elements.get(el_id, {})
        changes.append(ElementChange(
            element_id=el_id,
            action="removed",
            element_type=element.get("type") if isinstance(element, dict) else None,
            text=element.get("text") if isinstance(element, dict) else None
        ))

    for el_id in modified_ids:
        element = new_elements.get(el_id, {})
        changes.append(ElementChange(
            element_id=el_id,
            action="modified",
            element_type=element.get("type") if isinstance(element, dict) else None,
            text=element.get("text") if isinstance(element, dict) else None
        ))

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
        "isDeleted"
        ]
    for field in key_fields:
        if old.get(field) != new.get(field):
            return True

    # 检查版本号（如果存在）
    if old.get("version") != new.get("version"):
        return True

    return False


# 别名，保持向后兼容
def compute_strokes_diff(old_strokes: dict, new_strokes: dict):
    """计算元素差异 (别名函数，保持兼容)"""
    return compute_elements_diff(old_strokes, new_strokes)
