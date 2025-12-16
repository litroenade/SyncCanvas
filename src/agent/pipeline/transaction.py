"""模块名称: transaction
主要功能: 语义事务层
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from src.agent.pipeline.layout import PositionedOp
from src.agent.pipeline.reasoning import OpType
from src.logger import get_logger

if TYPE_CHECKING:
    from src.agent.base import AgentContext

logger = get_logger(__name__)

@dataclass
class Conflict:
    """冲突记录"""

    type: str  # position_overlap, reference_missing, semantic
    severity: str  # low, medium, high
    affected_op: PositionedOp
    description: str
    auto_fixable: bool = True


@dataclass
class TransactionResult:
    """事务结果"""

    success: bool
    applied_ops: int = 0
    created_ids: List[str] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    error: Optional[str] = None

class SemanticTransaction:
    """语义事务管理器

    Phase 5 核心 - 处理事务提交:
    1. 冲突检测 (位置重叠、引用缺失、语义冲突)
    2. 自动修复 (位置避让、引用更新)
    3. CRDT 原子提交

    使用示例:
        tx = SemanticTransaction()
        result = await tx.commit(positioned_ops, context)
    """

    # 位置重叠阈值
    OVERLAP_THRESHOLD = 20.0

    async def commit(
        self,
        ops: List[PositionedOp],
        context: "AgentContext",
    ) -> TransactionResult:
        """提交操作

        Args:
            ops: 有坐标的操作列表
            context: Agent 上下文

        Returns:
            TransactionResult: 事务结果
        """
        if not ops:
            return TransactionResult(success=True, applied_ops=0)

        ydoc = await context.get_ydoc()
        if not ydoc:
            return TransactionResult(success=False, error="无法获取 Yjs 文档")

        # 1. 冲突检测
        conflicts = self._detect_conflicts(ops, ydoc)

        # 2. 自动修复可修复的冲突
        fixed_ops = ops
        if conflicts:
            fixed_ops, remaining_conflicts = self._resolve_conflicts(
                ops, conflicts, ydoc
            )

            # 如果有无法修复的高严重度冲突,中止事务
            critical = [
                c
                for c in remaining_conflicts
                if c.severity == "high" and not c.auto_fixable
            ]
            if critical:
                return TransactionResult(
                    success=False,
                    conflicts=remaining_conflicts,
                    error=f"存在 {len(critical)} 个无法自动修复的冲突",
                )

        # 3. CRDT 原子提交
        created_ids = []
        try:
            with ydoc.transaction(origin="ai-agent/pipeline"):
                for op in fixed_ops:
                    result_id = self._apply_op(op, ydoc)
                    if result_id:
                        created_ids.append(result_id)

            logger.info(
                "[SemanticTransaction] 提交成功: %d 操作, %d 新元素",
                len(fixed_ops),
                len(created_ids),
            )

            return TransactionResult(
                success=True,
                applied_ops=len(fixed_ops),
                created_ids=created_ids,
                conflicts=conflicts,
            )

        except Exception as e:
            logger.error("[SemanticTransaction] 提交失败: %s", e)
            return TransactionResult(
                success=False,
                error=str(e),
                conflicts=conflicts,
            )

    def _detect_conflicts(self, ops: List[PositionedOp], ydoc: Any) -> List[Conflict]:
        """检测冲突"""
        conflicts = []

        try:
            elements_array = ydoc.get("elements", type="Array")
            existing_elements = list(elements_array)
        except Exception as e:
            logger.warning("[SemanticTransaction] 获取元素列表失败: %s", e)
            existing_elements = []

        existing_by_id = {e.get("id", ""): e for e in existing_elements}

        for op in ops:
            # 检查位置重叠
            if op.type == OpType.ADD_NODE:
                overlaps = self._check_position_overlap(op, existing_elements)
                for overlap in overlaps:
                    conflicts.append(
                        Conflict(
                            type="position_overlap",
                            severity="low",
                            affected_op=op,
                            description=f"与元素 {overlap[:8]} 位置重叠",
                            auto_fixable=True,
                        )
                    )

            # 检查引用缺失
            elif op.type == OpType.CONNECT:
                from_id = op.params.get("from", "")
                to_id = op.params.get("to", "")

                # 检查是否是新创建的节点 (temp_id) 或已存在的元素
                new_ids = {o.real_id for o in ops if o.type == OpType.ADD_NODE}

                if from_id not in existing_by_id and from_id not in new_ids:
                    conflicts.append(
                        Conflict(
                            type="reference_missing",
                            severity="medium",
                            affected_op=op,
                            description=f"源节点 {from_id[:8]} 不存在",
                            auto_fixable=False,
                        )
                    )

                if to_id not in existing_by_id and to_id not in new_ids:
                    conflicts.append(
                        Conflict(
                            type="reference_missing",
                            severity="medium",
                            affected_op=op,
                            description=f"目标节点 {to_id[:8]} 不存在",
                            auto_fixable=False,
                        )
                    )

        return conflicts

    def _check_position_overlap(
        self, op: PositionedOp, existing_elements: List[Dict]
    ) -> List[str]:
        """检查位置是否重叠"""
        overlaps = []

        for elem in existing_elements:
            ex = elem.get("x", 0)
            ey = elem.get("y", 0)
            ew = elem.get("width", 100)
            eh = elem.get("height", 100)

            # 检查矩形重叠
            if (
                op.x < ex + ew + self.OVERLAP_THRESHOLD
                and op.x + op.width + self.OVERLAP_THRESHOLD > ex
                and op.y < ey + eh + self.OVERLAP_THRESHOLD
                and op.y + op.height + self.OVERLAP_THRESHOLD > ey
            ):
                overlaps.append(elem.get("id", "unknown"))

        return overlaps

    def _resolve_conflicts(
        self, ops: List[PositionedOp], conflicts: List[Conflict],
    ) -> tuple[List[PositionedOp], List[Conflict]]:
        """解决冲突"""
        remaining = []
        fixed_ops = list(ops)

        for conflict in conflicts:
            if conflict.type == "position_overlap" and conflict.auto_fixable:
                # 自动位置避让: 向右下方偏移
                op = conflict.affected_op
                op.x += 50
                op.y += 50
                logger.debug("[SemanticTransaction] 自动避让: %s", op.temp_id)
            else:
                remaining.append(conflict)

        return fixed_ops, remaining

    def _apply_op(self, op: PositionedOp, ydoc: Any) -> Optional[str]:
        """应用单个操作到 Yjs 文档"""
        try:
            elements_array = ydoc.get("elements", type="Array")

            if op.type == OpType.ADD_NODE:
                element_id = op.real_id or str(uuid.uuid4())
                node_type = op.params.get("node_type", "rectangle")

                # 创建 Excalidraw 元素
                element = self._create_excalidraw_element(
                    element_id=element_id,
                    elem_type=node_type,
                    x=op.x,
                    y=op.y,
                    width=op.width,
                    height=op.height,
                    label=op.params.get("label", ""),
                )

                elements_array.append(element)

                # 如果有文本,创建绑定的文本元素
                label = op.params.get("label", "")
                if label:
                    text_element = self._create_text_element(
                        container_id=element_id,
                        text=label,
                        x=op.x,
                        y=op.y,
                        width=op.width,
                        height=op.height,
                    )
                    elements_array.append(text_element)

                    # 更新容器绑定
                    for i, elem in enumerate(elements_array):
                        if elem.get("id") == element_id:
                            elem["boundElements"] = [
                                {"id": text_element["id"], "type": "text"}
                            ]
                            break

                return element_id

            elif op.type == OpType.CONNECT:
                arrow_id = str(uuid.uuid4())
                from_id = op.params.get("from", "")
                to_id = op.params.get("to", "")

                arrow = self._create_arrow_element(
                    arrow_id=arrow_id,
                    from_id=from_id,
                    to_id=to_id,
                    label=op.params.get("label", ""),
                )

                elements_array.append(arrow)

                # 更新源和目标元素的 boundElements
                self._update_bound_elements(elements_array, from_id, arrow_id)
                self._update_bound_elements(elements_array, to_id, arrow_id)

                return arrow_id

            elif op.type == OpType.DELETE:
                target_id = op.params.get("target_id", "")
                # 查找并删除
                for i, elem in enumerate(list(elements_array)):
                    if elem.get("id") == target_id:
                        del elements_array[i]
                        return target_id

            return None

        except Exception as e:
            logger.error("[SemanticTransaction] 应用操作失败: %s", e)
            raise  # 不再静默返回 None

    def _create_excalidraw_element(
        self,
        element_id: str,
        elem_type: str,
        x: float,
        y: float,
        width: float,
        height: float,
        label: str = "",
    ) -> Dict[str, Any]:
        """创建 Excalidraw 元素"""

        return {
            "id": element_id,
            "type": elem_type,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "angle": 0,
            "strokeColor": "#1e1e1e",
            "backgroundColor": "#a5d8ff",
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": "solid",
            "roughness": 1,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": {"type": 3} if elem_type == "rectangle" else None,
            "seed": int(time.time() * 1000) % 2147483647,
            "version": 1,
            "versionNonce": int(time.time() * 1000) % 2147483647,
            "isDeleted": False,
            "boundElements": [],
            "updated": int(time.time() * 1000),
            "link": None,
            "locked": False,
        }

    def _create_text_element(
        self,
        container_id: str,
        text: str,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> Dict[str, Any]:
        """创建绑定文本元素"""

        text_id = str(uuid.uuid4())

        return {
            "id": text_id,
            "type": "text",
            "x": x + width / 2,
            "y": y + height / 2,
            "width": width * 0.8,
            "height": 20,
            "angle": 0,
            "strokeColor": "#1e1e1e",
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": "solid",
            "roughness": 1,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": None,
            "seed": int(time.time() * 1000) % 2147483647,
            "version": 1,
            "versionNonce": int(time.time() * 1000) % 2147483647,
            "isDeleted": False,
            "boundElements": None,
            "updated": int(time.time() * 1000),
            "link": None,
            "locked": False,
            "text": text,
            "fontSize": 16,
            "fontFamily": 1,
            "textAlign": "center",
            "verticalAlign": "middle",
            "baseline": 14,
            "containerId": container_id,
            "originalText": text,
            "lineHeight": 1.25,
        }

    def _create_arrow_element(
        self,
        arrow_id: str,
        from_id: str,
        to_id: str,
        label: str = "",
    ) -> Dict[str, Any]:
        """创建箭头元素"""

        return {
            "id": arrow_id,
            "type": "arrow",
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 50,
            "angle": 0,
            "strokeColor": "#1e1e1e",
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": "solid",
            "roughness": 1,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": {"type": 2},
            "seed": int(time.time() * 1000) % 2147483647,
            "version": 1,
            "versionNonce": int(time.time() * 1000) % 2147483647,
            "isDeleted": False,
            "boundElements": [],
            "updated": int(time.time() * 1000),
            "link": None,
            "locked": False,
            "points": [[0, 0], [100, 50]],
            "lastCommittedPoint": None,
            "startBinding": {
                "elementId": from_id,
                "focus": 0,
                "gap": 1,
            }
            if from_id
            else None,
            "endBinding": {
                "elementId": to_id,
                "focus": 0,
                "gap": 1,
            }
            if to_id
            else None,
            "startArrowhead": None,
            "endArrowhead": "arrow",
        }

    def _update_bound_elements(
        self, elements_array: Any, element_id: str, arrow_id: str
    ) -> None:
        """更新元素的 boundElements"""
        for elem in enumerate(elements_array):
            if elem.get("id") == element_id:
                bound = elem.get("boundElements", []) or []
                bound.append({"id": arrow_id, "type": "arrow"})
                elem["boundElements"] = bound
                break

def get_transaction() -> SemanticTransaction:
    """获取语义事务管理器"""
    return SemanticTransaction()
