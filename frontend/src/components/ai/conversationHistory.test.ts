import { describe, expect, it } from 'vitest';

import { hydrateConversationMessages } from './conversationHistory';

describe('conversationHistory', () => {
  it('hydrates assistant metadata for persisted managed-diagram responses', () => {
    const messages = hydrateConversationMessages([
      {
        role: 'assistant',
        content: 'Created a managed transformer diagram with 5 components.',
        created_at: 101,
        extra_data: {
          request_id: 'req-1',
          status: 'completed',
          used_mode: 'planning',
          diagram_family: 'transformer',
          generation_mode: 'deterministic_seed',
          diagram_bundle: {
            previewElements: [{ id: 'node-1' }],
            previewFiles: {},
            summary: { family: 'transformer' },
          },
          managed_scope: ['encoder.stack'],
          patch_summary: 'Created transformer diagram from prompt',
          unmanaged_warnings: ['connector normalized'],
          affected_node_ids: ['node-1'],
          risk_notes: ['preview only'],
        },
      },
    ]);

    expect(messages).toEqual([
      expect.objectContaining({
        requestId: 'req-1',
        role: 'assistant',
        status: 'completed',
        usedMode: 'planning',
        diagramFamily: 'transformer',
        generationMode: 'deterministic_seed',
        virtualElements: [{ id: 'node-1' }],
        managedScope: ['encoder.stack'],
        patchSummary: 'Created transformer diagram from prompt',
        unmanagedWarnings: ['connector normalized'],
        affectedNodeIds: ['node-1'],
        riskNotes: ['preview only'],
      }),
    ]);
  });

  it('keeps persisted user messages simple and preserves timestamps', () => {
    const messages = hydrateConversationMessages([
      {
        role: 'user',
        content: 'Create a transformer diagram',
        created_at: 202,
      },
    ]);

    expect(messages).toEqual([
      {
        id: 'history-202-0',
        requestId: undefined,
        role: 'user',
        content: 'Create a transformer diagram',
        timestamp: 202,
        status: undefined,
        virtualElements: undefined,
        usedMode: undefined,
        diagramBundle: undefined,
        diagramFamily: undefined,
        generationMode: undefined,
        managedScope: undefined,
        patchSummary: undefined,
        unmanagedWarnings: undefined,
        sources: undefined,
        changeReasoning: undefined,
        affectedNodeIds: undefined,
        riskNotes: undefined,
      },
    ]);
  });
});
