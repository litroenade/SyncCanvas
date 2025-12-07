"""Agent run lifecycle management and persistence."""

from typing import Any, Dict, Optional

from sqlmodel import Session

from src.db import crud
from src.db.models import AgentRun, AgentAction
from src.logger import get_logger

logger = get_logger(__name__)


class AgentRunService:
    """Lightweight helper to persist agent runs and tool invocations."""

    def __init__(self, session: Session):
        self.session = session

    def start_run(self, room_id: str, prompt: str, model: str) -> AgentRun:
        run = AgentRun(room_id=room_id, prompt=prompt, model=model, status="running")
        created = crud.create_agent_run(self.session, run)
        logger.info("agent run started", extra={"run_id": created.id, "room": room_id})
        return created

    def log_action(self, run_id: int, tool: str, args: Dict[str, Any], result: Dict[str, Any]) -> AgentAction:
        action = AgentAction(run_id=run_id, tool=tool, arguments=args or {}, result=result or {})
        recorded = crud.create_agent_action(self.session, action)
        logger.debug(
            "agent action recorded",
            extra={"run_id": run_id, "tool": tool},
        )
        return recorded

    def finish_run(self, run_id: int, status: str, message: str = "") -> AgentRun:
        finished = crud.finish_agent_run(self.session, run_id=run_id, status=status, message=message)
        logger.info(
            "agent run finished",
            extra={"run_id": run_id, "status": status},
        )
        return finished

    def get_run_detail(self, run_id: int) -> Optional[Dict[str, Any]]:
        run = self.session.get(AgentRun, run_id)
        if not run:
            return None
        actions = crud.list_agent_actions(self.session, run_id=run_id)
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
