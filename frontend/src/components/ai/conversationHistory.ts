import type { DiagramBundle } from '../../types';
import type {
  ConversationMessage,
  DiagramGenerationMode,
} from '../../services/api/ai';
import type { ConversationMode } from './ChatInput';

export interface HydratedConversationMessage {
  id: string;
  requestId?: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  status?: 'thinking' | 'working' | 'completed' | 'error';
  virtualElements?: Record<string, unknown>[];
  usedMode?: ConversationMode;
  diagramBundle?: DiagramBundle;
  diagramFamily?: string;
  generationMode?: DiagramGenerationMode;
  managedScope?: string[];
  patchSummary?: string | null;
  unmanagedWarnings?: string[];
  sources?: Array<{ type: string; provider?: string; model?: string; role?: string }>;
  changeReasoning?: Array<{ step: string; explanation: string }>;
  affectedNodeIds?: string[];
  riskNotes?: string[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function asMode(value: unknown): ConversationMode | undefined {
  return value === 'agent' || value === 'planning' || value === 'mermaid'
    ? value
    : undefined;
}

function asStatus(
  value: unknown,
): HydratedConversationMessage['status'] | undefined {
  return value === 'thinking'
    || value === 'working'
    || value === 'completed'
    || value === 'error'
    ? value
    : undefined;
}

function asGenerationMode(value: unknown): DiagramGenerationMode | undefined {
  return value === 'llm'
    || value === 'deterministic_seed'
    || value === 'heuristic_patch'
    ? value
    : undefined;
}

function asStringArray(value: unknown): string[] | undefined {
  return Array.isArray(value) && value.every((item) => typeof item === 'string')
    ? value
    : undefined;
}

function asObjectArray(value: unknown): Record<string, unknown>[] | undefined {
  return Array.isArray(value) && value.every((item) => isRecord(item))
    ? value
    : undefined;
}

export function hydrateConversationMessages(
  messages: ConversationMessage[],
): HydratedConversationMessage[] {
  return messages.map((message, index) => {
    const extra = isRecord(message.extra_data) ? message.extra_data : {};
    const usedMode = asMode(extra.used_mode ?? extra.mode);
    const diagramBundle = isRecord(extra.diagram_bundle)
      ? extra.diagram_bundle as unknown as DiagramBundle
      : undefined;
    const virtualElements = asObjectArray(extra.virtual_elements)
      ?? (
        usedMode === 'planning'
          && Array.isArray(diagramBundle?.previewElements)
          && diagramBundle.previewElements.length > 0
          ? diagramBundle.previewElements as Record<string, unknown>[]
          : undefined
      );

    return {
      id: `history-${message.created_at}-${index}`,
      requestId: typeof extra.request_id === 'string' ? extra.request_id : undefined,
      role: message.role,
      content: message.content,
      timestamp: message.created_at,
      status: message.role === 'assistant'
        ? asStatus(extra.status) ?? 'completed'
        : undefined,
      virtualElements,
      usedMode,
      diagramBundle,
      diagramFamily: typeof extra.diagram_family === 'string'
        ? extra.diagram_family
        : undefined,
      generationMode: asGenerationMode(extra.generation_mode),
      managedScope: asStringArray(extra.managed_scope),
      patchSummary: typeof extra.patch_summary === 'string'
        ? extra.patch_summary
        : undefined,
      unmanagedWarnings: asStringArray(extra.unmanaged_warnings),
      sources: asObjectArray(extra.sources) as HydratedConversationMessage['sources'],
      changeReasoning: asObjectArray(extra.change_reasoning) as HydratedConversationMessage['changeReasoning'],
      affectedNodeIds: asStringArray(extra.affected_node_ids),
      riskNotes: asStringArray(extra.risk_notes),
    };
  });
}
