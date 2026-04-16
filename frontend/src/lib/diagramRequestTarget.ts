import type { ManagedDiagramTarget } from '../types';
import type { ConversationMode } from '../components/ai/ChatInput';

export interface DiagramRequestTarget {
  targetDiagramId?: string;
  targetSemanticId?: string;
  editScope: 'create_new' | 'diagram' | 'semantic';
}

export function resolveDiagramRequestTarget(
  mode: ConversationMode,
  diagramTarget?: ManagedDiagramTarget | null,
): DiagramRequestTarget {
  if (mode !== 'agent') {
    return {
      targetDiagramId: undefined,
      targetSemanticId: undefined,
      editScope: 'create_new',
    };
  }

  if (!diagramTarget?.diagramId || diagramTarget.editScope === 'create_new') {
    return {
      targetDiagramId: undefined,
      targetSemanticId: undefined,
      editScope: 'create_new',
    };
  }

  return {
    targetDiagramId: diagramTarget.diagramId,
    targetSemanticId: diagramTarget.semanticId,
    editScope: diagramTarget.editScope,
  };
}
