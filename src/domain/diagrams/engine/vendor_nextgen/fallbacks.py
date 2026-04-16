"""Deterministic spec fallbacks backed by the vendored engineering examples."""


import re
from copy import deepcopy
from typing import Callable

from src.domain.diagrams.families import DEFAULT_FAMILY, canonical_family
from src.domain.diagrams.models import (
    DiagramAnnotation,
    DiagramComponent,
    DiagramConnector,
    DiagramGroup,
    DiagramSpec,
)

from .examples import (
    ai_app_stack_example,
    architecture_flow_example,
    coding_copilot_platform_example,
    component_cluster_example,
    istar_example,
    llm_layered_architecture_example,
    multiagent_code_review_example,
    platform_topology_example,
    rag_pipeline_example,
    react_loop_example,
    static_structure_example,
    technical_blueprint_example,
    technical_blueprint_llm_example,
    transformer_architecture_example,
    workflow_example,
)
from .semantic_ir import SemanticDiagram, SemanticNode

MANAGED_DIAGRAM_STYLE: dict[str, object] = {
    "preset": "handdrawn-paper",
    "fontFamily": "Virgil",
    "roughness": 1,
    "strokeWidth": 2,
}

DEFAULT_DIAGRAM_LAYOUT: dict[str, float] = {
    "titleX": 100,
    "titleY": 24,
    "titleWidth": 1040,
}


def _contains_any(prompt: str, values: tuple[str, ...]) -> bool:
    lowered = prompt.casefold()
    return any(value in lowered for value in values)


def _short_title(prompt: str, fallback: str) -> str:
    compact = re.sub(r"\s+", " ", prompt).strip(" \n\t.:;,-")
    if not compact:
        return fallback
    return compact[:72]


def _layered_example(prompt: str) -> SemanticDiagram:
    if _contains_any(
        prompt,
        (
            "multi-agent",
            "multiagent",
            "planner",
            "worker agent",
            "worker agents",
            "verifier",
            "code review",
            "\u4ee3\u7801\u5ba1\u67e5",
            "\u591a\u667a\u80fd\u4f53",
            "\u89c4\u5212\u5668",
            "\u5de5\u4f5c\u4ee3\u7406",
        ),
    ):
        return multiagent_code_review_example()
    if _contains_any(
        prompt,
        (
            "copilot",
            "ide",
            "editor",
            "sandbox",
            "tool sandbox",
            "\u4ee3\u7801\u52a9\u624b",
            "\u7f16\u8f91\u5668",
        ),
    ):
        return coding_copilot_platform_example()
    if _contains_any(
        prompt,
        (
            "topology",
            "fleet",
            "fabric",
            "control plane",
            "data plane",
            "\u62d3\u6251",
            "\u63a7\u5236\u5e73\u9762",
            "\u6570\u636e\u5e73\u9762",
        ),
    ):
        return platform_topology_example()
    if _contains_any(
        prompt,
        (
            "app stack",
            "application stack",
            "client apps",
            "\u73b0\u4ee3 ai \u5e94\u7528",
            "\u5e94\u7528\u6808",
        ),
    ):
        return ai_app_stack_example()
    return llm_layered_architecture_example()


_FAMILY_BUILDERS: dict[str, Callable[[str], SemanticDiagram]] = {
    "workflow": lambda _prompt: workflow_example(),
    "static_structure": lambda _prompt: static_structure_example(),
    "component_cluster": lambda _prompt: component_cluster_example(),
    "technical_blueprint": lambda prompt: (
        technical_blueprint_llm_example()
        if _contains_any(
            prompt,
            (
                "llm",
                "model",
                "inference",
                "runtime",
                "retrieval",
                "gateway",
                "safety",
                "rag",
                "\u5927\u6a21\u578b",
                "\u63a8\u7406",
                "\u68c0\u7d22",
            ),
        )
        else technical_blueprint_example(False)
    ),
    "istar": lambda _prompt: istar_example(),
    "architecture_flow": lambda _prompt: architecture_flow_example(),
    "layered_architecture": _layered_example,
    "transformer_stack": lambda _prompt: transformer_architecture_example(),
    "react_loop": lambda _prompt: react_loop_example(),
    "rag_pipeline": lambda _prompt: rag_pipeline_example(),
}


