"""Stable diagram render identifiers."""

import hashlib


def _slug(text: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in text.lower())
    return cleaned.strip("_") or "item"


def stable_element_id(diagram_id: str, semantic_id: str, role: str) -> str:
    digest = hashlib.sha1(f"{diagram_id}:{semantic_id}:{role}".encode()).hexdigest()[:10]
    return f"diag_{_slug(semantic_id)}_{role}_{digest}"

