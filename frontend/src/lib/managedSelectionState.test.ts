import { describe, expect, it } from 'vitest';

import type { ManagedDiagramTarget } from '../types';
import { coalesceManagedSelection, isSameManagedSelection } from './managedSelectionState';

function buildTarget(
  overrides: Partial<ManagedDiagramTarget> = {},
): ManagedDiagramTarget {
  return {
    mode: 'diagram',
    canEdit: true,
    diagramId: 'diagram_test',
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

describe('managedSelectionState helpers', () => {
  it('treats semantically equal selections as identical', () => {
    const previous = buildTarget({
      warnings: ['needs review'],
      warningCount: 1,
      semanticId: 'stack.encoder',
      semanticPath: 'stack.encoder',
    });
    const next = buildTarget({
      warnings: ['needs review'],
      warningCount: 1,
      semanticId: 'stack.encoder',
      semanticPath: 'stack.encoder',
    });

    expect(isSameManagedSelection(previous, next)).toBe(true);
    expect(coalesceManagedSelection(previous, next)).toBe(previous);
  });

  it('detects selection changes when managed scope metadata changes', () => {
    const previous = buildTarget({
      managedState: 'managed',
      warnings: [],
      warningCount: 0,
    });
    const next = buildTarget({
      managedState: 'semi_managed',
      warnings: ['needs review'],
      warningCount: 1,
    });

    expect(isSameManagedSelection(previous, next)).toBe(false);
    expect(coalesceManagedSelection(previous, next)).toBe(next);
  });

  it('handles null transitions without collapsing them incorrectly', () => {
    const selection = buildTarget();

    expect(isSameManagedSelection(null, null)).toBe(true);
    expect(isSameManagedSelection(selection, null)).toBe(false);
    expect(coalesceManagedSelection(selection, null)).toBeNull();
  });
});
