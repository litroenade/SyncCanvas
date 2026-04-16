import { describe, expect, it } from 'vitest';

import type { ManagedDiagramTarget } from '../types';
import { resolveDiagramRequestTarget } from './diagramRequestTarget';

function buildTarget(
  overrides: Partial<ManagedDiagramTarget> = {},
): ManagedDiagramTarget {
  return {
    mode: 'diagram',
    canEdit: true,
    diagramId: 'diagram_test',
    semanticId: 'component.test',
    editScope: 'diagram',
    title: 'Managed figure',
    family: 'paper_figure',
    managedState: 'managed',
    warnings: [],
    warningCount: 0,
    selectedCount: 1,
    ...overrides,
  };
}

describe('resolveDiagramRequestTarget', () => {
  it('forces Ask mode to create a new diagram even when a managed target is selected', () => {
    expect(resolveDiagramRequestTarget('planning', buildTarget())).toEqual({
      targetDiagramId: undefined,
      targetSemanticId: undefined,
      editScope: 'create_new',
    });
  });

  it('keeps Agent mode bound to the selected managed diagram', () => {
    expect(resolveDiagramRequestTarget('agent', buildTarget({
      diagramId: 'diagram_123',
      semanticId: 'encoder.stack',
      editScope: 'semantic',
    }))).toEqual({
      targetDiagramId: 'diagram_123',
      targetSemanticId: 'encoder.stack',
      editScope: 'semantic',
    });
  });

  it('falls back to create_new when Agent mode has no concrete diagram target', () => {
    expect(resolveDiagramRequestTarget('agent', buildTarget({
      diagramId: undefined,
      editScope: 'create_new',
    }))).toEqual({
      targetDiagramId: undefined,
      targetSemanticId: undefined,
      editScope: 'create_new',
    });
  });
});
