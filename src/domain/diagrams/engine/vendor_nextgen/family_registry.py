
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class FamilyConfig:
    name: str
    route_strategy: str
    notes: str


FAMILY_REGISTRY: Dict[str, FamilyConfig] = {
    'workflow': FamilyConfig('workflow', 'workflow_specialized', 'TB/LR flow with decision-aware branch routing'),
    'static_structure': FamilyConfig('static_structure', 'orthogonal', 'class/interface dependency routing'),
    'component_cluster': FamilyConfig('component_cluster', 'component_cluster_specialized', 'component-aware clustered wiring with dedicated database approach lanes'),
    'technical_blueprint': FamilyConfig('technical_blueprint', 'blueprint_specialized', 'trunk-aware blueprint routing with keepout-aware lanes and patch-friendly local wiring'),
    'istar': FamilyConfig('istar', 'istar_specialized', 'actor-boundary aware goal model routing with rationale-centric layout'),
    'architecture_flow': FamilyConfig('architecture_flow', 'architecture_flow_specialized', 'left-stack to network to repository architecture flow with specialized dashed network hub routing'),
    'layered_architecture': FamilyConfig('layered_architecture', 'generic_layered', 'layered paper/system architecture with grouped regions'),
    'transformer_stack': FamilyConfig('transformer_stack', 'transformer_specialized', 'encoder/decoder stack template with cross-attention'),
    'react_loop': FamilyConfig('react_loop', 'react_specialized', 'agent workflow loop with reasoning, tools, observation, memory, and answer'),
    'rag_pipeline': FamilyConfig('rag_pipeline', 'rag_specialized', 'dual-lane ingest/runtime retrieval-augmented generation pipeline'),
}


def family_for(diagram_family: str) -> FamilyConfig:
    if diagram_family not in FAMILY_REGISTRY:
        raise KeyError(f'Unknown family: {diagram_family}')
    return FAMILY_REGISTRY[diagram_family]
