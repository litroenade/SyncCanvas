import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';

import type {
  DiagramBundle,
  DiagramComponent,
  DiagramSpec,
  ManagedDiagramTarget,
  ManagedElementRef,
} from '../types';
import { config } from '../config/env';
import {
  isKnownSemantic,
  normalizeManagedScope,
  refreshManagedSelectionTarget,
  resolveSharedSemanticId,
} from './managedSelection';

export interface ExcalidrawElement {
  id: string;
  type: string;
  x: number;
  y: number;
  width: number;
  height: number;
  isDeleted?: boolean;
  [key: string]: unknown;
}

export interface BinaryFileData {
  id: string;
  dataURL: string;
  created: number;
  mimeType: string;
  [key: string]: unknown;
}

export type BinaryFiles = Record<string, BinaryFileData>;

const DIAGRAM_SPECS_KEY = 'diagram_specs';
const DIAGRAM_MANIFESTS_KEY = 'diagram_manifests';
const DIAGRAM_STATE_KEY = 'diagram_state';
const DIAGRAM_INDEX_KEY = 'diagram_index';
const LOCAL_SCENE_APPLY_TTL_MS = 2000;

const TOP_LEVEL_COMPONENT_TYPES = new Set([
  'container',
  'block',
  'panel',
  'caption',
  'callout',
  'image_slot',
  'badge',
  'brace_or_bracket',
]);

interface ReverseSyncOptions {
  previousElements?: Map<string, ExcalidrawElement>;
  changedElementIds?: string[];
  deletedElementIds?: string[];
}

interface ResolveManagedSelectionOptions {
  preferExistingDiagram?: boolean;
}

interface PendingSceneApply {
  elementIds: string[];
  selection: ManagedDiagramTarget | null;
  createdAt: number;
}

export interface ConsumedSceneApply {
  applied: boolean;
  selection: ManagedDiagramTarget | null;
}

interface ReverseSyncEffect {
  changed: boolean;
  affectedSemanticIds: Set<string>;
  warnings: string[];
}

interface TouchedDiagramBundle {
  bundle: DiagramBundle;
  effect: ReverseSyncEffect;
}

export class ExcalidrawYjsManager {
  private _roomId: string | null = null;
  private _ydoc: Y.Doc | null = null;
  private _provider: WebsocketProvider | null = null;
  private _elementsArray: Y.Array<Y.Map<unknown>> | null = null;
  private _filesMap: Y.Map<string> | null = null;
  private _diagramSpecsMap: Y.Map<string> | null = null;
  private _diagramManifestsMap: Y.Map<string> | null = null;
  private _diagramStateMap: Y.Map<string> | null = null;
  private _diagramIndexMap: Y.Map<string> | null = null;
  private _undoManager: Y.UndoManager | null = null;
  private _listeners: (() => void)[] = [];
  private _pendingSceneApply: PendingSceneApply | null = null;

  get roomId() { return this._roomId; }
  get ydoc() { return this._ydoc; }
  get provider() { return this._provider; }
  get elementsArray() { return this._elementsArray; }
  get filesMap() { return this._filesMap; }
  get diagramSpecsMap() { return this._diagramSpecsMap; }
  get diagramManifestsMap() { return this._diagramManifestsMap; }
  get diagramStateMap() { return this._diagramStateMap; }
  get diagramIndexMap() { return this._diagramIndexMap; }
  get undoManager() { return this._undoManager; }
  get isConnected() { return this._provider !== null; }
  get isWsConnected() { return this._provider?.wsconnected ?? false; }

  getAwareness() { return this._provider?.awareness; }

  connect(roomId: string): void {
    if (this._roomId === roomId && this._provider) return;
    this._cleanup();
    this._roomId = roomId;
    this._ydoc = new Y.Doc();

    this._provider = new WebsocketProvider(config.wsBaseUrl, roomId, this._ydoc);
    this._attachMaps();
  }

  disconnect(): void {
    this._cleanup();
  }

  onDocChange(listener: () => void): void {
    this._listeners.push(listener);
  }

  offDocChange(listener: () => void): void {
    this._listeners = this._listeners.filter((item) => item !== listener);
  }

  private _notify(): void {
    this._listeners.forEach((listener) => listener());
  }

  private _attachMaps(): void {
    if (!this._ydoc) return;
    this._elementsArray = this._ydoc.getArray('elements');
    this._filesMap = this._ydoc.getMap('files');
    this._diagramSpecsMap = this._ydoc.getMap(DIAGRAM_SPECS_KEY);
    this._diagramManifestsMap = this._ydoc.getMap(DIAGRAM_MANIFESTS_KEY);
    this._diagramStateMap = this._ydoc.getMap(DIAGRAM_STATE_KEY);
    this._diagramIndexMap = this._ydoc.getMap(DIAGRAM_INDEX_KEY);
    this._undoManager = new Y.UndoManager(this._elementsArray);
  }

