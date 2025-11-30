"""模块名称: observer
主要功能: CRDT 文档观察者，监听图形变更并同步到数据库
"""

from typing import Callable, Dict, Any, Optional
from pycrdt import Doc, Map

from src.logger import get_logger

logger = get_logger(__name__)


class ShapeObserver:
    """图形变更观察者

    监听 Yjs Map 的变更事件，将变更同步到数据库。

    Attributes:
        doc (Doc): pycrdt 文档对象
        shapes_map (Map): 图形数据 Map
        room_id (str): 房间 ID
        on_add (Callable): 添加图形回调
        on_update (Callable): 更新图形回调
        on_delete (Callable): 删除图形回调
    """

    def __init__(
        self,
        doc: Doc,
        room_id: str,
        on_add: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_update: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_delete: Optional[Callable[[str], None]] = None,
    ):
        """初始化观察者

        Args:
            doc: pycrdt 文档对象
            room_id: 房间 ID
            on_add: 添加图形时的回调函数
            on_update: 更新图形时的回调函数
            on_delete: 删除图形时的回调函数
        """
        self.doc = doc
        self.room_id = room_id
        self.shapes_map: Map = doc.get("shapes", type=Map)
        self.on_add = on_add
        self.on_update = on_update
        self.on_delete = on_delete
        self._subscription = None

    def start(self):
        """开始监听变更"""
        def observer(event):
            """处理 Map 变更事件"""
            try:
                for key, change in event.keys.items():
                    action = change.get("action")
                    if action == "add":
                        new_value = self.shapes_map.get(key)
                        if new_value and self.on_add:
                            logger.debug("图形添加: %s", key)
                            self.on_add(
                                key,
                                dict(new_value) if hasattr(new_value, "__iter__") else new_value
                                )
                    elif action == "update":
                        new_value = self.shapes_map.get(key)
                        if new_value and self.on_update:
                            logger.debug("图形更新: %s", key)
                            self.on_update(
                                key,
                                dict(new_value) if hasattr(new_value, "__iter__") else new_value
                                )
                    elif action == "delete":
                        if self.on_delete:
                            logger.debug("图形删除: %s", key)
                            self.on_delete(key)
            except Exception as e:  # pylint: disable=broad-except
                logger.error("处理图形变更失败: %s", e, exc_info=True)

        self._subscription = self.shapes_map.observe(observer)
        logger.info("开始监听房间 %s 的图形变更", self.room_id)

    def stop(self):
        """停止监听变更"""
        if self._subscription is not None:
            self.shapes_map.unobserve(self._subscription)
            self._subscription = None
            logger.info("停止监听房间 %s 的图形变更", self.room_id)

    def get_all_shapes(self) -> Dict[str, Any]:
        """获取所有图形数据

        Returns:
            Dict[str, Any]: 图形 ID -> 图形数据 的映射
        """
        result = {}
        for key in self.shapes_map:
            value = self.shapes_map.get(key)
            if value:
                result[key] = dict(value) if hasattr(value, "__iter__") else value
        return result
