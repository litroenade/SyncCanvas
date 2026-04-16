"""Conversation mode helpers."""

AI_CONVERSATION_MODES = {"agent", "planning", "mermaid"}


def normalize_conversation_mode(mode: str | None) -> str:
    normalized = (mode or "").strip().lower()
    return normalized if normalized in AI_CONVERSATION_MODES else "planning"

