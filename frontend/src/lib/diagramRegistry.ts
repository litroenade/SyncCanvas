import type { DiagramFamily } from '../types';
import { translate } from '../i18n';

export interface DiagramFamilyMeta {
  family: DiagramFamily;
  label: string;
  description: string;
  starterPrompt: string;
}

function createLocalizedFamilyMeta(
  family: DiagramFamily,
  labelKey: string,
  descriptionKey: string,
  starterPromptKey: string,
): DiagramFamilyMeta {
  return {
    family,
    get label() {
      return translate(labelKey);
    },
    get description() {
      return translate(descriptionKey);
    },
    get starterPrompt() {
      return translate(starterPromptKey);
    },
  };
}

export const DIAGRAM_FAMILY_REGISTRY = {
  workflow: createLocalizedFamilyMeta(
    'workflow',
    'diagramFamily.workflow.label',
    'diagramFamily.workflow.description',
    'diagramFamily.workflow.starterPrompt',
  ),
  static_structure: createLocalizedFamilyMeta(
    'static_structure',
    'diagramFamily.staticStructure.label',
    'diagramFamily.staticStructure.description',
    'diagramFamily.staticStructure.starterPrompt',
  ),
  component_cluster: createLocalizedFamilyMeta(
    'component_cluster',
    'diagramFamily.componentCluster.label',
    'diagramFamily.componentCluster.description',
    'diagramFamily.componentCluster.starterPrompt',
  ),
  technical_blueprint: createLocalizedFamilyMeta(
    'technical_blueprint',
    'diagramFamily.technicalBlueprint.label',
    'diagramFamily.technicalBlueprint.description',
    'diagramFamily.technicalBlueprint.starterPrompt',
  ),
  istar: createLocalizedFamilyMeta(
    'istar',
    'diagramFamily.istar.label',
    'diagramFamily.istar.description',
    'diagramFamily.istar.starterPrompt',
  ),
  architecture_flow: createLocalizedFamilyMeta(
    'architecture_flow',
    'diagramFamily.architectureFlow.label',
    'diagramFamily.architectureFlow.description',
    'diagramFamily.architectureFlow.starterPrompt',
  ),
  layered_architecture: createLocalizedFamilyMeta(
    'layered_architecture',
    'diagramFamily.layeredArchitecture.label',
    'diagramFamily.layeredArchitecture.description',
    'diagramFamily.layeredArchitecture.starterPrompt',
  ),
  transformer_stack: createLocalizedFamilyMeta(
    'transformer_stack',
    'diagramFamily.transformerStack.label',
    'diagramFamily.transformerStack.description',
    'diagramFamily.transformerStack.starterPrompt',
  ),
  rag_pipeline: createLocalizedFamilyMeta(
    'rag_pipeline',
    'diagramFamily.ragPipeline.label',
    'diagramFamily.ragPipeline.description',
    'diagramFamily.ragPipeline.starterPrompt',
  ),
  react_loop: createLocalizedFamilyMeta(
    'react_loop',
    'diagramFamily.reactLoop.label',
    'diagramFamily.reactLoop.description',
    'diagramFamily.reactLoop.starterPrompt',
  ),
  transformer: createLocalizedFamilyMeta(
    'transformer',
    'diagramFamily.transformer.label',
    'diagramFamily.transformer.description',
    'diagramFamily.transformer.starterPrompt',
  ),
  clip: createLocalizedFamilyMeta(
    'clip',
    'diagramFamily.clip.label',
    'diagramFamily.clip.description',
    'diagramFamily.clip.starterPrompt',
  ),
  llm_stack: createLocalizedFamilyMeta(
    'llm_stack',
    'diagramFamily.llmStack.label',
    'diagramFamily.llmStack.description',
    'diagramFamily.llmStack.starterPrompt',
  ),
  comparison: createLocalizedFamilyMeta(
    'comparison',
    'diagramFamily.comparison.label',
    'diagramFamily.comparison.description',
    'diagramFamily.comparison.starterPrompt',
  ),
  matrix: createLocalizedFamilyMeta(
    'matrix',
    'diagramFamily.matrix.label',
    'diagramFamily.matrix.description',
    'diagramFamily.matrix.starterPrompt',
  ),
  paper_figure: createLocalizedFamilyMeta(
    'paper_figure',
    'diagramFamily.paperFigure.label',
    'diagramFamily.paperFigure.description',
    'diagramFamily.paperFigure.starterPrompt',
  ),
} satisfies Record<DiagramFamily, DiagramFamilyMeta>;

