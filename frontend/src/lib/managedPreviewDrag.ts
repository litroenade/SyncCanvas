import type { DiagramBundle } from '../types';
import type { BinaryFiles, ExcalidrawElement } from './yjs';

export const MANAGED_PREVIEW_DRAG_MIME = 'application/x-sync-canvas-managed-preview';
export const MANAGED_PREVIEW_APPLIED_EVENT = 'sync-canvas:managed-preview-applied';

export interface ManagedPreviewDragPayload {
  messageId: string;
  elements: ExcalidrawElement[];
  files?: BinaryFiles;
  diagramBundle?: DiagramBundle;
}

interface ElementsBounds {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
  width: number;
  height: number;
  centerX: number;
  centerY: number;
}

const previewDragStore = new Map<string, ManagedPreviewDragPayload>();

function createDragToken(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `preview-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function storeManagedPreviewDragPayload(
  payload: ManagedPreviewDragPayload,
): string {
  const token = createDragToken();
  previewDragStore.set(token, payload);
  return token;
}

export function consumeManagedPreviewDragPayload(
  token: string | null | undefined,
): ManagedPreviewDragPayload | null {
  if (!token) {
    return null;
  }
  const payload = previewDragStore.get(token) ?? null;
  previewDragStore.delete(token);
  return payload;
}

export function getManagedPreviewDragToken(
  dataTransfer: Pick<DataTransfer, 'getData'> | null | undefined,
): string | null {
  if (!dataTransfer) {
    return null;
  }
  const token = dataTransfer.getData(MANAGED_PREVIEW_DRAG_MIME).trim();
  return token || null;
}

export function primeManagedPreviewDrag(
  dataTransfer: Pick<DataTransfer, 'setData' | 'effectAllowed'>,
  payload: ManagedPreviewDragPayload,
): string {
  const token = storeManagedPreviewDragPayload(payload);
  dataTransfer.setData(MANAGED_PREVIEW_DRAG_MIME, token);
  dataTransfer.setData('text/plain', 'sync-canvas-managed-preview');
  dataTransfer.effectAllowed = 'copy';
  return token;
}

export function translatePreviewElementsToScenePoint(
  elements: ExcalidrawElement[],
  target: { x: number; y: number },
): {
  elements: ExcalidrawElement[];
  deltaX: number;
  deltaY: number;
} {
  const visible = elements.filter((element) => !element.isDeleted);
  if (visible.length === 0) {
    return {
      elements: elements.map((element) => ({ ...element })),
      deltaX: 0,
      deltaY: 0,
    };
  }

  const minX = Math.min(...visible.map((element) => element.x));
  const minY = Math.min(...visible.map((element) => element.y));
  const maxX = Math.max(...visible.map((element) => element.x + element.width));
  const maxY = Math.max(...visible.map((element) => element.y + element.height));
  const centerX = minX + (maxX - minX) / 2;
  const centerY = minY + (maxY - minY) / 2;
  const deltaX = target.x - centerX;
  const deltaY = target.y - centerY;

  return {
    elements: elements.map((element) => ({
      ...element,
      x: element.x + deltaX,
      y: element.y + deltaY,
    })),
    deltaX,
    deltaY,
  };
}

export function getElementsBounds(
  elements: ExcalidrawElement[],
): ElementsBounds | null {
  const visible = elements.filter((element) => !element.isDeleted);
  if (visible.length === 0) {
    return null;
  }

  const minX = Math.min(...visible.map((element) => element.x));
  const minY = Math.min(...visible.map((element) => element.y));
  const maxX = Math.max(...visible.map((element) => element.x + element.width));
  const maxY = Math.max(...visible.map((element) => element.y + element.height));
  const width = maxX - minX;
  const height = maxY - minY;

  return {
    minX,
    minY,
    maxX,
    maxY,
    width,
    height,
    centerX: minX + width / 2,
    centerY: minY + height / 2,
  };
}

function boundsOverlap(
  left: ElementsBounds | null,
  right: ElementsBounds | null,
  padding: number,
): boolean {
  if (!left || !right) {
    return false;
  }

  return !(
    left.maxX + padding < right.minX
    || right.maxX + padding < left.minX
    || left.maxY + padding < right.minY
    || right.maxY + padding < left.minY
  );
}

export function placePreviewNearScenePoint(
  elements: ExcalidrawElement[],
  existingElements: ExcalidrawElement[],
  target: { x: number; y: number },
  options?: {
    padding?: number;
    gap?: number;
    maxAttempts?: number;
  },
): {
  elements: ExcalidrawElement[];
  deltaX: number;
  deltaY: number;
} {
  const padding = options?.padding ?? 80;
  const gap = options?.gap ?? 120;
  const maxAttempts = options?.maxAttempts ?? 8;
  const occupiedBounds = getElementsBounds(existingElements);
  const previewBounds = getElementsBounds(elements);

  const centered = translatePreviewElementsToScenePoint(elements, target);
  if (!boundsOverlap(getElementsBounds(centered.elements), occupiedBounds, padding)) {
    return centered;
  }

  if (!previewBounds || !occupiedBounds) {
    return centered;
  }

  const rightSideTarget = {
    x: occupiedBounds.maxX + gap + previewBounds.width / 2,
    y: Math.max(target.y, occupiedBounds.minY + previewBounds.height / 2),
  };
  const rightSidePlacement = translatePreviewElementsToScenePoint(elements, rightSideTarget);
  if (!boundsOverlap(getElementsBounds(rightSidePlacement.elements), occupiedBounds, padding)) {
    return rightSidePlacement;
  }

  const stepX = previewBounds.width + gap;
  const stepY = previewBounds.height + gap;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const candidate = translatePreviewElementsToScenePoint(elements, {
      x: rightSideTarget.x + stepX * attempt,
      y: rightSideTarget.y + stepY * attempt,
    });
    if (!boundsOverlap(getElementsBounds(candidate.elements), occupiedBounds, padding)) {
      return candidate;
    }
  }

  return rightSidePlacement;
}

export function translateDiagramBundle(
  bundle: DiagramBundle,
  deltaX: number,
  deltaY: number,
  previewElements?: Record<string, unknown>[],
): DiagramBundle {
  const translated = JSON.parse(JSON.stringify(bundle)) as DiagramBundle;

  translated.spec.components = translated.spec.components.map((component) => ({
    ...component,
    x: component.x + deltaX,
    y: component.y + deltaY,
  }));
  translated.spec.annotations = translated.spec.annotations.map((annotation) => ({
    ...annotation,
    x: annotation.x + deltaX,
    y: annotation.y + deltaY,
  }));
  translated.manifest.entries = translated.manifest.entries.map((entry) => ({
    ...entry,
    bounds: {
      ...entry.bounds,
      x: typeof entry.bounds.x === 'number' ? entry.bounds.x + deltaX : entry.bounds.x,
      y: typeof entry.bounds.y === 'number' ? entry.bounds.y + deltaY : entry.bounds.y,
    },
  }));

  if (typeof translated.spec.layout.titleX === 'number') {
    translated.spec.layout.titleX += deltaX;
  }
  if (typeof translated.spec.layout.titleY === 'number') {
    translated.spec.layout.titleY += deltaY;
  }
  if (previewElements) {
    translated.previewElements = previewElements;
  }

  return translated;
}
