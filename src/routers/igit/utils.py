"""模块名称: utils
主要功能: iGit 版本控制系统的工具函数
"""

import hashlib
from typing import Tuple, List
from pycrdt import Doc, Map
from src.logger import get_logger
from .models import StrokeChange

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


def parse_yjs_strokes(data: bytes) -> dict:
    """解析 Yjs 数据中的笔画信息
    
    Args:
        data: Yjs 文档的二进制数据
        
    Returns:
        dict: shape_id -> stroke_data 的映射
    """
    if not data:
        return {}

    try:
        ydoc = Doc()
        ydoc.apply_update(data)

        shapes_map = ydoc.get("shapes", type=Map)

        if shapes_map is None:
            return {}

        result = {}
        # pycrdt Map 转换为 dict
        try:
            # 使用 to_py() 方法转换
            shapes_dict = shapes_map.to_py()
            if isinstance(shapes_dict, dict):
                for shape_id, stroke_data in shapes_dict.items():
                    if isinstance(stroke_data, dict):
                        result[shape_id] = stroke_data
                    else:
                        result[shape_id] = {"raw": str(stroke_data)}
        except Exception:
            # 备用方法：迭代
            try:
                for key in shapes_map:
                    result[key] = shapes_map[key]
            except Exception:
                pass

        return result
    except Exception as e:
        logger.warning(f"解析 Yjs 数据失败: {e}")
        return {}


def compute_strokes_diff(
    old_strokes: dict,
    new_strokes: dict
) -> Tuple[int, int, int, List[StrokeChange]]:
    """计算两个笔画集合之间的差异
    
    Args:
        old_strokes: 旧的笔画映射
        new_strokes: 新的笔画映射
        
    Returns:
        (added, removed, modified, changes) 元组
    """
    old_ids = set(old_strokes.keys())
    new_ids = set(new_strokes.keys())

    added_ids = new_ids - old_ids
    removed_ids = old_ids - new_ids
    common_ids = old_ids & new_ids

    modified_ids = set()
    for shape_id in common_ids:
        old_data = old_strokes.get(shape_id, {})
        new_data = new_strokes.get(shape_id, {})
        # 简单比较：如果数据不同则认为被修改
        if str(old_data) != str(new_data):
            modified_ids.add(shape_id)

    changes = []

    for shape_id in added_ids:
        stroke = new_strokes.get(shape_id, {})
        changes.append(StrokeChange(
            shape_id=shape_id,
            action="added",
            stroke_type=stroke.get("type") if isinstance(stroke, dict) else None,
            points_count=len(stroke.get("points", [])) if isinstance(stroke, dict) else None
        ))

    for shape_id in removed_ids:
        stroke = old_strokes.get(shape_id, {})
        changes.append(StrokeChange(
            shape_id=shape_id,
            action="removed",
            stroke_type=stroke.get("type") if isinstance(stroke, dict) else None,
            points_count=len(stroke.get("points", [])) if isinstance(stroke, dict) else None
        ))

    for shape_id in modified_ids:
        stroke = new_strokes.get(shape_id, {})
        changes.append(StrokeChange(
            shape_id=shape_id,
            action="modified",
            stroke_type=stroke.get("type") if isinstance(stroke, dict) else None,
            points_count=len(stroke.get("points", [])) if isinstance(stroke, dict) else None
        ))

    return len(added_ids), len(removed_ids), len(modified_ids), changes