  private _toPlainObject(item: unknown): unknown {
    if (
      item
      && typeof item === 'object'
      && 'toJSON' in item
      && typeof (item as { toJSON: () => unknown }).toJSON === 'function'
    ) {
      return (item as { toJSON: () => unknown }).toJSON();
    }
    if (
      item
      && typeof item === 'object'
      && 'toArray' in item
      && typeof (item as { toArray: () => unknown[] }).toArray === 'function'
    ) {
      return (item as { toArray: () => unknown[] })
        .toArray()
        .map((value) => this._toPlainObject(value));
    }
    if (Array.isArray(item)) {
      return item.map((value) => this._toPlainObject(value));
    }
    if (item && typeof item === 'object') {
      const result: Record<string, unknown> = {};
      Object.entries(item).forEach(([key, value]) => {
        result[key] = this._toPlainObject(value);
      });
      return result;
    }
    return item;
  }

  private _findElementIndex(id: string): number {
    if (!this._elementsArray) return -1;
    for (let index = 0; index < this._elementsArray.length; index += 1) {
      if (this._elementsArray.get(index).get('id') === id) {
        return index;
      }
    }
    return -1;
  }

  private _elementToYMap(element: ExcalidrawElement): Y.Map<unknown> {
    const yMap = new Y.Map<unknown>();
    Object.entries(element).forEach(([key, value]) => yMap.set(key, value));
    return yMap;
  }

