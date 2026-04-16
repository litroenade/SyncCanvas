import * as Y from 'yjs';
import { describe, expect, it } from 'vitest';

import type { DiagramBundle, ManagedDiagramTarget } from '../types';
import { ExcalidrawYjsManager } from './yjs';

function buildBundle(
  diagramId: string,
  overrides: Partial<DiagramBundle> = {},
): DiagramBundle {
  const bundle: DiagramBundle = {
    spec: {
      diagramId,
      diagramType: 'paper_figure',
      family: 'paper_figure',
      version: 1,
      title: `Managed ${diagramId}`,
      prompt: 'Draw a managed paper figure',
      style: {},
      layout: {},
      components: [
        {
          id: `${diagramId}.panel`,
          componentType: 'panel',
          label: 'Panel',
          text: 'Panel',
          shape: 'rectangle',
          x: 80,
          y: 80,
          width: 260,
          height: 160,
          style: {},
          data: {},
        },
        {
          id: `${diagramId}.block`,
          componentType: 'block',
          label: 'Block',
          text: 'Block',
          shape: 'rectangle',
          x: 120,
          y: 130,
          width: 140,
          height: 52,
          style: {},
          data: {},
        },
      ],
      connectors: [
        {
          id: `${diagramId}.connector`,
          connectorType: 'arrow',
          fromComponent: `${diagramId}.panel`,
          toComponent: `${diagramId}.block`,
          label: 'flow',
          style: {},
          data: {},
        },
      ],
      groups: [],
      annotations: [
        {
          id: `${diagramId}.caption`,
          annotationType: 'caption',
          text: 'Caption',
          x: 90,
          y: 270,
          width: 220,
          height: 32,
          style: {},
        },
      ],
      assets: [],
      layoutConstraints: {},
      overrides: {},
    },
    manifest: {
      diagramId,
      renderVersion: 1,
      entries: [
        {
          semanticId: `${diagramId}.panel`,
          role: 'panel',
          elementIds: [`${diagramId}-panel-shape`, `${diagramId}-panel-text`],
          bounds: { x: 80, y: 80, width: 260, height: 160 },
          renderVersion: 1,
        },
        {
          semanticId: `${diagramId}.block`,
          role: 'block',
          elementIds: [`${diagramId}-block-shape`, `${diagramId}-block-text`],
          bounds: { x: 120, y: 130, width: 140, height: 52 },
          renderVersion: 1,
        },
        {
          semanticId: `${diagramId}.connector`,
          role: 'connector',
          elementIds: [`${diagramId}-connector`],
          bounds: { x: 180, y: 120, width: 40, height: 40 },
          renderVersion: 1,
        },
      ],
    },
    state: {
      diagramId,
      managedState: 'managed',
      managedScope: [`${diagramId}.panel`, `${diagramId}.block`],
      unmanagedPaths: [],
      warnings: [],
      lastEditSource: 'system',
      lastPatchSummary: 'Created from test bundle',
    },
    previewElements: [],
    previewFiles: {},
    summary: {
      diagramId,
      title: `Managed ${diagramId}`,
      family: 'paper_figure',
      componentCount: 2,
      connectorCount: 1,
      managedState: 'managed',
      managedElementCount: 5,
    },
  };

  return {
    ...bundle,
    ...overrides,
    spec: {
      ...bundle.spec,
      ...(overrides.spec || {}),
    },
    manifest: {
      ...bundle.manifest,
      ...(overrides.manifest || {}),
    },
    state: {
      ...bundle.state,
      ...(overrides.state || {}),
    },
    summary: {
      ...bundle.summary,
      ...(overrides.summary || {}),
    },
  };
}

function createManager(): ExcalidrawYjsManager {
  const manager = new ExcalidrawYjsManager();
  const internal = manager as unknown as {
    _roomId: string | null;
    _ydoc: Y.Doc | null;
    _attachMaps: () => void;
  };

  internal._roomId = 'room-test';
  internal._ydoc = new Y.Doc();
  internal._attachMaps();
  return manager;
}

