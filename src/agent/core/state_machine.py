"""模块名称: state_machine
主要功能: Agent 状态机

提供清晰的状态转换管理：
- 状态定义和转换规则
- 状态转换钩子
- 状态历史记录

@Time: 2025-12-10
@File: state_machine.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
import time

from src.logger import get_logger

logger = get_logger(__name__)


class AgentState(Enum):
    """Agent 状态"""

    IDLE = auto()  # 空闲
    INITIALIZING = auto()  # 初始化中
    THINKING = auto()  # 思考中（LLM 调用）
    PLANNING = auto()  # 规划中
    ACTING = auto()  # 执行工具中
    WAITING = auto()  # 等待外部输入
    RECOVERING = auto()  # 错误恢复中
    COMPLETED = auto()  # 已完成
    FAILED = auto()  # 失败
    CANCELLED = auto()  # 已取消


@dataclass
class StateTransition:
    """状态转换记录"""

    from_state: AgentState
    to_state: AgentState
    timestamp: float
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


# 有效的状态转换规则
VALID_TRANSITIONS: Dict[AgentState, Set[AgentState]] = {
    AgentState.IDLE: {
        AgentState.INITIALIZING,
        AgentState.CANCELLED,
    },
    AgentState.INITIALIZING: {
        AgentState.THINKING,
        AgentState.PLANNING,
        AgentState.FAILED,
        AgentState.CANCELLED,
    },
    AgentState.THINKING: {
        AgentState.ACTING,
        AgentState.COMPLETED,
        AgentState.RECOVERING,
        AgentState.FAILED,
        AgentState.CANCELLED,
    },
    AgentState.PLANNING: {
        AgentState.THINKING,
        AgentState.ACTING,
        AgentState.FAILED,
        AgentState.CANCELLED,
    },
    AgentState.ACTING: {
        AgentState.THINKING,  # 工具执行后回到思考
        AgentState.RECOVERING,  # 工具执行失败，尝试恢复
        AgentState.FAILED,
        AgentState.CANCELLED,
    },
    AgentState.WAITING: {
        AgentState.THINKING,
        AgentState.CANCELLED,
        AgentState.FAILED,
    },
    AgentState.RECOVERING: {
        AgentState.THINKING,  # 恢复成功，继续思考
        AgentState.ACTING,  # 重试工具执行
        AgentState.FAILED,  # 恢复失败
        AgentState.CANCELLED,
    },
    AgentState.COMPLETED: set(),  # 终态
    AgentState.FAILED: set(),  # 终态
    AgentState.CANCELLED: set(),  # 终态
}


class AgentStateMachine:
    """Agent 状态机

    管理 Agent 的状态转换，提供钩子机制。

    Example:
        ```python
        sm = AgentStateMachine()

        # 注册状态变更回调
        sm.on_enter(AgentState.THINKING, lambda: print("开始思考"))
        sm.on_exit(AgentState.ACTING, lambda: print("工具执行结束"))

        # 状态转换
        sm.transition(AgentState.THINKING, reason="开始处理用户请求")
        sm.transition(AgentState.ACTING, reason="调用 create_element")
        ```
    """

    def __init__(self, initial_state: AgentState = AgentState.IDLE):
        """初始化状态机

        Args:
            initial_state: 初始状态
        """
        self._state = initial_state
        self._history: List[StateTransition] = []
        self._enter_hooks: Dict[AgentState, List[Callable]] = {}
        self._exit_hooks: Dict[AgentState, List[Callable]] = {}
        self._any_hooks: List[Callable[[AgentState, AgentState], None]] = []

    @property
    def state(self) -> AgentState:
        """当前状态"""
        return self._state

    @property
    def history(self) -> List[StateTransition]:
        """状态转换历史"""
        return self._history.copy()

    @property
    def is_terminal(self) -> bool:
        """是否处于终态"""
        return self._state in {
            AgentState.COMPLETED,
            AgentState.FAILED,
            AgentState.CANCELLED,
        }

    def can_transition(self, to_state: AgentState) -> bool:
        """检查是否可以转换到指定状态

        Args:
            to_state: 目标状态

        Returns:
            是否可以转换
        """
        valid_targets = VALID_TRANSITIONS.get(self._state, set())
        return to_state in valid_targets

    def transition(
        self,
        to_state: AgentState,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        force: bool = False,
    ) -> bool:
        """执行状态转换

        Args:
            to_state: 目标状态
            reason: 转换原因
            metadata: 附加元数据
            force: 是否强制转换（跳过规则检查）

        Returns:
            是否转换成功
        """
        if not force and not self.can_transition(to_state):
            logger.warning(f"无效的状态转换: {self._state.name} -> {to_state.name}")
            return False

        from_state = self._state

        # 执行退出钩子
        self._run_exit_hooks(from_state)

        # 记录转换
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            timestamp=time.time(),
            reason=reason,
            metadata=metadata or {},
        )
        self._history.append(transition)

        # 更新状态
        self._state = to_state

        # 执行进入钩子
        self._run_enter_hooks(to_state)

        # 执行通用钩子
        for hook in self._any_hooks:
            try:
                hook(from_state, to_state)
            except Exception as e:
                logger.error(f"状态转换钩子执行失败: {e}")

        logger.debug(
            f"状态转换: {from_state.name} -> {to_state.name}"
            f"{f' ({reason})' if reason else ''}"
        )

        return True

    def on_enter(self, state: AgentState, callback: Callable[[], None]) -> None:
        """注册进入状态的钩子

        Args:
            state: 目标状态
            callback: 回调函数
        """
        if state not in self._enter_hooks:
            self._enter_hooks[state] = []
        self._enter_hooks[state].append(callback)

    def on_exit(self, state: AgentState, callback: Callable[[], None]) -> None:
        """注册离开状态的钩子

        Args:
            state: 源状态
            callback: 回调函数
        """
        if state not in self._exit_hooks:
            self._exit_hooks[state] = []
        self._exit_hooks[state].append(callback)

    def on_transition(
        self,
        callback: Callable[[AgentState, AgentState], None],
    ) -> None:
        """注册状态转换钩子

        Args:
            callback: 回调函数，接收 (from_state, to_state)
        """
        self._any_hooks.append(callback)

    def _run_enter_hooks(self, state: AgentState) -> None:
        """执行进入钩子"""
        for hook in self._enter_hooks.get(state, []):
            try:
                hook()
            except Exception as e:
                logger.error(f"进入钩子执行失败: {e}")

    def _run_exit_hooks(self, state: AgentState) -> None:
        """执行退出钩子"""
        for hook in self._exit_hooks.get(state, []):
            try:
                hook()
            except Exception as e:
                logger.error(f"退出钩子执行失败: {e}")

    def reset(self) -> None:
        """重置状态机"""
        self._state = AgentState.IDLE
        self._history.clear()

    def get_duration_in_state(self, state: AgentState) -> float:
        """获取在某状态停留的总时间（毫秒）

        Args:
            state: 目标状态

        Returns:
            停留时间（毫秒）
        """
        total_ms = 0.0

        # 遍历历史记录，计算在该状态的时间
        for i, transition in enumerate(self._history):
            if transition.to_state == state:
                # 找到下一个转换的时间
                if i + 1 < len(self._history):
                    next_transition = self._history[i + 1]
                    total_ms += (
                        next_transition.timestamp - transition.timestamp
                    ) * 1000
                elif self._state == state:
                    # 当前仍在该状态
                    total_ms += (time.time() - transition.timestamp) * 1000

        return total_ms

    def get_summary(self) -> Dict[str, Any]:
        """获取状态机摘要

        Returns:
            摘要字典
        """
        return {
            "current_state": self._state.name,
            "is_terminal": self.is_terminal,
            "transition_count": len(self._history),
            "time_in_thinking_ms": round(
                self.get_duration_in_state(AgentState.THINKING), 2
            ),
            "time_in_acting_ms": round(
                self.get_duration_in_state(AgentState.ACTING), 2
            ),
        }
