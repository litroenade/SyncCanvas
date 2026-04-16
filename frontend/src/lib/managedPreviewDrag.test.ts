import { describe, expect, it } from 'vitest';

import {
  consumeManagedPreviewDragPayload,
  placePreviewNearScenePoint,
  storeManagedPreviewDragPayload,
  translateDiagramBundle,
  translatePreviewElementsToScenePoint,
} from './managedPreviewDrag';
import type { DiagramBundle } from '../types';
import type { ExcalidrawElement } from './yjs';

function buildBundle(): DiagramBundle {
  return {
    spec: {
      diagramId: 'diagram-1',
      diagramType: 'paper_figure',
      family: 'transformer',
      version: 1,
      title: 'Transformer',
      prompt: 'prompt',
      style: {},
      layout: { titleX: 0, titleY: 0 },
      components: [
        {
          id: 'encoder',
          componentType: 'block',
          label: 'Encoder',
          text: 'Encoder',
          shape: 'rectangle',
          x: 0,
          y: 0,
          width: 100,
          height: 40,
          style: {},
          data: {},
        },
      ],
      connectors: [],
      groups: [],
      annotations: [],
      assets: [],
      layoutConstraints: {},
      overrides: {},
    },
    manifest: {
      diagramId: 'diagram-1',
      renderVersion: 1,
      entries: [
        {
          semanticId: 'encoder',
          role: 'block',
          elementIds: ['node-1'],
          bounds: { x: 0, y: 0, width: 100, height: 40 },
          renderVersion: 1,
        },
      ],
    },
    state: {
      diagramId: 'diagram-1',
      managedState: 'managed',
      managedScope: [],
      unmanagedPaths: [],
      warnings: [],
      lastEditSource: 'system',
      lastPatchSummary: 'Created',
    },
    previewElements: [{ id: 'node-1', x: 0, y: 0, width: 100, height: 40 }],
    previewFiles: {},
    summary: {
      diagramId: 'diagram-1',
      title: 'Transformer',
      family: 'transformer',
      componentCount: 1,
      connectorCount: 0,
      managedState: 'managed',
      managedElementCount: 1,
    },
  };
}

describe('managedPreviewDrag helpers', () => {
  it('translates preview elements so their bounds center matches the drop point', () => {
    const elements: ExcalidrawElement[] = [
      { id: 'node-1', type: 'rectangle', x: 10, y: 20, width: 80, height: 40 },
      { id: 'node-2', type: 'rectangle', x: 110, y: 20, width: 80, height: 40 },
    ];

    const translated = translatePreviewElementsToScenePoint(elements, { x: 300, y: 200 });

    expect(translated.deltaX).toBe(200);
    expect(translated.deltaY).toBe(160);
    expect(translated.elements[0].x).toBe(210);
    expect(translated.elements[0].y).toBe(180);
    expect(translated.elements[1].x).toBe(310);
  });

  it('translates the diagram bundle alongside dropped preview elements', () => {
    const previewElements = [{ id: 'node-1', x: 150, y: 200, width: 100, height: 40 }];
    const translated = translateDiagramBundle(buildBundle(), 150, 200, previewElements);

    expect(translated.spec.components[0].x).toBe(150);
    expect(translated.spec.components[0].y).toBe(200);
    expect(translated.manifest.entries[0].bounds.x).toBe(150);
    expect(translated.manifest.entries[0].bounds.y).toBe(200);
    expect(translated.previewElements).toEqual(previewElements);
  });

  it('places a preview at the requested scene point when nothing occupies it', () => {
    const elements: ExcalidrawElement[] = [
      { id: 'node-1', type: 'rectangle', x: 0, y: 0, width: 100, height: 40 },
    ];

    const placed = placePreviewNearScenePoint(elements, [], { x: 300, y: 200 });

    expect(placed.deltaX).toBe(250);
    expect(placed.deltaY).toBe(180);
    expect(placed.elements[0].x).toBe(250);
    expect(placed.elements[0].y).toBe(180);
  });

  it('moves the preview to the right when the requested point overlaps the existing scene', () => {
    const elements: ExcalidrawElement[] = [
      { id: 'node-1', type: 'rectangle', x: 0, y: 0, width: 100, height: 40 },
    ];
    const existing: ExcalidrawElement[] = [
      { id: 'existing-1', type: 'rectangle', x: 200, y: 120, width: 220, height: 140 },
    ];

    const placed = placePreviewNearScenePoint(elements, existing, { x: 300, y: 200 });

    expect(placed.elements[0].x).toBe(540);
    expect(placed.elements[0].y).toBe(180);
    expect(placed.deltaX).toBe(540);
    expect(placed.deltaY).toBe(180);
  });

  it('round-trips drag payloads through the in-memory store', () => {
    const token = storeManagedPreviewDragPayload({
      messageId: 'assistant-1',
      elements: [{ id: 'node-1', type: 'rectangle', x: 0, y: 0, width: 10, height: 10 }],
    });

    const payload = consumeManagedPreviewDragPayload(token);

    expect(payload?.messageId).toBe('assistant-1');
    expect(consumeManagedPreviewDragPayload(token)).toBeNull();
  });
});
