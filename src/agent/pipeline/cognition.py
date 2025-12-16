"""模块名称: cognition
主要功能: 增量图认知 (Graph Cognition)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from src.logger import get_logger

if TYPE_CHECKING:
    from src.agent.base import AgentContext

logger = get_logger(__name__)

@dataclass
class ElementInfo:
    """元素信息摘要"""

    id: str
    type: str
    label: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    @classmethod
    def from_element(cls, elem: Dict[str, Any]) -> "ElementInfo":
        """从 Excalidraw 元素创建"""
        return cls(
            id=elem.get("id", ""),
            type=elem.get("type", "unknown"),
            label=elem.get("text", elem.get("originalText", "")),
            x=elem.get("x", 0.0),
            y=elem.get("y", 0.0),
            width=elem.get("width", 0.0),
            height=elem.get("height", 0.0),
        )

    def center(self) -> tuple[float, float]:
        """元素中心点"""
        return (self.x + self.width / 2, self.y + self.height / 2)


@dataclass
class CanvasBounds:
    """画布边界信息"""

    min_x: float = 0.0
    min_y: float = 0.0
    max_x: float = 0.0
    max_y: float = 0.0
    suggested_x: float = 100.0
    suggested_y: float = 100.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "min_x": self.min_x,
            "min_y": self.min_y,
            "max_x": self.max_x,
            "max_y": self.max_y,
            "suggested_x": self.suggested_x,
            "suggested_y": self.suggested_y,
        }


@dataclass
class CanvasState:
    """画布状态快照

    用于 Pipeline Phase 1 的状态水合。
    """

    elements: List[ElementInfo] = field(default_factory=list)
    connections: List[Dict[str, str]] = field(default_factory=list)
    bounds: CanvasBounds = field(default_factory=CanvasBounds)
    summary: str = ""
    delta_summary: str = ""
    timestamp: float = 0.0

    @property
    def element_count(self) -> int:
        return len(self.elements)

    @property
    def is_empty(self) -> bool:
        return len(self.elements) == 0

    def get_element_by_id(self, element_id: str) -> Optional[ElementInfo]:
        """根据 ID 查找元素"""
        for elem in self.elements:
            if elem.id == element_id:
                return elem
        return None

    def get_elements_by_type(self, elem_type: str) -> List[ElementInfo]:
        """根据类型筛选元素"""
        return [e for e in self.elements if e.type == elem_type]


@dataclass
class DeltaChange:
    """变更记录"""

    added: List[ElementInfo] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)  # 存储 ID
    modified: List[tuple[str, str]] = field(default_factory=list)  # (ID, 变更描述)

class GraphCognition:
    """增量图认知引擎

    Phase 1 核心组件 - 管理画布状态认知:
    1. 解析画布文档
    2. 生成结构化摘要
    3. 计算增量变更
    4. 注入到 Prompt

    使用示例:
        cognition = GraphCognition()
        state = await cognition.hydrate(context)
        prompt = cognition.inject_to_prompt(system_prompt, state)
    """

    # 单例
    _instance: Optional["GraphCognition"] = None
    _initialized: bool = False

    def __new__(cls) -> "GraphCognition":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._last_state: Optional[CanvasState] = None
        self._state_cache: Dict[str, CanvasState] = {}  # session_id -> state
        self._initialized = True
        logger.info("[GraphCognition] 初始化完成")

    async def hydrate(self, context: "AgentContext") -> CanvasState:
        """Phase 1: 状态水合

        解析画布当前状态，计算增量变更，生成结构化摘要。

        Args:
            context: Agent 执行上下文

        Returns:
            CanvasState: 画布状态快照
        """
        ydoc = await context.get_ydoc()
        if not ydoc:
            logger.warning("[GraphCognition] 无法获取 ydoc: %s", context.session_id)
            return CanvasState(summary="画布为空", delta_summary="无变更")

        # 解析画布
        current_state = self._parse_canvas(ydoc)
        current_state.timestamp = time.time()

        # 获取上一状态
        last_state = self._state_cache.get(context.session_id)

        # 计算增量
        if last_state:
            delta = self._compute_delta(last_state, current_state)
            current_state.delta_summary = self._format_delta(delta)
        else:
            current_state.delta_summary = "首次加载画布"

        # 生成摘要
        current_state.summary = self._generate_summary(current_state)

        # 缓存当前状态
        self._state_cache[context.session_id] = current_state
        self._last_state = current_state

        logger.debug(
            "[GraphCognition] 水合完成: %d 元素, %d 连接",
            len(current_state.elements),
            len(current_state.connections),
        )

        return current_state

    def _parse_canvas(self, ydoc: Any) -> CanvasState:
        """解析 Yjs 文档"""
        state = CanvasState()

        try:
            elements_array = ydoc.get("elements", type="Array")
            raw_elements = list(elements_array)
        except Exception as e:  # pylint: disable=broad-except
            logger.warning("[GraphCognition] 获取 elements 失败: %s", e)
            return state

        # 解析元素
        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")

        for elem in raw_elements:
            if not isinstance(elem, dict):
                continue

            info = ElementInfo.from_element(elem)
            state.elements.append(info)

            # 更新边界
            min_x = min(min_x, info.x)
            min_y = min(min_y, info.y)
            max_x = max(max_x, info.x + info.width)
            max_y = max(max_y, info.y + info.height)

            # 解析连接关系 (箭头)
            if info.type == "arrow":
                start_binding = elem.get("startBinding", {})
                end_binding = elem.get("endBinding", {})
                if start_binding and end_binding:
                    state.connections.append(
                        {
                            "from": start_binding.get("elementId", ""),
                            "to": end_binding.get("elementId", ""),
                            "arrow_id": info.id,
                        }
                    )

        # 设置边界
        if state.elements:
            state.bounds = CanvasBounds(
                min_x=min_x if min_x != float("inf") else 0,
                min_y=min_y if min_y != float("inf") else 0,
                max_x=max_x if max_x != float("-inf") else 0,
                max_y=max_y if max_y != float("-inf") else 0,
                suggested_x=max_x + 100 if max_x != float("-inf") else 100,
                suggested_y=min_y if min_y != float("inf") else 100,
            )

        return state

    def _compute_delta(self, prev: CanvasState, curr: CanvasState) -> DeltaChange:
        """计算两个状态之间的差异"""
        delta = DeltaChange()

        prev_ids = {e.id for e in prev.elements}
        curr_ids = {e.id for e in curr.elements}

        # 新增元素
        added_ids = curr_ids - prev_ids
        for elem in curr.elements:
            if elem.id in added_ids:
                delta.added.append(elem)

        # 删除元素
        delta.removed = list(prev_ids - curr_ids)

        # 修改元素
        common_ids = prev_ids & curr_ids
        prev_map = {e.id: e for e in prev.elements}
        curr_map = {e.id: e for e in curr.elements}

        for eid in common_ids:
            prev_elem = prev_map[eid]
            curr_elem = curr_map[eid]

            changes = []
            # 检查位置变化
            if abs(prev_elem.x - curr_elem.x) > 1 or abs(prev_elem.y - curr_elem.y) > 1:
                changes.append("移动")
            # 检查文本变化
            if prev_elem.label != curr_elem.label:
                changes.append("文本修改")
            # 检查大小变化
            if (
                abs(prev_elem.width - curr_elem.width) > 1
                or abs(prev_elem.height - curr_elem.height) > 1
            ):
                changes.append("调整大小")

            if changes:
                delta.modified.append((eid[:8], "/".join(changes)))

        return delta

    def _format_delta(self, delta: DeltaChange) -> str:
        """格式化变更摘要"""
        parts = []

        if delta.added:
            types = [e.type for e in delta.added]
            parts.append(f"新增 {len(delta.added)} 个元素 ({', '.join(set(types))})")

        if delta.removed:
            parts.append(f"删除 {len(delta.removed)} 个元素")

        if delta.modified:
            mods = [f"{eid}({desc})" for eid, desc in delta.modified[:3]]
            parts.append(f"修改: {', '.join(mods)}")
            if len(delta.modified) > 3:
                parts.append(f"及其他 {len(delta.modified) - 3} 项")

        return "; ".join(parts) if parts else "无变更"

    def _generate_summary(self, state: CanvasState) -> str:
        """生成画布摘要"""
        if state.is_empty:
            return "画布为空"

        # 统计元素类型
        type_counts: Dict[str, int] = {}
        labels: List[str] = []

        for elem in state.elements:
            type_counts[elem.type] = type_counts.get(elem.type, 0) + 1
            if elem.label:
                label_preview = (
                    elem.label[:20] + "..." if len(elem.label) > 20 else elem.label
                )
                labels.append(f'"{label_preview}"')

        # 构建摘要
        parts = [f"画布包含 {len(state.elements)} 个元素"]

        # 类型分布
        type_desc = ", ".join(f"{count}个{t}" for t, count in type_counts.items())
        parts.append(f"类型: {type_desc}")

        # 文本内容
        if labels:
            shown = labels[:5]
            parts.append(f"内容: {', '.join(shown)}")

        # 连接关系
        if state.connections:
            parts.append(f"连接: {len(state.connections)} 条")

        return "; ".join(parts)

    def inject_to_prompt(self, prompt: str, state: CanvasState) -> str:
        """将画布状态注入系统 Prompt

        在系统提示词末尾添加画布上下文信息。

        Args:
            prompt: 原始系统提示词
            state: 画布状态

        Returns:
            str: 增强后的提示词
        """
        context_block = f"""

## 当前画布状态 (自动注入)

### 摘要
{state.summary}

### 最近变更
{state.delta_summary}

### 空间信息
- 元素数量: {state.element_count}
- 边界: X=[{state.bounds.min_x:.0f}, {state.bounds.max_x:.0f}], Y=[{state.bounds.min_y:.0f}, {state.bounds.max_y:.0f}]
- **建议新元素起始位置**: ({state.bounds.suggested_x:.0f}, {state.bounds.suggested_y:.0f})
"""
        return prompt + context_block

    def reset_cache(self, session_id: Optional[str] = None) -> None:
        """重置状态缓存"""
        if session_id:
            self._state_cache.pop(session_id, None)
        else:
            self._state_cache.clear()
        logger.info("[GraphCognition] 缓存已重置: %s", session_id or "全部")

def get_cognition() -> GraphCognition:
    """获取 GraphCognition 单例"""
    return GraphCognition()
