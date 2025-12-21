"""模块名称: context
主要功能: Agent 执行上下文和指标
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from src.agent.canvas.backend import get_canvas_backend
from src.logger import get_logger

logger = get_logger(__name__)


class AgentStatus(Enum):
    """Agent 运行状态枚举"""

    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    COMPLETED = "completed"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class AgentMetrics:
    """Agent 执行指标"""

    start_time: float = 0.0
    end_time: float = 0.0
    total_llm_calls: int = 0
    total_tool_calls: int = 0
    total_retries: int = 0
    llm_latency_ms: List[float] = field(default_factory=list)
    tool_latency_ms: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        """总执行时间 (毫秒)"""
        if self.end_time > 0:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    @property
    def avg_llm_latency_ms(self) -> float:
        """平均 LLM 延迟"""
        if self.llm_latency_ms:
            return sum(self.llm_latency_ms) / len(self.llm_latency_ms)
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "duration_ms": round(self.duration_ms, 2),
            "total_llm_calls": self.total_llm_calls,
            "total_tool_calls": self.total_tool_calls,
            "total_retries": self.total_retries,
            "avg_llm_latency_ms": round(self.avg_llm_latency_ms, 2),
            "errors": self.errors[-5:],
        }


@dataclass
class AgentContext:
    """Agent 执行上下文"""

    run_id: int
    session_id: str
    user_id: Optional[str] = None
    theme: str = "light"  # 画布主题 ("light" | "dark")
    shared_state: Dict[str, Any] = field(default_factory=dict)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    created_element_ids: List[str] = field(default_factory=list)
    _cancelled: bool = field(default=False, repr=False)
    _ydoc: Any = field(default=None, repr=False)

    def cancel(self) -> None:
        """标记任务为已取消"""
        self._cancelled = True
        logger.info("[AgentContext] 任务已取消: run_id= %s", self.run_id)

    @property
    def is_cancelled(self) -> bool:
        """检查任务是否已取消"""
        return self._cancelled

    async def get_ydoc(self) -> Any:
        """获取房间的 Yjs 文档"""
        if self._ydoc is not None:
            return self._ydoc

        try:
            backend = get_canvas_backend()
            doc, _ = await backend.get_room_doc(self.session_id)
            self._ydoc = doc
            return self._ydoc
        except Exception as e:  # pylint: disable=broad-except
            logger.warning("[AgentContext] 获取 ydoc 失败: %s", e)
            return None

    async def get_room_and_doc(self):
        """获取房间文档和元素数组 (统一入口)"""
        try:
            backend = get_canvas_backend()
            return await backend.get_room_doc(self.session_id)
        except Exception as e:  # pylint: disable=broad-except
            logger.warning("[AgentContext] 获取 room doc 失败: %s", e)
            return None, None

    async def get_canvas_elements(self) -> List[Dict[str, Any]]:
        """获取画布上的所有元素"""
        ydoc = await self.get_ydoc()
        if not ydoc:
            logger.warning("[AgentContext] 无法获取房间文档: %s", self.session_id)
            return []

        try:
            elements_array = ydoc.get("elements", type="Array")
            return list(elements_array)
        except Exception as e:  # pylint: disable=broad-except
            logger.error("[AgentContext] 获取画布元素失败: %s", e)
            return []

    async def get_canvas_bounds(self) -> Dict[str, Any]:
        """获取画布边界信息"""
        elements = await self.get_canvas_elements()

        if not elements:
            return {
                "minX": 0, "minY": 0, "maxX": 0, "maxY": 0,
                "suggested_x": 100, "suggested_y": 100, "elements_count": 0,
            }

        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")

        for elem in elements:
            x = elem.get("x", 0)
            y = elem.get("y", 0)
            width = elem.get("width", 100)
            height = elem.get("height", 100)
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x + width)
            max_y = max(max_y, y + height)

        return {
            "minX": min_x if min_x != float("inf") else 0,
            "minY": min_y if min_y != float("inf") else 0,
            "maxX": max_x if max_x != float("-inf") else 0,
            "maxY": max_y if max_y != float("-inf") else 0,
            "suggested_x": max_x + 50 if max_x != float("-inf") else 100,
            "suggested_y": min_y if min_y != float("inf") else 100,
            "elements_count": len(elements),
        }

    def record_tool_result(self, tool_name: str, args: Dict, result: Any) -> None:
        """记录工具执行结果"""
        self.tool_results.append({
            "tool": tool_name, "arguments": args, "result": result,
        })

    def get_shared(self, key: str, default: Any = None) -> Any:
        """获取共享状态值"""
        return self.shared_state.get(key, default)

    def set_shared(self, key: str, value: Any) -> None:
        """设置共享状态值"""
        self.shared_state[key] = value