describe('ExcalidrawYjsManager managed diagram behavior', () => {
  it('prefers existing selection scope when semantic target is refreshed into managed', () => {
    const manager = createManager();
    const template = buildBundle('diagram_theta');
    const before = buildBundle('diagram_theta', {
      state: {
        ...template.state,
        managedState: 'semi_managed',
        warnings: ['Manual drag on panel'],
      },
    });

    manager.saveDiagramBundle(before);

    const stale = manager.refreshManagedSelection({
      mode: 'semantic',
      canEdit: true,
      diagramId: 'diagram_theta',
      semanticId: 'diagram_theta.block',
      semanticPath: 'diagram_theta.block',
      editScope: 'semantic',
      title: before.summary.title,
      family: before.summary.family,
      managedState: before.state.managedState,
      warnings: ['stale warning'],
      warningCount: 1,
      selectedCount: 1,
    });

    expect(stale).not.toBeNull();
    expect(stale?.warningCount).toBe(1);

    const rebuilt = buildBundle('diagram_theta', {
      state: {
        ...template.state,
        managedState: 'managed',
      },
    });

    manager.saveDiagramBundle(rebuilt);

    const refreshed = manager.refreshManagedSelection(stale);

    expect(refreshed).not.toBeNull();
    expect(refreshed?.mode).toBe('semantic');
    expect(refreshed?.managedState).toBe('managed');
    expect(refreshed?.warnings).toEqual([]);
    expect(refreshed?.warningCount).toBe(0);
  });

  it('treats same-diagram selection as diagram scope when no shared semantic prefix exists', () => {
    const manager = createManager();
    const bundle = buildBundle('diagram_theta');

    manager.saveDiagramBundle(bundle);

    const selection = manager.getManagedSelection([
      `${bundle.spec.diagramId}-panel-shape`,
      `${bundle.spec.diagramId}-connector`,
    ]);

    expect(selection).not.toBeNull();
    expect(selection?.mode).toBe('diagram');
    expect(selection?.canEdit).toBe(true);
    expect(selection?.semanticId).toBeUndefined();
    expect(selection?.diagramId).toBe(bundle.spec.diagramId);
  });

  it('returns conflict when selection spans multiple managed diagrams', () => {
    const manager = createManager();
    const first = buildBundle('diagram_alpha');
    const second = buildBundle('diagram_beta');

    manager.saveDiagramBundle(first);
    manager.saveDiagramBundle(second);

    const selection = manager.getManagedSelection([
      'diagram_alpha-block-shape',
      'diagram_beta-block-shape',
    ]);

    expect(selection?.mode).toBe('conflict');
    expect(selection?.canEdit).toBe(false);
    expect(selection?.reason).toBe('You can only edit one managed diagram at a time.');
  });

  it('degrades semantic selection to diagram scope after the semantic disappears', () => {
    const manager = createManager();
    const original = buildBundle('diagram_gamma');
    const updated = buildBundle('diagram_gamma', {
      spec: {
        ...original.spec,
        components: original.spec.components.filter(
          (component) => component.id !== 'diagram_gamma.block',
        ),
      },
      manifest: {
        ...original.manifest,
        entries: original.manifest.entries.filter(
          (entry) => entry.semanticId !== 'diagram_gamma.block',
        ),
      },
    });

    manager.saveDiagramBundle(original);
    manager.saveDiagramBundle(updated);

    const refreshed = manager.refreshManagedSelection({
      mode: 'semantic',
      canEdit: true,
      diagramId: 'diagram_gamma',
      semanticId: 'diagram_gamma.block',
      semanticPath: 'diagram_gamma.block',
      editScope: 'semantic',
      title: original.summary.title,
      family: original.summary.family,
      managedState: original.state.managedState,
      warnings: [],
      warningCount: 0,
      selectedCount: 1,
    });

    expect(refreshed?.mode).toBe('diagram');
    expect(refreshed?.semanticId).toBeUndefined();
    expect(refreshed?.warningCount).toBe(0);
    expect(refreshed?.warnings).toEqual([]);
  });

  it('normalizes stale managed scope and deduplicates warnings when saving bundles', () => {
    const manager = createManager();
    const bundle = buildBundle('diagram_delta', {
      state: {
        diagramId: 'diagram_delta',
        managedState: 'semi_managed',
        managedScope: ['missing.semantic', 'missing.semantic'],
        unmanagedPaths: ['matrix.scan.cell_0_0', 'matrix.scan.cell_0_0'],
        warnings: ['Matrix edits need review.', 'Matrix edits need review.'],
        lastEditSource: 'manual',
        lastPatchSummary: 'Manual edit requires review',
      },
    });

    manager.saveDiagramBundle(bundle);

    const persisted = manager.getDiagramBundle('diagram_delta');

    expect(persisted).not.toBeNull();
    expect(persisted?.state.managedScope).toEqual([
      'diagram_delta.panel',
      'diagram_delta.block',
    ]);
    expect(persisted?.state.unmanagedPaths).toEqual(['matrix.scan.cell_0_0']);
    expect(persisted?.state.warnings).toEqual(['Matrix edits need review.']);
    expect(persisted?.summary.managedState).toBe('semi_managed');
  });

  it('transitions from semi_managed to managed and clears warning state on rebuild-like save', () => {
    const manager = createManager();
    const beforeRebuild = buildBundle('diagram_epsilon', {
      state: {
        diagramId: 'diagram_epsilon',
        managedState: 'semi_managed',
        managedScope: ['diagram_epsilon.panel', 'diagram_epsilon.block'],
        unmanagedPaths: ['matrix.scan.cell_0_0'],
        warnings: ['Manual edits on diagram_epsilon.block need review.'],
        lastEditSource: 'manual',
        lastPatchSummary: 'Manual edit requires review',
      },
    });
    const afterRebuild = buildBundle('diagram_epsilon', {
      state: {
        diagramId: 'diagram_epsilon',
        managedState: 'managed',
        managedScope: ['diagram_epsilon.panel', 'diagram_epsilon.block'],
        unmanagedPaths: ['matrix.scan.cell_0_0'],
        warnings: ['Should be cleared by managed state'],
        lastEditSource: 'system',
        lastPatchSummary: 'Rebuild recovered',
      },
    });

    manager.saveDiagramBundle(beforeRebuild);
    manager.saveDiagramBundle(afterRebuild);

    const persisted = manager.getDiagramBundle('diagram_epsilon');

    expect(persisted).not.toBeNull();
    expect(persisted?.state.managedState).toBe('managed');
    expect(persisted?.state.warnings).toEqual([]);
    expect(persisted?.state.unmanagedPaths).toEqual([]);
    expect(persisted?.state.managedScope).toEqual(['diagram_epsilon.panel', 'diagram_epsilon.block']);
    expect(persisted?.state.lastPatchSummary).toBe('Rebuild recovered');
  });

  it('aligns applyDiagramBundle with saveDiagramBundle managed-state normalization', () => {
    const manager = createManager();
    const beforeApply = buildBundle('diagram_kappa', {
      state: {
        ...buildBundle('diagram_kappa').state,
        managedState: 'semi_managed',
        unmanagedPaths: ['matrix.scan.cell_1_1'],
        warnings: ['Need rebuild'],
        managedScope: ['diagram_kappa.panel'],
        lastPatchSummary: 'Manual update before rebuild',
      },
    });

    manager.saveDiagramBundle(beforeApply);

    const rebuilt = buildBundle('diagram_kappa', {
      state: {
        ...buildBundle('diagram_kappa').state,
        managedState: 'managed',
        unmanagedPaths: ['matrix.scan.cell_1_1'],
        warnings: ['Should be removed by managed normalization'],
        managedScope: ['diagram_kappa.panel', 'diagram_kappa.block'],
        lastPatchSummary: 'Rebuild through apply',
      },
      previewElements: [
        ...beforeApply.previewElements,
      ],
    });

    manager.applyDiagramBundle(rebuilt);

    const persisted = manager.getDiagramBundle('diagram_kappa');
    expect(persisted).not.toBeNull();
    expect(persisted?.state.managedState).toBe('managed');
    expect(persisted?.state.warnings).toEqual([]);
    expect(persisted?.state.unmanagedPaths).toEqual([]);
    expect(persisted?.state.lastPatchSummary).toBe('Rebuild through apply');
  });

  it('keeps diagram target when remote rerender removes a semantic, without resetting to create_new', () => {
    const manager = createManager();
    const original = buildBundle('diagram_zeta');
    const remoteRerender = buildBundle('diagram_zeta', {
      spec: {
        ...original.spec,
        components: original.spec.components.filter(
          (component) => component.id !== 'diagram_zeta.block',
        ),
      },
      manifest: {
        ...original.manifest,
        entries: original.manifest.entries.filter(
          (entry) => entry.semanticId !== 'diagram_zeta.block',
        ),
      },
      summary: {
        ...original.summary,
        componentCount: original.summary.componentCount - 1,
      },
    });

    manager.saveDiagramBundle(original);
    manager.saveDiagramBundle(remoteRerender);

    const refreshed = manager.refreshManagedSelection({
      mode: 'semantic',
      canEdit: true,
      diagramId: 'diagram_zeta',
      semanticId: 'diagram_zeta.block',
      semanticPath: 'diagram_zeta.block',
      editScope: 'semantic',
      title: original.summary.title,
      family: original.summary.family,
      managedState: 'managed',
      warnings: [],
      warningCount: 0,
      selectedCount: 1,
    });

    expect(refreshed).not.toBeNull();
    expect(refreshed?.mode).toBe('diagram');
    expect(refreshed?.editScope).toBe('diagram');
    expect(refreshed?.diagramId).toBe('diagram_zeta');
    expect(refreshed?.semanticId).toBeUndefined();
    expect(refreshed?.warningCount).toBe(0);
    expect(refreshed?.warnings).toEqual([]);
  });

  it('degrades unknown semantic in refreshManagedSelectionTarget to diagram scope without creating error state', () => {
    const manager = createManager();
    const original = buildBundle('diagram_eta');

    manager.saveDiagramBundle(original);

    const selection = manager.getManagedSelection([
      `${original.spec.diagramId}-panel-shape`,
    ]);
    expect(selection).not.toBeNull();
    expect(selection?.mode).toBe('semantic');

    const refreshed = manager.refreshManagedSelection({
      ...selection,
      semanticId: 'diagram_eta.unknown',
      semanticPath: 'diagram_eta.unknown',
      canEdit: true,
      warningCount: 2,
      warnings: ['stale warning'],
    } as ManagedDiagramTarget);

    expect(refreshed).not.toBeNull();
    expect(refreshed?.mode).toBe('diagram');
    expect(refreshed?.diagramId).toBe('diagram_eta');
    expect(refreshed?.canEdit).toBe(true);
    expect(refreshed?.warnings).toEqual([]);
  });

  it('preserves selected diagram scope for stale semantics when other diagrams are updated', () => {
    const manager = createManager();
    const alpha = buildBundle('diagram_alpha');
    const beta = buildBundle('diagram_beta');

    manager.saveDiagramBundle(alpha);
    manager.saveDiagramBundle(beta);

    const unknownAlphaSelection = {
      mode: 'semantic',
      canEdit: true,
      diagramId: 'diagram_alpha',
      semanticId: 'diagram_alpha.unknown',
      semanticPath: 'diagram_alpha.unknown',
      editScope: 'semantic',
      title: alpha.summary.title,
      family: alpha.summary.family,
      managedState: alpha.state.managedState,
      warnings: ['stale warning'],
      warningCount: 1,
      selectedCount: 1,
    } as ManagedDiagramTarget;

    const staleRefreshed = manager.refreshManagedSelection(unknownAlphaSelection);

    expect(staleRefreshed).not.toBeNull();
    expect(staleRefreshed?.mode).toBe('diagram');
    expect(staleRefreshed?.diagramId).toBe('diagram_alpha');
    expect(staleRefreshed?.warningCount).toBe(0);

    const updatedBeta = buildBundle('diagram_beta', {
      summary: {
        ...beta.summary,
        componentCount: beta.summary.componentCount + 1,
      },
    });
    manager.saveDiagramBundle(updatedBeta);

    const afterCrossUpdate = manager.refreshManagedSelection(staleRefreshed);
    expect(afterCrossUpdate).not.toBeNull();
    expect(afterCrossUpdate?.mode).toBe('diagram');
    expect(afterCrossUpdate?.diagramId).toBe('diagram_alpha');
    expect(afterCrossUpdate?.warningCount).toBe(0);
  });
});
