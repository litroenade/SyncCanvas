"""AI run/request repositories."""

import time
from typing import List, Optional

from sqlmodel import Session, select

from src.persistence.db.engine import commit_session
from src.persistence.db.models.ai import AgentAction, AgentRequest, AgentRun


def create_agent_run(session: Session, run: AgentRun, auto_commit: bool = True) -> AgentRun:
    session.add(run)
    if auto_commit:
        commit_session(session)
    else:
        session.flush()
    session.refresh(run)
    return run


def get_agent_request_by_idempotency_key(
    session: Session,
    idempotency_key: str,
) -> Optional[AgentRequest]:
    statement = select(AgentRequest).where(AgentRequest.idempotency_key == idempotency_key)
    return session.exec(statement).first()


def create_agent_request(
    session: Session,
    request_id: str,
    room_id: str,
    user_id: Optional[int],
    idempotency_key: str,
    source: str = "api",
    status: str = "processing",
    explain_requested: bool = False,
    timeout_ms: Optional[int] = None,
    auto_commit: bool = True,
) -> AgentRequest:
    request = AgentRequest(
        request_id=request_id,
        room_id=room_id,
        user_id=user_id,
        idempotency_key=idempotency_key,
        source=source,
        status=status,
        explain_requested=explain_requested,
        timeout_ms=timeout_ms,
    )
    request.updated_at = int(time.time() * 1000)
    session.add(request)
    if auto_commit:
        commit_session(session)
    else:
        session.flush()
    session.refresh(request)
    return request


def update_agent_request(
    session: Session,
    request_id: str,
    *,
    status: Optional[str] = None,
    run_id: Optional[int] = None,
    response: Optional[dict] = None,
    error: Optional[str] = None,
    auto_commit: bool = True,
) -> Optional[AgentRequest]:
    statement = select(AgentRequest).where(AgentRequest.request_id == request_id)
    req = session.exec(statement).first()
    if req is None:
        return None
    if status is not None:
        req.status = status
    if run_id is not None:
        req.run_id = run_id
    if response is not None:
        req.response = response
    if error is not None:
        req.error = error
    req.updated_at = int(time.time() * 1000)
    session.add(req)
    if auto_commit:
        commit_session(session)
    else:
        session.flush()
    return req


def finish_agent_run(session: Session, run_id: int, status: str, message: str = "") -> AgentRun:
    run = session.get(AgentRun, run_id)
    if not run:
        raise ValueError(f"Agent run not found: {run_id}")
    run.status = status
    run.message = message
    run.finished_at = int(time.time() * 1000)
    session.add(run)
    commit_session(session)
    session.refresh(run)
    return run


def create_agent_action(session: Session, action: AgentAction, auto_commit: bool = True) -> AgentAction:
    session.add(action)
    if auto_commit:
        commit_session(session)
    else:
        session.flush()
    session.refresh(action)
    return action


def list_agent_actions(session: Session, run_id: int) -> List[AgentAction]:
    statement = (
        select(AgentAction)
        .where(AgentAction.run_id == run_id)
        .order_by(AgentAction.created_at)  # type: ignore[arg-type]
    )
    return list(session.exec(statement))
