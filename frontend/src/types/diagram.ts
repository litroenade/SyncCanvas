export type DiagramFamily =
  | 'workflow'
  | 'static_structure'
  | 'component_cluster'
  | 'technical_blueprint'
  | 'istar'
  | 'architecture_flow'
  | 'layered_architecture'
  | 'transformer_stack'
  | 'rag_pipeline'
  | 'react_loop'
  | 'transformer'
  | 'clip'
  | 'llm_stack'
  | 'comparison'
  | 'matrix'
  | 'paper_figure';

export interface ManagedElementRef {
  diagramId: string;
  semanticId: string;
  role: string;
  managed: boolean;
  renderVersion: number;
}

export interface DiagramComponent {
  id: string;
  componentType: string;
  label: string;
  text: string;
  shape: string;
  x: number;
  y: number;
  width: number;
  height: number;
  style: Record<string, unknown>;
  data: Record<string, unknown>;
}

export interface DiagramConnector {
  id: string;
  connectorType: string;
  fromComponent: string;
  toComponent: string;
  label: string;
  style: Record<string, unknown>;
  data?: Record<string, unknown>;
}

export interface DiagramAnnotation {
  id: string;
  annotationType: string;
  text: string;
  x: number;
  y: number;
  width: number;
  height: number;
  style: Record<string, unknown>;
}

export interface ManifestEntry {
  semanticId: string;
  role: string;
  elementIds: string[];
  bounds: Record<string, number>;
  renderVersion: number;
}

export interface RenderManifest {
  diagramId: string;
  renderVersion: number;
  entries: ManifestEntry[];
}

export interface DiagramState {
  diagramId: string;
  managedState: 'managed' | 'semi_managed' | 'unmanaged';
  managedScope: string[];
  unmanagedPaths: string[];
  warnings: string[];
  lastEditSource: string;
  lastPatchSummary: string;
}

export interface DiagramSummary {
  diagramId: string;
  title: string;
  family: DiagramFamily;
  componentCount: number;
  connectorCount: number;
  managedState: 'managed' | 'semi_managed' | 'unmanaged';
  managedElementCount: number;
}

export interface DiagramSpec {
  diagramId: string;
  diagramType: string;
  family: DiagramFamily;
  version: number;
  title: string;
  prompt: string;
  style: Record<string, unknown>;
  layout: Record<string, unknown>;
  components: DiagramComponent[];
  connectors: DiagramConnector[];
  groups: unknown[];
  annotations: DiagramAnnotation[];
  assets: unknown[];
  layoutConstraints: Record<string, unknown>;
  overrides: Record<string, unknown>;
}

export interface DiagramPatch {
  diagramId: string;
  summary: string;
  componentUpdates: Record<string, Record<string, unknown>>;
  componentAdditions: DiagramComponent[];
  componentRemovals: string[];
  connectorUpdates: Record<string, Record<string, unknown>>;
  connectorAdditions: DiagramConnector[];
  connectorRemovals: string[];
  annotationUpdates: Record<string, Record<string, unknown>>;
  annotationAdditions: DiagramAnnotation[];
  annotationRemovals: string[];
  stateUpdates: Record<string, unknown>;
}

export interface DiagramBundle {
  spec: DiagramSpec;
  manifest: RenderManifest;
  state: DiagramState;
  previewElements: Record<string, unknown>[];
  previewFiles: Record<string, unknown>;
  summary: DiagramSummary;
}

export interface ManagedDiagramTarget {
  mode: 'create_new' | 'diagram' | 'semantic' | 'conflict';
  canEdit: boolean;
  reason?: string;
  diagramId?: string;
  semanticId?: string;
  semanticPath?: string;
  editScope: 'create_new' | 'diagram' | 'semantic';
  title?: string;
  family?: DiagramFamily;
  managedState?: 'managed' | 'semi_managed' | 'unmanaged';
  warnings: string[];
  warningCount: number;
  selectedCount: number;
}
