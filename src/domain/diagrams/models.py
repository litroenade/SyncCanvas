"""Diagram domain models for spec-first rendering."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


DiagramFamily = Literal[
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
    "transformer",
    "clip",
    "llm_stack",
    "comparison",
    "matrix",
    "paper_figure",
]

DiagramGenerationMode = Literal["llm", "deterministic_seed", "heuristic_patch"]

ComponentType = Literal[
    "container",
    "block",
    "repeated_stack",
    "token_strip",
    "matrix",
    "panel",
    "image_slot",
    "caption",
    "callout",
    "brace_or_bracket",
    "badge",
    "chart_bar",
    "zoom_inset",
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
]

ConnectorType = Literal["arrow", "line", "dashed-arrow"]
ManagedState = Literal["managed", "semi_managed", "unmanaged"]


class ManagedElementRef(BaseModel):
    """Semantic ownership marker attached to rendered elements."""

    diagram_id: str = Field(..., alias="diagramId")
    semantic_id: str = Field(..., alias="semanticId")
    role: str
    managed: bool = True
    render_version: int = Field(1, alias="renderVersion")

    model_config = {"populate_by_name": True}


class DiagramComponent(BaseModel):
    """High-level semantic component."""

    id: str
    component_type: ComponentType = Field(..., alias="componentType")
    label: str = ""
    text: str = ""
    shape: str = "rectangle"
    x: float = 0
    y: float = 0
    width: float = 120
    height: float = 60
    style: Dict[str, Any] = Field(default_factory=dict)
    data: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class DiagramConnector(BaseModel):
    """Semantic connection between components."""

    id: str
    connector_type: ConnectorType = Field("arrow", alias="connectorType")
    from_component: str = Field(..., alias="fromComponent")
    to_component: str = Field(..., alias="toComponent")
    label: str = ""
    style: Dict[str, Any] = Field(default_factory=dict)
    data: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class DiagramGroup(BaseModel):
    """Logical semantic grouping."""

    id: str
    label: str = ""
    component_ids: List[str] = Field(default_factory=list, alias="componentIds")
    style: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class DiagramAnnotation(BaseModel):
    """Annotation, caption, or free-standing label."""

    id: str
    annotation_type: str = Field("caption", alias="annotationType")
    text: str
    x: float = 0
    y: float = 0
    width: float = 220
    height: float = 40
    style: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class DiagramAsset(BaseModel):
    """Optional file/image asset metadata."""

    id: str
    asset_type: str = Field("image", alias="assetType")
    label: str = ""
    source: str = ""
    mime_type: str = Field("", alias="mimeType")
    width: float = 120
    height: float = 120

    model_config = {"populate_by_name": True}


class ManifestEntry(BaseModel):
    """Rendered element mapping for a semantic object."""

    semantic_id: str = Field(..., alias="semanticId")
    role: str
    element_ids: List[str] = Field(default_factory=list, alias="elementIds")
    bounds: Dict[str, float] = Field(default_factory=dict)
    render_version: int = Field(1, alias="renderVersion")

    model_config = {"populate_by_name": True}


class RenderManifest(BaseModel):
    """Semantic to rendered element manifest."""

    diagram_id: str = Field(..., alias="diagramId")
    render_version: int = Field(1, alias="renderVersion")
    entries: List[ManifestEntry] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class DiagramState(BaseModel):
    """Runtime state for managed/unmanaged status."""

    diagram_id: str = Field(..., alias="diagramId")
    managed_state: ManagedState = Field("managed", alias="managedState")
    managed_scope: List[str] = Field(default_factory=list, alias="managedScope")
    unmanaged_paths: List[str] = Field(default_factory=list, alias="unmanagedPaths")
    warnings: List[str] = Field(default_factory=list)
    last_edit_source: str = Field("system", alias="lastEditSource")
    last_patch_summary: str = Field("", alias="lastPatchSummary")

    model_config = {"populate_by_name": True}


class DiagramSummary(BaseModel):
    """Compact description returned to the UI."""

    diagram_id: str = Field(..., alias="diagramId")
    title: str
    family: DiagramFamily
    component_count: int = Field(..., alias="componentCount")
    connector_count: int = Field(..., alias="connectorCount")
    managed_state: ManagedState = Field(..., alias="managedState")
    managed_element_count: int = Field(..., alias="managedElementCount")

    model_config = {"populate_by_name": True}


class DiagramSpec(BaseModel):
    """Single diagram spec."""

    diagram_id: str = Field(..., alias="diagramId")
    diagram_type: str = Field("layered_architecture", alias="diagramType")
    family: DiagramFamily = "layered_architecture"
    version: int = 1
    title: str = ""
    prompt: str = ""
    style: Dict[str, Any] = Field(default_factory=dict)
    layout: Dict[str, Any] = Field(default_factory=dict)
    components: List[DiagramComponent] = Field(default_factory=list)
    connectors: List[DiagramConnector] = Field(default_factory=list)
    groups: List[DiagramGroup] = Field(default_factory=list)
    annotations: List[DiagramAnnotation] = Field(default_factory=list)
    assets: List[DiagramAsset] = Field(default_factory=list)
    layout_constraints: Dict[str, Any] = Field(default_factory=dict, alias="layoutConstraints")
    overrides: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class DiagramPatch(BaseModel):
    """Semantic patch applied to an existing diagram spec."""

    diagram_id: str = Field(..., alias="diagramId")
    summary: str = ""
    component_updates: Dict[str, Dict[str, Any]] = Field(default_factory=dict, alias="componentUpdates")
    component_additions: List[DiagramComponent] = Field(default_factory=list, alias="componentAdditions")
    component_removals: List[str] = Field(default_factory=list, alias="componentRemovals")
    connector_updates: Dict[str, Dict[str, Any]] = Field(default_factory=dict, alias="connectorUpdates")
    connector_additions: List[DiagramConnector] = Field(default_factory=list, alias="connectorAdditions")
    connector_removals: List[str] = Field(default_factory=list, alias="connectorRemovals")
    annotation_updates: Dict[str, Dict[str, Any]] = Field(default_factory=dict, alias="annotationUpdates")
    annotation_additions: List[DiagramAnnotation] = Field(default_factory=list, alias="annotationAdditions")
    annotation_removals: List[str] = Field(default_factory=list, alias="annotationRemovals")
    state_updates: Dict[str, Any] = Field(default_factory=dict, alias="stateUpdates")

    model_config = {"populate_by_name": True}


class DiagramBundle(BaseModel):
    """Payload returned to the client and/or persisted in Y.Doc."""

    spec: DiagramSpec
    manifest: RenderManifest
    state: DiagramState
    preview_elements: List[Dict[str, Any]] = Field(default_factory=list, alias="previewElements")
    preview_files: Dict[str, Any] = Field(default_factory=dict, alias="previewFiles")
    summary: DiagramSummary

    model_config = {"populate_by_name": True}
