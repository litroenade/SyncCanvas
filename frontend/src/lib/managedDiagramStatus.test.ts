import { describe, expect, it } from 'vitest';

import type { ManagedDiagramTarget } from '../types';
import { getManagedDiagramStatusView } from './managedDiagramStatus';

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

describe('managedDiagramStatus helper', () => {
  it('maps create_new target to a new-diagram status panel', () => {
    const status = getManagedDiagramStatusView(buildTarget({
      mode: 'create_new',
      diagramId: undefined,
      editScope: 'create_new',
      title: undefined,
      family: undefined,
      managedState: undefined,
    }));

    expect(status.mode).toBe('create_new');
    expect(status.headline).toBe('\u521b\u5efa\u56fe\u8868');
    expect(status.showRebuild).toBe(false);
    expect(status.warningCount).toBe(0);
    expect(status.description).toContain('\u521b\u5efa');
  });

  it('maps semantic managed target to normal editable status', () => {
    const status = getManagedDiagramStatusView(buildTarget({
      mode: 'semantic',
      editScope: 'semantic',
      managedState: 'managed',
      semanticId: 'stack.encoder.block1',
      semanticPath: 'stack.encoder.block1',
    }));

    expect(status.severity).toBe('normal');
    expect(status.headline).toContain('\u76ee\u6807');
    expect(status.stateLabel).toBe('\u7ba1\u7406');
    expect(status.metaItems).toContain('stack.encoder.block1');
    expect(status.showRebuild).toBe(false);
  });

  it('uses diagram family display labels instead of raw ids in meta items', () => {
    const status = getManagedDiagramStatusView(buildTarget({
      family: 'paper_figure',
    }));

    expect(status.metaItems).toContain('Paper Figure');
    expect(status.metaItems).not.toContain('paper_figure');
  });

  it('maps semi-managed diagram target to warning status with warnings', () => {
    const status = getManagedDiagramStatusView(buildTarget({
      managedState: 'semi_managed',
      warnings: ['Matrix edits need review.'],
      warningCount: 1,
    }));

    expect(status.severity).toBe('warning');
    expect(status.stateLabel).toBe('\u534a\u53d7\u7ba1');
    expect(status.warningSummary).toBe('1' + '\u6761\u544a\u8b66');
    expect(status.warnings).toEqual(['Matrix edits need review.']);
    expect(status.showRebuild).toBe(true);
  });

  it('maps unmanaged managed state to warning and keeps rebuild visible when editable', () => {
    const status = getManagedDiagramStatusView(buildTarget({
      managedState: 'unmanaged',
      warnings: ['Deep nested edit requires review.'],
      warningCount: 1,
    }));

    expect(status.severity).toBe('warning');
    expect(status.stateLabel).toBe('\u65e0\u7ba1\u7406');
    expect(status.warningCount).toBe(1);
    expect(status.showRebuild).toBe(true);
  });

  it('maps conflict to blocked status with localized reason', () => {
    const status = getManagedDiagramStatusView(buildTarget({
      mode: 'conflict',
      canEdit: false,
      reason: 'You can only edit one managed diagram at a time.',
      diagramId: undefined,
    }));

    expect(status.severity).toBe('blocked');
    expect(status.canEdit).toBe(false);
    expect(status.reason).toBe('\u5f53\u524d\u53ea\u80fd\u7f16\u8f91\u4e00\u4e2a\u53d7\u7ba1\u56fe\u8868');
    expect(status.showRebuild).toBe(false);
  });

  it('normalizes conflict reason from missing diagram message', () => {
    const status = getManagedDiagramStatusView(buildTarget({
      mode: 'conflict',
      canEdit: false,
      reason: 'The selected managed diagram is missing or not loaded yet.',
    }));

    expect(status.reason).toBe("\u5f53\u524d\u53ea\u80fd\u7f16\u8f91\u4e00\u4e2a\u53d7\u7ba1\u56fe\u8868");
  });

  it('maps managed state to normal without warning summary', () => {
    const status = getManagedDiagramStatusView(buildTarget({
      managedState: 'managed',
      warnings: ['Unexpected warning should be ignored when managed'],
      warningCount: 5,
    }));

    expect(status.severity).toBe('normal');
    expect(status.warningSummary).toBeUndefined();
    expect(status.showRebuild).toBe(false);
  });

  it('shows rebuild only on semi-managed and unmanaged states', () => {
    const managed = getManagedDiagramStatusView(buildTarget({
      managedState: 'managed',
      warnings: ['warning should not show rebuild'],
      warningCount: 1,
      diagramId: 'diagram_test',
    }));
    const semiManaged = getManagedDiagramStatusView(buildTarget({
      managedState: 'semi_managed',
      warnings: ['needs review'],
      warningCount: 1,
      diagramId: 'diagram_test',
    }));
    const unmanaged = getManagedDiagramStatusView(buildTarget({
      managedState: 'unmanaged',
      warnings: ['needs review'],
      diagramId: 'diagram_test',
      warningCount: 1,
    }));

    expect(managed.showRebuild).toBe(false);
    expect(semiManaged.showRebuild).toBe(true);
    expect(unmanaged.showRebuild).toBe(true);
  });

  it('maps canEdit=false to blocked status without rebuild action', () => {
    const status = getManagedDiagramStatusView(buildTarget({
      mode: 'diagram',
      canEdit: false,
    }));

    expect(status.severity).toBe('blocked');
    expect(status.canEdit).toBe(false);
    expect(status.showRebuild).toBe(false);
  });
});
