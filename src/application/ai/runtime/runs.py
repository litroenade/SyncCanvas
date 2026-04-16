"""Agent run persistence helpers."""

import time
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from src.infra.logging import get_logger
from src.persistence.db.models.ai import AgentAction, AgentRun

logger = get_logger(__name__)


class AgentRunService:
    """Data access helpers for agent runs and tool actions."""

    def __init__(self, session: Session):
        self.session = session

    def create_run(
        self,
        room_id: str,
        prompt: str,
        model: str = "",
        user_id: Optional[int] = None,
        *,
        auto_commit: bool = True,
    ) -> AgentRun:
        del user_id
        run = AgentRun(
            room_id=room_id,
            prompt=prompt,
            model=model,
            status="running",
            created_at=int(time.time() * 1000),
        )
        self.session.add(run)
        if auto_commit:
            self.session.commit()
        else:
            self.session.flush()
        self.session.refresh(run)
        logger.info(
            "Agent run created",
            extra={"run_id": run.id, "room_id": room_id, "model": model},
        )
        return run

    def log_action(
        self,
        run_id: int,
        tool: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any],
        *,
        auto_commit: bool = True,
    ) -> AgentAction:
        action = AgentAction(
            run_id=run_id,
            tool=tool,
            arguments=arguments or {},
            result=result or {},
            created_at=int(time.time() * 1000),
        )
        self.session.add(action)
        if auto_commit:
            self.session.commit()
            self.session.refresh(action)
        return action

    def complete_run(
        self,
        run_id: int,
        message: str = "",
        output: Optional[str] = None,
        *,
        auto_commit: bool = True,
    ) -> AgentRun:
        run = self.session.get(AgentRun, run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")
        run.status = "completed"
        run.message = message or output or ""
        run.finished_at = int(time.time() * 1000)
        self.session.add(run)
        if auto_commit:
            self.session.commit()
        self.session.refresh(run)
        logger.info("Agent run completed", extra={"run_id": run_id})
        return run

    def fail_run(
        self,
        run_id: int,
        error: str = "",
        *,
        auto_commit: bool = True,
    ) -> AgentRun:
        run = self.session.get(AgentRun, run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")
        run.status = "failed"
        run.message = error
        run.finished_at = int(time.time() * 1000)
        self.session.add(run)
        if auto_commit:
            self.session.commit()
        self.session.refresh(run)
        logger.error("Agent run failed", extra={"run_id": run_id, "error": error})
        return run

    def get_run(self, run_id: int) -> Optional[AgentRun]:
        return self.session.get(AgentRun, run_id)

    def get_run_actions(self, run_id: int) -> List[AgentAction]:
        statement = (
            select(AgentAction)
            .where(AgentAction.run_id == run_id)
            .order_by(AgentAction.created_at)  # type: ignore[arg-type]
        )
        return list(self.session.exec(statement).all())

    def get_run_detail(self, run_id: int) -> Optional[Dict[str, Any]]:
        run = self.get_run(run_id)
        if not run:
            return None
        actions = self.get_run_actions(run_id)
        return {
            "id": run.id,
            "room_id": run.room_id,
            "prompt": run.prompt,
            "model": run.model,
            "status": run.status,
            "message": run.message,
            "created_at": run.created_at,
            "finished_at": run.finished_at,
            "actions": [
                {
                    "id": action.id,
                    "tool": action.tool,
                    "arguments": action.arguments,
                    "result": action.result,
                    "created_at": action.created_at,
                }
                for action in actions
            ],
        }

    def get_room_runs(self, room_id: str, limit: int = 20) -> List[AgentRun]:
        statement = (
            select(AgentRun)
            .where(AgentRun.room_id == room_id)
            .order_by(AgentRun.created_at.desc())  # type: ignore[arg-type]
            .limit(limit)
        )
        return list(self.session.exec(statement).all())

