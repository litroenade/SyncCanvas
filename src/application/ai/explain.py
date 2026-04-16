"""Explain payload helpers."""

from typing import Any


def build_explain_payload(
    payload: dict[str, Any],
    *,
    provider: str,
    model: str,
    affected_node_ids: list[str] | None = None,
) -> dict[str, Any]:
    response = dict(payload)
    response.setdefault(
        "sources",
        [{"type": "llm", "provider": provider, "model": model, "role": "assistant"}],
    )
    response.setdefault(
        "change_reasoning",
        [{"step": "agent", "explanation": "AI generated a response using the current room context."}],
    )
    response.setdefault("affected_node_ids", affected_node_ids or [])
    response.setdefault("risk_notes", [])
    return response

