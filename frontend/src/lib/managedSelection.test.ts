import { describe, expect, it } from 'vitest';

import type { DiagramBundle, ManagedDiagramTarget } from '../types';
import {
  isKnownSemantic,
  normalizeManagedScope,
  refreshManagedSelectionTarget,
  resolveSharedSemanticId,
} from './managedSelection';

function buildBundle(): DiagramBundle {
  return {
    spec: {
      diagramId: 'diagram_test',
      diagramType: 'paper_figure',
      family: 'paper_figure',
      version: 1,
      title: 'Managed figure',
      prompt: 'Draw a managed paper figure',
      style: {},
      layout: {},
      components: [
        {
          id: 'stack.encoder',
          componentType: 'container',
          label: 'Encoder',
          text: 'Encoder',
          shape: 'rectangle',
          x: 80,
          y: 80,
          width: 240,
          height: 180,
          style: {},
          data: {},
        },
        {
          id: 'stack.encoder.block1',
          componentType: 'block',
          label: 'Block 1',
          text: 'Block 1',
          shape: 'rectangle',
          x: 100,
          y: 110,
          width: 200,
          height: 48,
          style: {},
          data: {},
        },
        {
          id: 'stack.encoder.block2',
          componentType: 'block',
          label: 'Block 2',
          text: 'Block 2',
          shape: 'rectangle',
          x: 100,
          y: 170,
          width: 200,
          height: 48,
          style: {},
          data: {},
        },
      ],
      connectors: [
        {
          id: 'connector.flow',
          connectorType: 'arrow',
          fromComponent: 'stack.encoder.block1',
          toComponent: 'stack.encoder.block2',
          label: 'flow',
          style: {},
        },
      ],
      groups: [],
      annotations: [
        {
          id: 'annotation.caption',
          annotationType: 'caption',
          text: 'Caption',
          x: 80,
          y: 280,
          width: 240,
          height: 40,
          style: {},
        },
      ],
      assets: [],
      layoutConstraints: {},
      overrides: {},
    },
    manifest: {
      diagramId: 'diagram_test',
      renderVersion: 1,
      entries: [],
    },
    state: {
      diagramId: 'diagram_test',
      managedState: 'semi_managed',
      managedScope: ['stack.encoder'],
      unmanagedPaths: ['matrix.cell.1'],
      warnings: ['Matrix edits need review.'],
      lastEditSource: 'user',
      lastPatchSummary: 'Manual edit',
    },
    previewElements: [],
    previewFiles: {},
    summary: {
      diagramId: 'diagram_test',
      title: 'Managed figure',
      family: 'paper_figure',
      componentCount: 3,
      connectorCount: 1,
      managedState: 'semi_managed',
      managedElementCount: 6,
    },
  };
}

function buildSelection(
  overrides: Partial<ManagedDiagramTarget> = {},
): ManagedDiagramTarget {
  return {
    mode: 'semantic',
    canEdit: true,
    diagramId: 'diagram_test',
    semanticId: 'stack.encoder.block1',
    semanticPath: 'stack.encoder.block1',
    editScope: 'semantic',
    title: 'Managed figure',
    family: 'paper_figure',
    managedState: 'managed',
    warnings: [],
    warningCount: 0,
    selectedCount: 1,
    ...overrides,
  };
}

describe('managedSelection helpers', () => {
  it('detects known semantics across components, connectors, and title', () => {
    const bundle = buildBundle();

    expect(isKnownSemantic(bundle, 'diagram.title')).toBe(true);
    expect(isKnownSemantic(bundle, 'stack.encoder.block1')).toBe(true);
    expect(isKnownSemantic(bundle, 'connector.flow')).toBe(true);
    expect(isKnownSemantic(bundle, 'missing.node')).toBe(false);
  });

  it('resolves the longest known shared semantic prefix', () => {
    const bundle = buildBundle();

    expect(
      resolveSharedSemanticId(bundle, [
        'stack.encoder.block1.text',
        'stack.encoder.block2.label',
      ]),
    ).toBe('stack.encoder');
  });

  it('returns undefined when no valid shared semantic exists', () => {
    const bundle = buildBundle();

    expect(
      resolveSharedSemanticId(bundle, [
        'stack.encoder.block1',
        'annotation.caption',
      ]),
    ).toBeUndefined();
  });

  it('returns undefined for a single unknown semantic id', () => {
    const bundle = buildBundle();

    expect(resolveSharedSemanticId(bundle, ['missing.semantic'])).toBeUndefined();
  });

  it('normalizes managed scope to known semantics and removes duplicates', () => {
    const bundle = buildBundle();

    expect(
      normalizeManagedScope(bundle, [
        'connector.flow',
        'stack.encoder.block1',
        'connector.flow',
        'missing.node',
      ]),
    ).toEqual(['connector.flow', 'stack.encoder.block1']);
  });

  it('falls back to diagram scope when managed scope only contains missing semantics', () => {
    const bundle = buildBundle();

    expect(
      normalizeManagedScope(bundle, ['missing.branch', 'missing.branch.child']),
    ).toEqual([
      'stack.encoder',
      'stack.encoder.block1',
      'stack.encoder.block2',
    ]);
  });

  it('degrades semantic selection to diagram scope when the semantic disappears', () => {
    const bundle = buildBundle();
    const refreshed = refreshManagedSelectionTarget(
      bundle,
      buildSelection({ semanticId: 'stack.encoder.block9', semanticPath: 'stack.encoder.block9' }),
    );

    expect(refreshed).not.toBeNull();
    expect(refreshed?.mode).toBe('diagram');
    expect(refreshed?.editScope).toBe('diagram');
    expect(refreshed?.semanticId).toBeUndefined();
    expect(refreshed?.warnings).toEqual(['Matrix edits need review.']);
    expect(refreshed?.warningCount).toBe(1);
  });
});
