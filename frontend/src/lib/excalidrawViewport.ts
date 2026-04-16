import type { ExcalidrawElement } from './yjs';

type ZoomLike = { value?: number } | number | null | undefined;

interface ViewportStateLike {
  zoom?: ZoomLike;
  offsetLeft?: number;
  offsetTop?: number;
  scrollX?: number;
  scrollY?: number;
  width?: number;
  height?: number;
}

const DEFAULT_ZOOM_VALUE = 1;
const DEFAULT_VIEWPORT_WIDTH = 1280;
const DEFAULT_VIEWPORT_HEIGHT = 720;

function finiteNumber(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function hasFinitePositiveZoom(zoom: ZoomLike): boolean {
  if (typeof zoom === 'number') {
    return Number.isFinite(zoom) && zoom > 0;
  }
  if (typeof zoom === 'object' && zoom !== null && 'value' in zoom) {
    return typeof zoom.value === 'number' && Number.isFinite(zoom.value) && zoom.value > 0;
  }
  return false;
}

function viewportFallbackWidth(): number {
  if (typeof window !== 'undefined' && Number.isFinite(window.innerWidth) && window.innerWidth > 0) {
    return window.innerWidth;
  }
  return DEFAULT_VIEWPORT_WIDTH;
}

function viewportFallbackHeight(): number {
  if (typeof window !== 'undefined' && Number.isFinite(window.innerHeight) && window.innerHeight > 0) {
    return window.innerHeight;
  }
  return DEFAULT_VIEWPORT_HEIGHT;
}

export function normalizeZoom(zoom: ZoomLike): { value: number } {
  if (typeof zoom === 'number' && Number.isFinite(zoom) && zoom > 0) {
    return { value: zoom };
  }
  if (
    typeof zoom === 'object'
    && zoom !== null
    && 'value' in zoom
    && typeof zoom.value === 'number'
    && Number.isFinite(zoom.value)
    && zoom.value > 0
  ) {
    return { value: zoom.value };
  }
  return { value: DEFAULT_ZOOM_VALUE };
}

export function normalizeViewportState(state: ViewportStateLike | null | undefined) {
  return {
    zoom: normalizeZoom(state?.zoom),
    offsetLeft: finiteNumber(state?.offsetLeft, 0),
    offsetTop: finiteNumber(state?.offsetTop, 0),
    scrollX: finiteNumber(state?.scrollX, 0),
    scrollY: finiteNumber(state?.scrollY, 0),
    width: finiteNumber(state?.width, viewportFallbackWidth()),
    height: finiteNumber(state?.height, viewportFallbackHeight()),
  };
}

export function buildViewportRepairAppState(
  state: ViewportStateLike | null | undefined,
): { zoom: { value: number }; scrollX: number; scrollY: number } | null {
  const needsRepair = !hasFinitePositiveZoom(state?.zoom)
    || !Number.isFinite(state?.scrollX)
    || !Number.isFinite(state?.scrollY)
    || !Number.isFinite(state?.width)
    || !Number.isFinite(state?.height)
    || !Number.isFinite(state?.offsetLeft)
    || !Number.isFinite(state?.offsetTop);
  if (!needsRepair) {
    return null;
  }
  const normalized = normalizeViewportState(state);
  return {
    zoom: normalized.zoom,
    scrollX: normalized.scrollX,
    scrollY: normalized.scrollY,
  };
}

function hasFinitePoint(point: unknown): boolean {
  return Array.isArray(point)
    && point.length === 2
    && typeof point[0] === 'number'
    && Number.isFinite(point[0])
    && typeof point[1] === 'number'
    && Number.isFinite(point[1]);
}

export function hasFiniteSceneGeometry(element: ExcalidrawElement): boolean {
  if (!Number.isFinite(element.x) || !Number.isFinite(element.y)) {
    return false;
  }
  if (!Number.isFinite(element.width) || !Number.isFinite(element.height)) {
    return false;
  }
  if (Array.isArray(element.points) && !element.points.every(hasFinitePoint)) {
    return false;
  }
  return true;
}

export function filterFiniteSceneElements(
  elements: readonly ExcalidrawElement[],
): ExcalidrawElement[] {
  return elements.filter(hasFiniteSceneGeometry);
}