def _shape_for_node(node: SemanticNode) -> str:
    if node.kind == "decision":
        return "diamond"
    if node.kind in {"terminator", "goal", "softgoal", "network"}:
        return "ellipse"
    return "rectangle"


def _component_type_for_node(node: SemanticNode) -> str:
    if node.kind in {
        "process",
        "decision",
        "terminator",
        "class",
        "interface",
        "component",
        "database",
        "device",
        "title_block",
        "goal",
        "task",
        "resource",
        "softgoal",
        "network",
    }:
        return node.kind
    return "block"


def _style_for_node(diagram: SemanticDiagram, node: SemanticNode) -> dict[str, object]:
    style: dict[str, object] = {}
    if diagram.family in {"layered_architecture", "component_cluster"} and node.kind in {
        "process",
        "component",
        "database",
    }:
        style["backgroundColor"] = "#ffffff"
    return style


def _annotation_for_prompt(prompt: str, family: str) -> DiagramAnnotation:
    return DiagramAnnotation(
        id=f"note.{family}",
        annotationType="caption",
        text=_short_title(prompt, family.replace("_", " ").title()),
        x=120,
        y=690,
        width=900,
        height=36,
        style={},
    )


def build_seed_spec(prompt: str, family: str, *, diagram_id: str) -> DiagramSpec:
    resolved_family = canonical_family(family)
    builder = _FAMILY_BUILDERS.get(resolved_family, _FAMILY_BUILDERS[DEFAULT_FAMILY])
    diagram = builder(prompt)
    return semantic_diagram_to_spec(
        diagram,
        prompt=prompt,
        family=resolved_family,
        diagram_id=diagram_id,
    )


def semantic_diagram_to_spec(
    diagram: SemanticDiagram,
    *,
    prompt: str,
    family: str,
    diagram_id: str,
) -> DiagramSpec:
    groups = [
        DiagramGroup(
            id=group.id,
            label=group.label,
            componentIds=list(group.members),
            style={"kind": group.kind},
        )
        for group in diagram.groups
    ]
    components = [
        DiagramComponent(
            id=node.id,
            componentType=_component_type_for_node(node),
            label=node.label,
            text=node.label,
            shape=_shape_for_node(node),
            x=0,
            y=0,
            width=0,
            height=0,
            style=_style_for_node(diagram, node),
            data={
                **node.meta,
                "vendorKind": node.kind,
                "rowHint": node.row_hint,
                "colHint": node.col_hint,
                "styleRole": node.style_role,
                "groupId": node.group,
                "attrs": list(node.attrs),
                "methods": list(node.methods),
            },
        )
        for node in diagram.nodes
    ]
    connectors = [
        DiagramConnector(
            id=edge.id,
            connectorType="dashed-arrow" if edge.dashed else "arrow",
            fromComponent=edge.src,
            toComponent=edge.dst,
            label=edge.label,
            style={},
            data={
                **edge.meta,
                "vendorKind": edge.kind,
                "preferredDir": edge.preferred_dir,
            },
        )
        for edge in diagram.edges
    ]
    return DiagramSpec(
        diagramId=diagram_id,
        diagramType=family,
        family=family,
        version=1,
        title=_short_title(prompt, diagram.title or family.replace("_", " ").title()),
        prompt=prompt,
        style=deepcopy(MANAGED_DIAGRAM_STYLE),
        layout=deepcopy(DEFAULT_DIAGRAM_LAYOUT),
        components=components,
        connectors=connectors,
        groups=groups,
        annotations=[_annotation_for_prompt(prompt, family)],
        assets=[],
        layoutConstraints={
            "vendorUseFamilyEngine": True,
            "keepouts": [list(keepout) for keepout in diagram.keepouts],
            "vendorTemplateId": diagram.id,
        },
        overrides={},
    )
