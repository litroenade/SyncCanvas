"""模块名称: utils
主要功能: CRDT 工具函数，提供文档操作的便捷方法
"""

from typing import Dict, Any, List, Optional
from pycrdt import Doc, Map

from src.logger import get_logger

logger = get_logger(__name__)


def create_shape_in_doc(
    doc: Doc,
    shape_id: str,
    shape_data: Dict[str, Any],
    origin: str = "server"
) -> bool:
    """在文档中创建图形

    Args:
        doc: pycrdt 文档对象
        shape_id: 图形 UUID
        shape_data: 图形数据
        origin: 事务来源标识

    Returns:
        bool: 是否创建成功
    """
    try:
        shapes_map: Map = doc.get("shapes", type=Map)
        with doc.transaction(origin=origin):
            shapes_map[shape_id] = shape_data
        logger.debug("创建图形: %s", shape_id)
        return True
    except Exception as e:  # pylint: disable=broad-except
        logger.error("创建图形失败: %s, 错误: %s", shape_id, e)
        return False


def update_shape_in_doc(
    doc: Doc,
    shape_id: str,
    updates: Dict[str, Any],
    origin: str = "server"
) -> bool:
    """在文档中更新图形

    Args:
        doc: pycrdt 文档对象
        shape_id: 图形 UUID
        updates: 要更新的属性
        origin: 事务来源标识

    Returns:
        bool: 是否更新成功
    """
    try:
        shapes_map: Map = doc.get("shapes", type=Map)
        current = shapes_map.get(shape_id)
        if current is None:
            logger.warning("更新图形失败: %s 不存在", shape_id)
            return False

        # 合并更新
        current_dict = dict(current) if hasattr(current, "__iter__") else {}
        current_dict.update(updates)

        with doc.transaction(origin=origin):
            shapes_map[shape_id] = current_dict
        logger.debug("更新图形: %s", shape_id)
        return True
    except Exception as e:  # pylint: disable=broad-except
        logger.error("更新图形失败: %s, 错误: %s", shape_id, e)
        return False


def delete_shape_in_doc(
    doc: Doc,
    shape_id: str,
    origin: str = "server"
) -> bool:
    """在文档中删除图形

    Args:
        doc: pycrdt 文档对象
        shape_id: 图形 UUID
        origin: 事务来源标识

    Returns:
        bool: 是否删除成功
    """
    try:
        shapes_map: Map = doc.get("shapes", type=Map)
        if shape_id not in shapes_map:
            logger.warning("删除图形失败: %s 不存在", shape_id)
            return False

        with doc.transaction(origin=origin):
            del shapes_map[shape_id]
        logger.debug("删除图形: %s", shape_id)
        return True
    except Exception as e:  # pylint: disable=broad-except
        logger.error("删除图形失败: %s, 错误: %s", shape_id, e)
        return False


def batch_create_shapes(
    doc: Doc,
    shapes: List[Dict[str, Any]],
    origin: str = "server"
) -> int:
    """批量创建图形

    Args:
        doc: pycrdt 文档对象
        shapes: 图形数据列表，每个必须包含 'id' 字段
        origin: 事务来源标识

    Returns:
        int: 成功创建的图形数量
    """
    try:
        shapes_map: Map = doc.get("shapes", type=Map)
        count = 0
        with doc.transaction(origin=origin):
            for shape in shapes:
                shape_id = shape.get("id")
                if shape_id:
                    shapes_map[shape_id] = shape
                    count += 1
        logger.info("批量创建 %d 个图形", count)
        return count
    except Exception as e:  # pylint: disable=broad-except
        logger.error("批量创建图形失败: %s", e)
        return 0


def get_shape_from_doc(doc: Doc, shape_id: str) -> Optional[Dict[str, Any]]:
    """从文档获取图形数据

    Args:
        doc: pycrdt 文档对象
        shape_id: 图形 UUID

    Returns:
        Optional[Dict[str, Any]]: 图形数据，不存在返回 None
    """
    try:
        shapes_map: Map = doc.get("shapes", type=Map)
        value = shapes_map.get(shape_id)
        if value is None:
            return None
        return dict(value) if hasattr(value, "__iter__") else value
    except Exception as e:  # pylint: disable=broad-except
        logger.error("获取图形失败: %s, 错误: %s", shape_id, e)
        return None


def get_all_shapes_from_doc(doc: Doc) -> Dict[str, Any]:
    """从文档获取所有图形

    Args:
        doc: pycrdt 文档对象

    Returns:
        Dict[str, Any]: 图形 ID -> 图形数据 的映射
    """
    try:
        shapes_map: Map = doc.get("shapes", type=Map)
        result = {}
        for key in shapes_map:
            value = shapes_map.get(key)
            if value:
                result[key] = dict(value) if hasattr(value, "__iter__") else value
        return result
    except Exception as e:  # pylint: disable=broad-except
        logger.error("获取所有图形失败: %s", e)
        return {}


def clear_all_shapes(doc: Doc, origin: str = "server") -> int:
    """清空文档中所有图形

    Args:
        doc: pycrdt 文档对象
        origin: 事务来源标识

    Returns:
        int: 删除的图形数量
    """
    try:
        shapes_map: Map = doc.get("shapes", type=Map)
        keys = list(shapes_map.keys())
        count = len(keys)
        with doc.transaction(origin=origin):
            for key in keys:
                del shapes_map[key]
        logger.info("清空 %d 个图形", count)
        return count
    except Exception as e:  # pylint: disable=broad-except
        logger.error("清空图形失败: %s", e)
        return 0
