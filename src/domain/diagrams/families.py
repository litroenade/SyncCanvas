"""Diagram family routing and canonicalization."""


import re
from collections.abc import Iterable

DEFAULT_FAMILY = "layered_architecture"

CANONICAL_FAMILIES: tuple[str, ...] = (
    "workflow",
    "static_structure",
    "component_cluster",
    "technical_blueprint",
    "istar",
    "architecture_flow",
    "layered_architecture",
    "transformer_stack",
    "react_loop",
    "rag_pipeline",
)

FAMILY_ALIASES: dict[str, str] = {
    "transformer": "transformer_stack",
    "clip": "transformer_stack",
    "llm_stack": "layered_architecture",
    "comparison": "layered_architecture",
    "matrix": "layered_architecture",
    "paper_figure": "layered_architecture",
}

_ROUTING_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "transformer_stack",
        (
            "transformer",
            "encoder-decoder",
            "encoder decoder",
            "cross attention",
            "self-attention",
            "self attention",
            "attention block",
            "token flow",
            "embedding",
            "decoder stack",
            "\u53d8\u6362\u5668",
            "\u6ce8\u610f\u529b",
        ),
    ),
    (
        "react_loop",
        (
            "react loop",
            "reason act",
            "tool action",
            "observation",
            "reasoning loop",
            "agent loop",
            "thought action observation",
            "tool-use loop",
            "\u63a8\u7406",
            "\u89c2\u5bdf",
            "\u5de5\u5177\u8c03\u7528",
        ),
    ),
    (
        "rag_pipeline",
        (
            "rag",
            "retrieval augmented",
            "retrieval-augmented",
            "vector store",
            "embedding index",
            "rerank",
            "retriever",
            "knowledge base",
            "\u68c0\u7d22\u589e\u5f3a",
            "\u5411\u91cf\u5e93",
        ),
    ),
    (
        "technical_blueprint",
        (
            "blueprint",
            "rack",
            "cabinet",
            "deployment node",
            "machine room",
            "server rack",
            "hardware layout",
            "infra blueprint",
            "technical blueprint",
            "\u6280\u672f\u84dd\u56fe",
            "\u84dd\u56fe",
        ),
    ),
    (
        "workflow",
        (
            "workflow",
            "flowchart",
            "approval flow",
            "state transition",
            "business process",
            "pipeline steps",
            "\u5de5\u4f5c\u6d41",
            "\u6d41\u7a0b\u56fe",
        ),
    ),
    (
        "static_structure",
        (
            "class diagram",
            "uml class",
            "domain model",
            "entity relationship",
            "static structure",
            "repository pattern",
            "interface and class",
            "\u7c7b\u56fe",
            "\u9759\u6001\u7ed3\u6784",
        ),
    ),
    (
        "component_cluster",
        (
            "component cluster",
            "service cluster",
            "module graph",
            "component map",
            "subsystem map",
            "dependency cluster",
            "\u7ec4\u4ef6\u96c6\u7fa4",
            "\u6a21\u5757\u56fe",
        ),
    ),
    (
        "istar",
        (
            "i*",
            "istar",
            "goal model",
            "softgoal",
            "actor dependency",
            "goal/task/resource",
            "\u76ee\u6807\u6a21\u578b",
            "\u8f6f\u76ee\u6807",
        ),
    ),
    (
        "architecture_flow",
        (
            "request flow",
            "data flow",
            "event flow",
            "processing flow",
            "system flow",
            "architecture flow",
            "\u8bf7\u6c42\u6d41",
            "\u6570\u636e\u6d41",
        ),
    ),
    (
        "layered_architecture",
        (
            "architecture",
            "system design",
            "system diagram",
            "platform diagram",
            "layered",
            "llm stack",
            "\u5206\u5c42",
            "\u67b6\u6784",
            "\u7cfb\u7edf\u56fe",
            "\u8bba\u6587\u56fe",
        ),
    ),
)


def canonical_family(family: str | None) -> str:
    if not family:
        return DEFAULT_FAMILY
    normalized = family.strip().casefold().replace("-", "_").replace(" ", "_")
    if normalized in CANONICAL_FAMILIES:
        return normalized
    return FAMILY_ALIASES.get(normalized, DEFAULT_FAMILY)


def family_aliases() -> dict[str, str]:
    return dict(FAMILY_ALIASES)


def known_families(include_aliases: bool = False) -> tuple[str, ...]:
    if not include_aliases:
        return CANONICAL_FAMILIES
    aliases = tuple(sorted(FAMILY_ALIASES))
    return CANONICAL_FAMILIES + aliases


def supports_prompt(prompt: str, mode: str = "agent") -> bool:
    text = prompt.strip()
    if not text:
        return False
    if mode == "mermaid":
        return False
    lowered = text.casefold()
    return any(
        token in lowered
        for token in (
            "diagram",
            "figure",
            "architecture",
            "workflow",
            "pipeline",
            "graph",
            "chart",
            "\u56fe",
            "\u67b6\u6784",
            "\u6d41\u7a0b",
            "\u7cfb\u7edf",
        )
    ) or len(text) > 8


def route_family(prompt: str) -> str:
    lowered = prompt.casefold()
    for family, keywords in _ROUTING_RULES:
        if _contains_any(lowered, keywords):
            return family
    return DEFAULT_FAMILY


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    for keyword in keywords:
        if keyword.isascii():
            pattern = rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])"
            if re.search(pattern, text):
                return True
            continue
        if keyword in text:
            return True
    return False