export const DEFAULT_DIAGRAM_ENTRY_FAMILIES: readonly DiagramFamily[] = [
  'layered_architecture',
  'transformer_stack',
  'react_loop',
  'rag_pipeline',
];

export const DIAGRAM_ENTRY_COPY = {
  get emptyStateTitle() {
    return translate('diagramEntry.emptyStateTitle');
  },
  get emptyStateDescription() {
    return translate('diagramEntry.emptyStateDescription');
  },
  get inputPlaceholder() {
    return translate('diagramEntry.inputPlaceholder');
  },
};

export const MANAGED_DIAGRAM_COPY = {
  get defaultConflictReason() {
    return translate('managedDiagram.defaultConflictReason');
  },
  stateLabels: {
    get managed() {
      return translate('managedDiagram.state.managed');
    },
    get semi_managed() {
      return translate('managedDiagram.state.semiManaged');
    },
    get unmanaged() {
      return translate('managedDiagram.state.unmanaged');
    },
  },
  createNew: {
    get headline() {
      return translate('managedDiagram.createNew.headline');
    },
    get description() {
      return translate('managedDiagram.createNew.description');
    },
  },
  blocked: {
    get headline() {
      return translate('managedDiagram.blocked.headline');
    },
    get description() {
      return translate('managedDiagram.blocked.description');
    },
  },
  editable: {
    get semanticHeadline() {
      return translate('managedDiagram.editable.semanticHeadline');
    },
    get diagramHeadline() {
      return translate('managedDiagram.editable.diagramHeadline');
    },
    get semanticDescription() {
      return translate('managedDiagram.editable.semanticDescription');
    },
    get diagramDescription() {
      return translate('managedDiagram.editable.diagramDescription');
    },
  },
};

export const DIAGRAM_AGENT_COPY = {
  get blockedAssistantFallback() {
    return translate('diagramAgent.blockedAssistantFallback');
  },
  summary: {
    get diagramLabel() {
      return translate('diagramAgent.summary.diagramLabel');
    },
    get componentsLabel() {
      return translate('diagramAgent.summary.componentsLabel');
    },
    get connectorsLabel() {
      return translate('diagramAgent.summary.connectorsLabel');
    },
    get titleLabel() {
      return translate('diagramAgent.summary.titleLabel');
    },
    get managedLabel() {
      return translate('diagramAgent.summary.managedLabel');
    },
    get generationModeLabel() {
      return translate('diagramAgent.summary.generationModeLabel');
    },
    get scopeLabel() {
      return translate('diagramAgent.summary.scopeLabel');
    },
    get patchLabel() {
      return translate('diagramAgent.summary.patchLabel');
    },
    get warningsLabel() {
      return translate('diagramAgent.summary.warningsLabel');
    },
  },
  conflictPanel: {
    get headline() {
      return translate('diagramAgent.conflictPanel.headline');
    },
    get descriptionFallback() {
      return translate('diagramAgent.conflictPanel.descriptionFallback');
    },
    get actionsLabel() {
      return translate('diagramAgent.conflictPanel.actionsLabel');
    },
    get stashLabel() {
      return translate('diagramAgent.conflictPanel.stashLabel');
    },
    get replayBaselineLabel() {
      return translate('diagramAgent.conflictPanel.replayBaselineLabel');
    },
    get manualMergeLabel() {
      return translate('diagramAgent.conflictPanel.manualMergeLabel');
    },
    get restoreDraftLabel() {
      return translate('diagramAgent.conflictPanel.restoreDraftLabel');
    },
    get manualMergeGuideTitle() {
      return translate('diagramAgent.conflictPanel.manualMergeGuideTitle');
    },
    get manualMergeGuideMessage() {
      return translate('diagramAgent.conflictPanel.manualMergeGuideMessage');
    },
  },
  stash: {
    get saved() {
      return translate('diagramAgent.stash.saved');
    },
    get canvasUnavailable() {
      return translate('diagramAgent.stash.canvasUnavailable');
    },
    get missing() {
      return translate('diagramAgent.stash.missing');
    },
    get invalidFormat() {
      return translate('diagramAgent.stash.invalidFormat');
    },
    get restored() {
      return translate('diagramAgent.stash.restored');
    },
    get restoreFailed() {
      return translate('diagramAgent.stash.restoreFailed');
    },
  },
  replay: {
    get confirm() {
      return translate('diagramAgent.replay.confirm');
    },
    get title() {
      return translate('diagramAgent.replay.title');
    },
    get missingHead() {
      return translate('diagramAgent.replay.missingHead');
    },
    get success() {
      return translate('diagramAgent.replay.success');
    },
    get buttonLabel() {
      return translate('diagramAgent.replay.buttonLabel');
    },
  },
  rebuild: {
    get success() {
      return translate('diagramAgent.rebuild.success');
    },
    get failure() {
      return translate('diagramAgent.rebuild.failure');
    },
    get normalActionLabel() {
      return translate('diagramAgent.rebuild.normalActionLabel');
    },
    get warningActionLabel() {
      return translate('diagramAgent.rebuild.warningActionLabel');
    },
  },
};

