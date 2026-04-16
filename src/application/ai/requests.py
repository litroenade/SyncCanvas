"""AI request ledger helpers."""

from sqlmodel import Session

from src.persistence.db.models.ai import AgentRequest
from src.persistence.db.repositories import ai_runs


def get_request_by_idempotency_key(
    session: Session,
    idempotency_key: str,
) -> AgentRequest | None:
    return ai_runs.get_agent_request_by_idempotency_key(session, idempotency_key)


def update_request(
    session: Session,
    request_id: str,
    *,
    status: str | None = None,
    run_id: int | None = None,
    response: dict | None = None,
    error: str | None = None,
) -> AgentRequest | None:
    return ai_runs.update_agent_request(
        session,
        request_id,
        status=status,
        run_id=run_id,
        response=response,
        error=error,
    )
