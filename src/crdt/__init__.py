"""包名称: crdt
功能说明: 基于 pycrdt 的 CRDT 同步和观察者功能

该模块提供:
- ShapeObserver: 图形变更观察者，监听并回调变更事件
- 工具函数: 创建、更新、删除、批量操作图形
"""

from .observer import ShapeObserver
from .utils import (
    create_shape_in_doc,
    update_shape_in_doc,
    delete_shape_in_doc,
    batch_create_shapes,
    get_shape_from_doc,
    get_all_shapes_from_doc,
    clear_all_shapes,
)

__all__ = [
    "ShapeObserver",
    "create_shape_in_doc",
    "update_shape_in_doc",
    "delete_shape_in_doc",
    "batch_create_shapes",
    "get_shape_from_doc",
    "get_all_shapes_from_doc",
    "clear_all_shapes",
]
