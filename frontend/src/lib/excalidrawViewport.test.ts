import { describe, expect, it } from 'vitest';

import {
  buildViewportRepairAppState,
  filterFiniteSceneElements,
  normalizeViewportState,
  normalizeZoom,
} from './excalidrawViewport';
import type { ExcalidrawElement } from './yjs';

describe('excalidrawViewport helpers', () => {
  it('repairs invalid viewport numbers to sane defaults', () => {
    const normalized = normalizeViewportState({
      zoom: { value: Number.NaN },
      offsetLeft: Number.NaN,
      offsetTop: Number.NaN,
      scrollX: Number.NaN,
      scrollY: Number.NaN,
      width: Number.NaN,
      height: Number.NaN,
    });

    expect(normalized.zoom.value).toBe(1);
    expect(normalized.offsetLeft).toBe(0);
    expect(normalized.offsetTop).toBe(0);
    expect(normalized.scrollX).toBe(0);
    expect(normalized.scrollY).toBe(0);
    expect(normalized.width).toBeGreaterThan(0);
    expect(normalized.height).toBeGreaterThan(0);
  });

  it('only emits an app-state repair patch when the viewport is invalid', () => {
    expect(buildViewportRepairAppState({
      zoom: { value: 1.25 },
      offsetLeft: 0,
      offsetTop: 0,
      scrollX: 10,
      scrollY: 20,
      width: 1280,
      height: 720,
    })).toBeNull();

    expect(buildViewportRepairAppState({
      zoom: { value: Number.NaN },
      offsetLeft: 0,
      offsetTop: 0,
      scrollX: Number.NaN,
      scrollY: 20,
      width: 1280,
      height: Number.NaN,
    })).toEqual({
      zoom: { value: 1 },
      scrollX: 0,
      scrollY: 20,
    });
  });

  it('filters out scene elements with invalid geometry before they hit Excalidraw', () => {
    const elements: ExcalidrawElement[] = [
      { id: 'valid-node', type: 'rectangle', x: 10, y: 20, width: 100, height: 60 },
      { id: 'bad-node', type: 'rectangle', x: Number.NaN, y: 20, width: 100, height: 60 },
      {
        id: 'bad-arrow',
        type: 'arrow',
        x: 10,
        y: 20,
        width: 100,
        height: 60,
        points: [[0, 0], [Number.POSITIVE_INFINITY, 10]],
      },
    ];

    expect(filterFiniteSceneElements(elements).map((element) => element.id)).toEqual(['valid-node']);
  });

  it('normalizes zoom objects and bare zoom numbers', () => {
    expect(normalizeZoom({ value: 1.5 })).toEqual({ value: 1.5 });
    expect(normalizeZoom(2)).toEqual({ value: 2 });
    expect(normalizeZoom({ value: Number.NaN })).toEqual({ value: 1 });
  });
});
