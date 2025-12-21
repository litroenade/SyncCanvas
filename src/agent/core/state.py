"""模块名称: state
主要功能: Agent 状态机
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Set
from src.logger import get_logger

logger = get_logger(__name__)


class AgentState(Enum):
    """Agent 状态"""

    IDLE = auto()
    INITIALIZING = auto()
    THINKING = auto()
    PLANNING = auto()
    ACTING = auto()
    WAITING = auto()
    RECOVERING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class StateTransition:
    """状态转换记录"""

    from_state: AgentState
    to_state: AgentState
    timestamp: float
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


VALID_TRANSITIONS: Dict[AgentState, Set[AgentState]] = {
    AgentState.IDLE: {AgentState.INITIALIZING, AgentState.CANCELLED},
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
        AgentState.THINKING,
        AgentState.RECOVERING,
        AgentState.FAILED,
        AgentState.CANCELLED,
    },
    AgentState.WAITING: {AgentState.THINKING, AgentState.CANCELLED, AgentState.FAILED},
    AgentState.RECOVERING: {
        AgentState.THINKING,
        AgentState.ACTING,
        AgentState.FAILED,
        AgentState.CANCELLED,
    },
    AgentState.COMPLETED: set(),
    AgentState.FAILED: set(),
    AgentState.CANCELLED: set(),
}


class AgentStateMachine:
    """Agent 状态机"""

    def __init__(self, initial_state: AgentState = AgentState.IDLE):
        self._state = initial_state
        self._history: List[StateTransition] = []
        self._enter_hooks: Dict[AgentState, List[Callable]] = {}
        self._exit_hooks: Dict[AgentState, List[Callable]] = {}

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def is_terminal(self) -> bool:
        return self._state in {
            AgentState.COMPLETED,
            AgentState.FAILED,
            AgentState.CANCELLED,
        }

    def transition(
        self, to_state: AgentState, reason: str = "", force: bool = False
    ) -> bool:
        valid_targets = VALID_TRANSITIONS.get(self._state, set())
        if not force and to_state not in valid_targets:
            logger.warning("无效状态转换: %s -> %s", self._state.name, to_state.name)
            return False

        from_state = self._state
        self._history.append(StateTransition(from_state, to_state, time.time(), reason))
        self._state = to_state
        logger.debug("状态转换: %s -> %s (%s)", from_state.name, to_state.name, reason)
        return True

    def reset(self) -> None:
        self._state = AgentState.IDLE
        self._history.clear()

    def get_summary(self) -> Dict[str, Any]:
        return {
            "current_state": self._state.name,
            "transition_count": len(self._history),
        }