  private _readJson<T>(map: Y.Map<string> | null, key: string): T | null {
    if (!map) return null;
    const raw = map.get(key);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as T;
    } catch {
      return null;
    }
  }

  private _writeJson(map: Y.Map<string> | null, key: string, value: unknown): void {
    if (!map) return;
    map.set(key, JSON.stringify(value));
  }

  private _getElementSnapshot(id: string): ExcalidrawElement | null {
    if (!this._elementsArray) return null;
    const index = this._findElementIndex(id);
    if (index < 0) return null;
    return this._toPlainObject(this._elementsArray.get(index)) as ExcalidrawElement;
  }

  private _extractManagedRefFromElement(
    element: Record<string, unknown> | null | undefined,
  ): ManagedElementRef | null {
    if (!element || typeof element !== 'object') return null;
    const customData = element.customData;
    if (!customData || typeof customData !== 'object') return null;
    const syncCanvas = (customData as Record<string, unknown>).syncCanvas;
    if (!syncCanvas || typeof syncCanvas !== 'object') return null;

    const candidate = syncCanvas as Record<string, unknown>;
    if (
      typeof candidate.diagramId !== 'string'
      || typeof candidate.semanticId !== 'string'
      || typeof candidate.role !== 'string'
    ) {
      return null;
    }

    return {
      diagramId: candidate.diagramId,
      semanticId: candidate.semanticId,
      role: candidate.role,
      managed: candidate.managed !== false,
      renderVersion: typeof candidate.renderVersion === 'number' ? candidate.renderVersion : 1,
    };
  }

  private _isKnownSemantic(bundle: DiagramBundle, semanticId: string): boolean {
    return isKnownSemantic(bundle, semanticId);
  }

  private _buildManagedTarget(
    bundle: DiagramBundle,
    options: {
      mode: 'diagram' | 'semantic';
      semanticId?: string;
      canEdit?: boolean;
      reason?: string;
      selectedCount?: number;
    },
  ): ManagedDiagramTarget {
    const semanticId = options.mode === 'semantic' ? options.semanticId : undefined;
    return {
      mode: options.mode,
      canEdit: options.canEdit ?? true,
      reason: options.reason,
      diagramId: bundle.spec.diagramId,
      semanticId,
      semanticPath: semanticId,
      editScope: options.mode,
      title: bundle.summary.title,
      family: bundle.summary.family,
      managedState: bundle.state.managedState,
      warnings: [...bundle.state.warnings],
      warningCount: bundle.state.warnings.length,
      selectedCount: options.selectedCount ?? 0,
    };
  }

  private _buildCreateNewTarget(selectedCount: number): ManagedDiagramTarget {
    return {
      mode: 'create_new',
      canEdit: true,
      editScope: 'create_new',
      warnings: [],
      warningCount: 0,
      selectedCount,
    };
  }

  private _buildConflictTarget(reason: string, selectedCount: number): ManagedDiagramTarget {
    return {
      mode: 'conflict',
      canEdit: false,
      reason,
      editScope: 'diagram',
      warnings: [],
      warningCount: 0,
      selectedCount,
    };
  }

  private _resolveSharedSemanticId(bundle: DiagramBundle, semanticIds: string[]): string | undefined {
    return resolveSharedSemanticId(bundle, semanticIds);
  }

  private _collectDiagramElements(diagramId: string): ExcalidrawElement[] {
    return this.getElements().filter((element) => {
      if (element.isDeleted) return false;
      const ref = this._extractManagedRefFromElement(element as Record<string, unknown>);
      return ref?.diagramId === diagramId;
    });
  }

  private _clearDiagramIndex(diagramId: string): void {
    if (!this._diagramIndexMap) return;
    Array.from(this._diagramIndexMap.keys()).forEach((elementId) => {
      const existing = this._readJson<ManagedElementRef>(this._diagramIndexMap, elementId);
      if (existing?.diagramId === diagramId) {
        this._diagramIndexMap?.delete(elementId);
      }
    });
  }

  private _writeDiagramIndex(bundle: DiagramBundle, sourceElements: ExcalidrawElement[]): void {
    if (!this._diagramIndexMap) return;
    const indexed = new Set<string>();

    sourceElements.forEach((element) => {
      const ref = this._extractManagedRefFromElement(element as Record<string, unknown>);
      if (!ref || ref.diagramId !== bundle.spec.diagramId) return;
      this._writeJson(this._diagramIndexMap, element.id, ref);
      indexed.add(element.id);
    });

    bundle.manifest.entries.forEach((entry) => {
      entry.elementIds.forEach((elementId) => {
        if (indexed.has(elementId)) return;
        this._writeJson(this._diagramIndexMap, elementId, {
          diagramId: bundle.spec.diagramId,
          semanticId: entry.semanticId,
          role: entry.role,
          managed: bundle.state.managedState !== 'unmanaged',
          renderVersion: bundle.manifest.renderVersion,
        });
      });
    });
  }

  private _writeDiagramMaps(bundle: DiagramBundle, sourceElements?: ExcalidrawElement[]): void {
    this._writeJson(this._diagramSpecsMap, bundle.spec.diagramId, bundle.spec);
    this._writeJson(this._diagramManifestsMap, bundle.spec.diagramId, bundle.manifest);
    this._writeJson(this._diagramStateMap, bundle.spec.diagramId, bundle.state);
    this._clearDiagramIndex(bundle.spec.diagramId);
    this._writeDiagramIndex(
      bundle,
      sourceElements && sourceElements.length > 0
        ? sourceElements
        : this._collectDiagramElements(bundle.spec.diagramId),
    );
  }

  private _logManagedEvent(
    level: 'info' | 'warn',
    message: string,
    details: Record<string, unknown>,
  ): void {
    const logger = level === 'warn' ? console.warn : console.info;
    logger(`[managed-diagram] ${message}`, details);
  }

  private _normalizeBundleState(bundle: DiagramBundle): void {
    bundle.state.managedScope = normalizeManagedScope(bundle, bundle.state.managedScope);
    bundle.state.unmanagedPaths = Array.from(new Set(bundle.state.unmanagedPaths));
    bundle.state.warnings = Array.from(new Set(bundle.state.warnings));

    if (bundle.state.managedState === 'managed') {
      bundle.state.unmanagedPaths = [];
      bundle.state.warnings = [];
    }
  }

  getElements(): ExcalidrawElement[] {
    if (!this._elementsArray) return [];
    return this._elementsArray
      .toArray()
      .map((item) => this._toPlainObject(item) as ExcalidrawElement)
      .filter(Boolean);
  }

  syncElements(elements: readonly ExcalidrawElement[]): void {
    if (!this._ydoc || !this._elementsArray) return;
    const elementsArray = this._elementsArray;
    this._ydoc.transact(() => {
      const nextIds = new Set<string>();

      elements.forEach((element) => {
        nextIds.add(element.id);
        const index = this._findElementIndex(element.id);
        if (index >= 0) {
          const yMap = elementsArray.get(index);
          Object.entries(element).forEach(([key, value]) => {
            if (JSON.stringify(yMap.get(key)) !== JSON.stringify(value)) {
              yMap.set(key, value);
            }
          });
        } else {
          elementsArray.push([this._elementToYMap(element)]);
        }
      });

      for (let index = elementsArray.length - 1; index >= 0; index -= 1) {
        const id = elementsArray.get(index).get('id') as string;
        if (id && !nextIds.has(id)) {
          elementsArray.delete(index, 1);
        }
      }
    }, 'excalidraw-sync');
  }

  getFiles(): BinaryFiles {
    if (!this._filesMap) return {};
    const files: BinaryFiles = {};
    this._filesMap.forEach((json, key) => {
      try {
        files[key] = JSON.parse(json);
      } catch {
        /* noop */
      }
    });
    return files;
  }

  syncFiles(files: BinaryFiles): void {
    if (!this._ydoc || !this._filesMap) return;
    this._ydoc.transact(() => {
      Object.entries(files).forEach(([id, fileData]) => {
        if (!this._filesMap?.has(id)) {
          this._filesMap?.set(id, JSON.stringify(fileData));
        }
      });
    }, 'excalidraw-files-sync');
  }

  addElement(element: ExcalidrawElement): void {
    if (!this._ydoc || !this._elementsArray) return;
    this._ydoc.transact(() => {
      this._elementsArray?.push([this._elementToYMap(element)]);
    }, 'excalidraw-add');
  }

  updateElement(id: string, updates: Partial<ExcalidrawElement>): void {
    if (!this._ydoc || !this._elementsArray) return;
    const index = this._findElementIndex(id);
    if (index < 0) return;
    this._ydoc.transact(() => {
      const yMap = this._elementsArray?.get(index);
      Object.entries(updates).forEach(([key, value]) => yMap?.set(key, value));
    }, 'excalidraw-update');
  }

  deleteElements(ids: string[]): void {
    if (!this._ydoc || !this._elementsArray) return;
    const elementsArray = this._elementsArray;
    const idSet = new Set(ids);
    this._ydoc.transact(() => {
      for (let index = elementsArray.length - 1; index >= 0; index -= 1) {
        const id = elementsArray.get(index).get('id') as string;
        if (id && idSet.has(id)) {
          elementsArray.delete(index, 1);
        }
      }
    }, 'excalidraw-delete');
  }

  clearElements(): void {
    if (!this._ydoc || !this._elementsArray) return;
    const elementsArray = this._elementsArray;
    this._ydoc.transact(() => {
      elementsArray.delete(0, elementsArray.length);
    }, 'excalidraw-clear');
  }

  saveDiagramBundle(bundle: DiagramBundle): void {
    if (!this._ydoc) return;
    this._refreshBundleSummary(bundle);
    this._ydoc.transact(() => {
      this._writeDiagramMaps(
        bundle,
        (bundle.previewElements as ExcalidrawElement[]).filter(Boolean),
      );
    }, 'diagram-bundle-sync');
    this._logManagedEvent('info', 'persisted diagram bundle to yjs maps', {
      diagramId: bundle.spec.diagramId,
      managedState: bundle.state.managedState,
      warningCount: bundle.state.warnings.length,
      scopeSize: bundle.state.managedScope.length,
    });
  }

  applyDiagramBundle(bundle: DiagramBundle): void {
    if (!this._ydoc || !this._elementsArray) return;
    const previewElements = (bundle.previewElements as ExcalidrawElement[]).filter(Boolean);
    this._refreshBundleSummary(bundle);

    this._ydoc.transact(() => {
      this._writeDiagramMaps(bundle, previewElements);

      const renderedIds = new Set(previewElements.map((element) => element.id));
      const existingIds = new Set<string>();

      this.getElements().forEach((element) => {
        const ref = this._extractManagedRefFromElement(element as Record<string, unknown>);
        if (ref?.diagramId === bundle.spec.diagramId) {
          existingIds.add(element.id);
        }
      });

      previewElements.forEach((element) => {
        const index = this._findElementIndex(element.id);
        if (index >= 0) {
          const yMap = this._elementsArray?.get(index);
          Object.entries(element).forEach(([key, value]) => {
            yMap?.set(key, value);
          });
        } else {
          this._elementsArray?.push([this._elementToYMap(element)]);
        }
      });

      Array.from(existingIds)
        .filter((elementId) => !renderedIds.has(elementId))
        .forEach((elementId) => {
          const index = this._findElementIndex(elementId);
          if (index >= 0) {
            this._elementsArray?.get(index).set('isDeleted', true);
          }
        });
    }, 'diagram-bundle-apply');
    this._logManagedEvent('info', 'applied diagram bundle to managed scene', {
      diagramId: bundle.spec.diagramId,
      renderedCount: previewElements.length,
      managedState: bundle.state.managedState,
      warningCount: bundle.state.warnings.length,
    });
  }

  stageLocalSceneApply(elementIds: string[], selection: ManagedDiagramTarget | null): void {
    this._pendingSceneApply = {
      elementIds: Array.from(new Set(elementIds)),
      selection: selection
        ? {
          ...selection,
          warnings: [...selection.warnings],
        }
        : null,
      createdAt: Date.now(),
    };
  }

  consumeLocalSceneApply(elements: readonly ExcalidrawElement[]): ConsumedSceneApply {
    const pending = this._pendingSceneApply;
    if (!pending) {
      return { applied: false, selection: null };
    }

    if (Date.now() - pending.createdAt > LOCAL_SCENE_APPLY_TTL_MS) {
      this._pendingSceneApply = null;
      return { applied: false, selection: null };
    }

    const currentIds = new Set(elements.map((element) => element.id));
    const hasExpectedElement = pending.elementIds.some((elementId) => currentIds.has(elementId));
    if (!hasExpectedElement) {
      return { applied: false, selection: null };
    }

    this._pendingSceneApply = null;
    return {
      applied: true,
      selection: pending.selection
        ? this.refreshManagedSelection(pending.selection) ?? pending.selection
        : null,
    };
  }

  getDiagramBundle(diagramId: string): DiagramBundle | null {
    const spec = this._readJson<DiagramSpec>(this._diagramSpecsMap, diagramId);
    const manifest = this._readJson<DiagramBundle['manifest']>(this._diagramManifestsMap, diagramId);
    const state = this._readJson<DiagramBundle['state']>(this._diagramStateMap, diagramId);
    if (!spec || !manifest || !state) return null;

    const bundle: DiagramBundle = {
      spec,
      manifest,
      state,
      previewElements: [],
      previewFiles: {},
      summary: {
        diagramId,
        title: spec.title || spec.diagramType,
        family: spec.family,
        componentCount: spec.components.length,
        connectorCount: spec.connectors.length,
        managedState: state.managedState,
        managedElementCount: manifest.entries.reduce(
          (total, entry) => total + entry.elementIds.length,
          0,
        ),
      },
    };
    this._refreshBundleSummary(bundle);
    return bundle;
  }

  listDiagramBundles(): DiagramBundle[] {
    if (!this._diagramSpecsMap) return [];
    return Array.from(this._diagramSpecsMap.keys())
      .map((diagramId) => this.getDiagramBundle(diagramId))
      .filter((bundle): bundle is DiagramBundle => bundle !== null);
  }

  getManagedElementRef(
    elementId: string,
    element?: ExcalidrawElement | null,
  ): ManagedElementRef | null {
    const fromElement = this._extractManagedRefFromElement(
      (element ?? this._getElementSnapshot(elementId)) as Record<string, unknown>,
    );
    if (fromElement) return fromElement;
    return this._readJson<ManagedElementRef>(this._diagramIndexMap, elementId);
  }

  getManagedSelection(elementIds: string[]): ManagedDiagramTarget | null {
    if (elementIds.length === 0) {
      return this._buildCreateNewTarget(0);
    }

    const refs = elementIds
      .map((elementId) => this.getManagedElementRef(elementId))
      .filter((ref): ref is ManagedElementRef => ref !== null);
    const hasUnmanagedSelection = refs.length !== elementIds.length;

    if (refs.length === 0) {
      return this._buildCreateNewTarget(elementIds.length);
    }

    const diagramIds = Array.from(new Set(refs.map((ref) => ref.diagramId)));
    if (diagramIds.length > 1) {
      return this._buildConflictTarget(
        'You can only edit one managed diagram at a time.',
        elementIds.length,
      );
    }

    const diagramId = diagramIds[0];
    const bundle = this.getDiagramBundle(diagramId);
    if (!bundle) {
      return this._buildConflictTarget(
        'The selected managed diagram is missing or not loaded yet.',
        elementIds.length,
      );
    }

    const semanticIds = Array.from(new Set(refs.map((ref) => ref.semanticId)));
    const semanticId = hasUnmanagedSelection
      ? undefined
      : this._resolveSharedSemanticId(bundle, semanticIds);

    return this._buildManagedTarget(bundle, {
      mode: semanticId ? 'semantic' : 'diagram',
      semanticId,
      selectedCount: elementIds.length,
    });
  }

  private _preferExistingManagedSelection(
    derivedSelection: ManagedDiagramTarget | null,
    previousSelection: ManagedDiagramTarget | null,
  ): ManagedDiagramTarget | null {
    if (
      !previousSelection
      || previousSelection.mode === 'create_new'
      || previousSelection.mode === 'conflict'
    ) {
      return derivedSelection;
    }

    const refreshed = this.refreshManagedSelection(previousSelection);
    if (!refreshed) {
      return derivedSelection;
    }

    if (!derivedSelection || derivedSelection.mode === 'create_new') {
      return refreshed;
    }

    if (
      derivedSelection.mode === 'diagram'
      && refreshed.diagramId
      && refreshed.diagramId === derivedSelection.diagramId
    ) {
      return refreshed;
    }

    return derivedSelection;
  }

  resolveManagedSelection(
    elementIds: string[],
    previousSelection: ManagedDiagramTarget | null = null,
    options: ResolveManagedSelectionOptions = {},
  ): ManagedDiagramTarget | null {
    const derivedSelection = this.getManagedSelection(elementIds);
    if (!options.preferExistingDiagram) {
      return derivedSelection;
    }
    return this._preferExistingManagedSelection(derivedSelection, previousSelection);
  }

  refreshManagedSelection(selection: ManagedDiagramTarget | null): ManagedDiagramTarget | null {
    if (!selection) return null;
    if (selection.mode === 'create_new' || selection.mode === 'conflict') {
      return selection;
    }
    if (!selection.diagramId) {
      return null;
    }

    const bundle = this.getDiagramBundle(selection.diagramId);
    if (!bundle) {
      return null;
    }

    const refreshed = refreshManagedSelectionTarget(bundle, selection);
    if (!refreshed || refreshed.mode === 'create_new' || refreshed.mode === 'conflict') {
      return refreshed;
    }

    if (selection.mode === 'semantic' && refreshed.mode === 'diagram' && selection.semanticId) {
      this._logManagedEvent('info', 'selection degraded from semantic to diagram scope', {
        diagramId: selection.diagramId,
        previousSemanticId: selection.semanticId,
        managedState: bundle.state.managedState,
      });
    }

    return this._buildManagedTarget(bundle, {
      mode: refreshed.mode,
      semanticId: refreshed.semanticId,
      canEdit: refreshed.canEdit,
      reason: refreshed.reason,
      selectedCount: refreshed.selectedCount,
    });
  }

  reverseSyncManagedElements(
    elements: readonly ExcalidrawElement[],
    options: ReverseSyncOptions = {},
  ): void {
    if (!this._ydoc || !this._diagramIndexMap) return;

    const previousElements = options.previousElements;
    const changedElementIds = options.changedElementIds && options.changedElementIds.length > 0
      ? new Set(options.changedElementIds)
      : new Set(elements.map((element) => element.id));
    const deletedElementIds = options.deletedElementIds ?? [];
    const currentElements = new Map(elements.map((element) => [element.id, element]));
    const touched = new Map<string, TouchedDiagramBundle>();

    const ensureBundle = (diagramId: string): TouchedDiagramBundle | null => {
      if (!touched.has(diagramId)) {
        const bundle = this.getDiagramBundle(diagramId);
        if (bundle) {
          touched.set(diagramId, {
            bundle,
            effect: this._createReverseSyncEffect(),
          });
        }
      }
      return touched.get(diagramId) ?? null;
    };

    changedElementIds.forEach((elementId) => {
      const element = currentElements.get(elementId);
      if (!element) return;

      const ref = this.getManagedElementRef(elementId, element)
        ?? this.getManagedElementRef(elementId, previousElements?.get(elementId) ?? null);
      if (!ref) return;

      const touchedBundle = ensureBundle(ref.diagramId);
      if (!touchedBundle) return;
      this._mergeReverseSyncEffect(
        touchedBundle.effect,
        this._applyManagedElementToBundle(touchedBundle.bundle, ref, element),
      );
    });

    deletedElementIds.forEach((elementId) => {
      const ref = this.getManagedElementRef(elementId, previousElements?.get(elementId) ?? null);
      if (!ref) return;

      const touchedBundle = ensureBundle(ref.diagramId);
      if (!touchedBundle) return;
      this._mergeReverseSyncEffect(
        touchedBundle.effect,
        this._markDeletedManagedRef(touchedBundle.bundle, ref),
      );
    });

    touched.forEach(({ bundle, effect }) => {
      if (!effect.changed) return;
      bundle.state.lastEditSource = 'manual';
      if (effect.affectedSemanticIds.size > 0) {
        bundle.state.managedScope = normalizeManagedScope(
          bundle,
          Array.from(effect.affectedSemanticIds),
        );
      }
      bundle.state.lastPatchSummary = this._buildReverseSyncSummary(bundle, effect);
      this._refreshBundleSummary(bundle);
      this._logManagedEvent(effect.warnings.length > 0 ? 'warn' : 'info', 'reverse sync updated diagram bundle', {
        diagramId: bundle.spec.diagramId,
        managedState: bundle.state.managedState,
        affectedSemantics: Array.from(effect.affectedSemanticIds),
        warningCount: bundle.state.warnings.length,
      });
      this.saveDiagramBundle(bundle);
    });
  }

  private _createReverseSyncEffect(): ReverseSyncEffect {
    return {
      changed: false,
      affectedSemanticIds: new Set<string>(),
      warnings: [],
    };
  }

  private _mergeReverseSyncEffect(
    target: ReverseSyncEffect,
    next: ReverseSyncEffect | null,
  ): void {
    if (!next) return;
    target.changed = target.changed || next.changed;
    next.affectedSemanticIds.forEach((semanticId) => target.affectedSemanticIds.add(semanticId));
    next.warnings.forEach((warning) => {
      if (!target.warnings.includes(warning)) {
        target.warnings.push(warning);
      }
    });
  }

  private _effectForSemantic(
    semanticId: string,
    options: { changed?: boolean; warning?: string } = {},
  ): ReverseSyncEffect {
    const effect = this._createReverseSyncEffect();
    effect.changed = options.changed ?? true;
    effect.affectedSemanticIds.add(semanticId);
    if (options.warning) {
      effect.warnings.push(options.warning);
    }
    return effect;
  }

  private _refreshBundleSummary(bundle: DiagramBundle): void {
    this._normalizeBundleState(bundle);
    bundle.summary.title = bundle.spec.title || bundle.spec.diagramType;
    bundle.summary.family = bundle.spec.family;
    bundle.summary.componentCount = bundle.spec.components.length;
    bundle.summary.connectorCount = bundle.spec.connectors.length;
    bundle.summary.managedState = bundle.state.managedState;
    bundle.summary.managedElementCount = bundle.manifest.entries.reduce(
      (total, entry) => total + entry.elementIds.length,
      0,
    );
  }

  private _buildReverseSyncSummary(bundle: DiagramBundle, effect: ReverseSyncEffect): string {
    if (bundle.state.managedState !== 'managed' || effect.warnings.length > 0) {
      return 'Manual managed edit requires review';
    }
    if (effect.affectedSemanticIds.size === 1) {
      return `Updated ${Array.from(effect.affectedSemanticIds)[0]} from managed canvas edit`;
    }
    if (effect.affectedSemanticIds.size > 1) {
      return `Updated ${effect.affectedSemanticIds.size} managed elements from managed canvas edit`;
    }
    return 'Updated from managed canvas edit';
  }

  private _applyManagedElementToBundle(
    bundle: DiagramBundle,
    ref: ManagedElementRef,
    element: ExcalidrawElement,
  ): ReverseSyncEffect {
    const component = bundle.spec.components.find((item) => item.id === ref.semanticId);
    const annotation = bundle.spec.annotations.find((item) => item.id === ref.semanticId);
    const connector = bundle.spec.connectors.find((item) => item.id === ref.semanticId);
    const manifestEntry = bundle.manifest.entries.find(
      (item) => item.semanticId === ref.semanticId && item.role === ref.role,
    ) || bundle.manifest.entries.find((item) => item.semanticId === ref.semanticId);
    const isTopLevelComponent = component
      ? TOP_LEVEL_COMPONENT_TYPES.has(component.componentType)
      : false;
    let effect: ReverseSyncEffect;

    if (ref.semanticId === 'diagram.title') {
      effect = this._syncManagedTitle(bundle, ref, element);
    } else if (component && isTopLevelComponent) {
      effect = this._syncManagedComponent(bundle, component, ref, element);
    } else if (annotation && this._isKnownSemantic(bundle, annotation.id)) {
      effect = this._syncManagedAnnotation(annotation, ref, element);
    } else if (connector && (ref.role === 'connector' || ref.role === 'connector_label')) {
      effect = this._syncManagedConnector(bundle, connector, ref, element);
    } else {
      effect = this._markSemiManaged(bundle, ref.semanticId, `Manual edits on ${ref.semanticId} need review.`);
    }

    if (manifestEntry) {
      manifestEntry.bounds = {
        x: element.x,
        y: element.y,
        width: element.width,
        height: element.height,
      };
      effect.changed = true;
      effect.affectedSemanticIds.add(ref.semanticId);
    }
    return effect;
  }

  private _syncManagedTitle(
    bundle: DiagramBundle,
    ref: ManagedElementRef,
    element: ExcalidrawElement,
  ): ReverseSyncEffect {
    const text = typeof element.text === 'string' ? element.text.trim() : '';
    if (!text) {
      return this._markSemiManaged(bundle, ref.semanticId, 'Manual title edit needs review.');
    }
    bundle.spec.title = text;
    return this._effectForSemantic(ref.semanticId);
  }

  private _syncManagedComponent(
    bundle: DiagramBundle,
    component: DiagramComponent,
    ref: ManagedElementRef,
    element: ExcalidrawElement,
  ): ReverseSyncEffect {
    const isComponentTextRole = ref.role === `${component.componentType}_text`;
    if (ref.role !== component.componentType && !isComponentTextRole) {
      return this._markSemiManaged(
        bundle,
        ref.semanticId,
        `Manual edits on ${ref.semanticId} need review.`,
      );
    }

    if (isComponentTextRole) {
      const text = typeof element.text === 'string' ? element.text.trim() : '';
      if (!text) {
        return this._markSemiManaged(
          bundle,
          ref.semanticId,
          `Manual text edit on ${ref.semanticId} needs review.`,
        );
      }
      component.text = text;
      component.label = text;
      return this._effectForSemantic(ref.semanticId);
    }

    this._updateComponentFromElement(component, element);
    return this._effectForSemantic(ref.semanticId);
  }

  private _syncManagedAnnotation(
    annotation: DiagramBundle['spec']['annotations'][number],
    ref: ManagedElementRef,
    element: ExcalidrawElement,
  ): ReverseSyncEffect {
    this._updateAnnotationFromElement(annotation, element);
    return this._effectForSemantic(ref.semanticId);
  }

  private _syncManagedConnector(
    bundle: DiagramBundle,
    connector: DiagramBundle['spec']['connectors'][number],
    ref: ManagedElementRef,
    element: ExcalidrawElement,
  ): ReverseSyncEffect {
    const didUpdate = this._updateConnectorFromElement(bundle, connector, ref, element);
    if (!didUpdate) {
      return this._markSemiManaged(
        bundle,
        ref.semanticId,
        `Manual connector edit on ${ref.semanticId} needs review.`,
      );
    }
    return this._effectForSemantic(ref.semanticId);
  }

  private _updateComponentFromElement(component: DiagramComponent, element: ExcalidrawElement): void {
    component.x = element.x;
    component.y = element.y;
    component.width = element.width;
    component.height = element.height;
    component.style = {
      ...component.style,
      ...(element.strokeColor ? { strokeColor: element.strokeColor } : {}),
      ...(element.backgroundColor ? { backgroundColor: element.backgroundColor } : {}),
      ...(element.strokeStyle ? { strokeStyle: element.strokeStyle } : {}),
      ...(element.fillStyle ? { fillStyle: element.fillStyle } : {}),
      ...(element.fontSize ? { fontSize: element.fontSize } : {}),
    };
  }

  private _updateAnnotationFromElement(
    annotation: DiagramBundle['spec']['annotations'][number],
    element: ExcalidrawElement,
  ): void {
    annotation.x = element.x;
    annotation.y = element.y;
    annotation.width = element.width;
    annotation.height = element.height;

    if (typeof element.text === 'string' && element.text.trim()) {
      annotation.text = element.text.trim();
    }

    annotation.style = {
      ...annotation.style,
      ...(element.strokeColor ? { textColor: element.strokeColor } : {}),
      ...(element.fontSize ? { fontSize: element.fontSize } : {}),
    };
  }

  private _updateConnectorFromElement(
    bundle: DiagramBundle,
    connector: DiagramBundle['spec']['connectors'][number],
    ref: ManagedElementRef,
    element: ExcalidrawElement,
  ): boolean {
    connector.style = {
      ...connector.style,
      ...(element.strokeColor ? { strokeColor: element.strokeColor } : {}),
      ...(element.strokeStyle ? { strokeStyle: element.strokeStyle } : {}),
    };

    if (ref.role === 'connector_label') {
      if (typeof element.text === 'string' && element.text.trim()) {
        connector.label = element.text.trim();
      }
      return true;
    }

    if (typeof element.width !== 'number' || typeof element.height !== 'number') {
      return false;
    }

    const points = Array.isArray(element.points) ? element.points as number[][] : [];
    if (points.length < 2) {
      return true;
    }

    const start = {
      x: element.x + (points[0]?.[0] ?? 0),
      y: element.y + (points[0]?.[1] ?? 0),
    };
    const end = {
      x: element.x + (points[points.length - 1]?.[0] ?? 0),
      y: element.y + (points[points.length - 1]?.[1] ?? 0),
    };

    const topLevelComponents = bundle.spec.components.filter((component) => (
      TOP_LEVEL_COMPONENT_TYPES.has(component.componentType)
    ));
    const nearest = (point: { x: number; y: number }) => {
      const ranked = topLevelComponents
        .map((component) => {
          const centerX = component.x + component.width / 2;
          const centerY = component.y + component.height / 2;
          const distance = Math.hypot(centerX - point.x, centerY - point.y);
          return { component, distance };
        })
        .sort((left, right) => left.distance - right.distance);
      const match = ranked[0];
      return match && match.distance < 180 ? match.component.id : null;
    };

    const fromComponent = nearest(start);
    const toComponent = nearest(end);
    if (!fromComponent || !toComponent || fromComponent === toComponent) {
      return false;
    }

    connector.fromComponent = fromComponent;
    connector.toComponent = toComponent;
    return true;
  }

  private _markSemiManaged(
    bundle: DiagramBundle,
    semanticId: string,
    warning: string,
  ): ReverseSyncEffect {
    if (bundle.state.managedState === 'managed') {
      bundle.state.managedState = 'semi_managed';
    }
    if (!bundle.state.unmanagedPaths.includes(semanticId)) {
      bundle.state.unmanagedPaths.push(semanticId);
    }
    if (!bundle.state.warnings.includes(warning)) {
      bundle.state.warnings.push(warning);
    }
    this._logManagedEvent('warn', 'diagram entered semi-managed boundary', {
      diagramId: bundle.spec.diagramId,
      semanticId,
      warning,
      managedState: bundle.state.managedState,
    });
    return this._effectForSemantic(semanticId, { warning });
  }

  private _markDeletedManagedRef(
    bundle: DiagramBundle,
    ref: ManagedElementRef,
  ): ReverseSyncEffect {
    return this._markSemiManaged(
      bundle,
      ref.semanticId,
      `Deleted managed element ${ref.semanticId} needs review.`,
    );
  }

  previewData(data: ArrayBuffer): void {
    if (!this._roomId) return;
    const roomId = this._roomId;
    this._cleanup();
    this._roomId = roomId;
    this._ydoc = new Y.Doc();
    Y.applyUpdate(this._ydoc, new Uint8Array(data));
    this._attachMaps();
    this._notify();
  }

  exitPreview(): void {
    if (!this._roomId) return;
    const roomId = this._roomId;
    this.connect(roomId);
    this._notify();
  }

  private _cleanup(): void {
    if (this._provider) {
      this._provider.disconnect();
      this._provider.destroy();
      this._provider = null;
    }
    if (this._ydoc) {
      this._ydoc.destroy();
      this._ydoc = null;
    }
    this._elementsArray = null;
    this._filesMap = null;
    this._diagramSpecsMap = null;
    this._diagramManifestsMap = null;
    this._diagramStateMap = null;
    this._diagramIndexMap = null;
    this._undoManager = null;
    this._pendingSceneApply = null;
    this._roomId = null;
  }
}

export const yjsManager = new ExcalidrawYjsManager();