export const MERMAID_PREVIEW_CONFIG = {
  parser: {
    themeVariables: {
      fontSize: '16px',
    },
  },
  convert: {
    regenerateIds: true,
  },
} as const;

export const MERMAID_PREVIEW_COPY = {
  get title() {
    return translate('mermaidPreview.title');
  },
  get copyLabel() {
    return translate('mermaidPreview.copyLabel');
  },
  get copiedLabel() {
    return translate('mermaidPreview.copiedLabel');
  },
  get convertingLabel() {
    return translate('mermaidPreview.convertingLabel');
  },
  get previewLabel() {
    return translate('mermaidPreview.previewLabel');
  },
  get errorPrefix() {
    return translate('mermaidPreview.errorPrefix');
  },
};

export const PREVIEW_CANVAS_COPY = {
  get emptyState() {
    return translate('previewCanvas.emptyState');
  },
  get clearTitle() {
    return translate('previewCanvas.clearTitle');
  },
  get addToCanvasLabel() {
    return translate('previewCanvas.addToCanvasLabel');
  },
  get addedLabel() {
    return translate('previewCanvas.addedLabel');
  },
};

export const VIRTUAL_CANVAS_COPY = {
  get expandTitle() {
    return translate('virtualCanvas.expandTitle');
  },
  get collapseTitle() {
    return translate('virtualCanvas.collapseTitle');
  },
  get addToCanvasLabel() {
    return translate('virtualCanvas.addToCanvasLabel');
  },
  get addedLabel() {
    return translate('virtualCanvas.addedLabel');
  },
  get imageAlt() {
    return translate('virtualCanvas.imageAlt');
  },
  get generatingLabel() {
    return translate('virtualCanvas.generatingLabel');
  },
  get generationFailedLabel() {
    return translate('virtualCanvas.generationFailedLabel');
  },
  get preparingLabel() {
    return translate('virtualCanvas.preparingLabel');
  },
  get emptyState() {
    return translate('virtualCanvas.emptyState');
  },
  get dragPreviewTitle() {
    return translate('virtualCanvas.dragPreviewTitle');
  },
};

export const AI_CONVERSATION_MODE_COPY = {
  planning: {
    get label() {
      return translate('conversationMode.planning.label');
    },
    get description() {
      return translate('conversationMode.planning.description');
    },
  },
  agent: {
    get label() {
      return translate('conversationMode.agent.label');
    },
    get description() {
      return translate('conversationMode.agent.description');
    },
  },
  mermaid: {
    get label() {
      return translate('conversationMode.mermaid.label');
    },
    get description() {
      return translate('conversationMode.mermaid.description');
    },
  },
};

export function getDiagramQuickPrompts(
  families: readonly DiagramFamily[] = DEFAULT_DIAGRAM_ENTRY_FAMILIES,
): string[] {
  return families.map((family) => DIAGRAM_FAMILY_REGISTRY[family].starterPrompt);
}

export function getDiagramFamilyMeta(
  family: string | null | undefined,
): DiagramFamilyMeta | null {
  if (!family) {
    return null;
  }

  return DIAGRAM_FAMILY_REGISTRY[family as DiagramFamily] ?? null;
}

export function getDiagramFamilyLabel(
  family: string | null | undefined,
): string {
  return getDiagramFamilyMeta(family)?.label ?? family ?? translate('diagramFamily.unknown');
}

const NORMALIZED_MANAGED_DIAGRAM_CONFLICT_REASONS = new Set([
  'You can only edit one managed diagram at a time.',
  'You can only target one managed diagram at a time.',
  'The selected managed diagram is missing or not loaded yet.',
]);

export function localizeManagedDiagramReason(
  reason: string | undefined,
  fallback?: string,
): string | undefined {
  const text = reason?.trim();

  if (!text) {
    return fallback;
  }

  if (NORMALIZED_MANAGED_DIAGRAM_CONFLICT_REASONS.has(text)) {
    return MANAGED_DIAGRAM_COPY.defaultConflictReason;
  }

  return text;
}

export function formatManagedDiagramWarningSummary(warningCount: number): string {
  return translate('managedDiagram.warningSummary', { count: warningCount });
}
