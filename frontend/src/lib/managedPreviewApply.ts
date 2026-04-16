import { CaptureUpdateAction, viewportCoordsToSceneCoords } from '@excalidraw/excalidraw';
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types';

import type { DiagramBundle } from '../types';
import {
  buildViewportRepairAppState,
  filterFiniteSceneElements,
  normalizeViewportState,
} from './excalidrawViewport';
import {
  placePreviewNearScenePoint,
  translateDiagramBundle,
} from './managedPreviewDrag';
import { yjsManager, type BinaryFiles, type ExcalidrawElement } from './yjs';

type UpdateSceneArgs = Parameters<ExcalidrawImperativeAPI['updateScene']>[0];
type ScrollToContentTarget = Parameters<ExcalidrawImperativeAPI['scrollToContent']>[0];
type AddFilesArgs = Parameters<ExcalidrawImperativeAPI['addFiles']>[0];

export function applyManagedPreviewToCanvas(args: {
  excalidrawAPI: ExcalidrawImperativeAPI;
  elementsToAdd: ExcalidrawElement[];
  diagramBundle?: DiagramBundle;
  files?: BinaryFiles;
  placement?: 'preserve' | 'viewport-cascade';
}): void {
  const {
    excalidrawAPI,
    elementsToAdd,
    diagramBundle,
    files = {},
    placement = 'preserve',
  } = args;

  const existingElements = filterFiniteSceneElements(
    excalidrawAPI.getSceneElements() as unknown as ExcalidrawElement[],
  );
  let positionedElements = elementsToAdd;
  let positionedBundle = diagramBundle;

  if (placement === 'viewport-cascade') {
    const appState = normalizeViewportState(excalidrawAPI.getAppState());
    const viewportCenter = viewportCoordsToSceneCoords(
      {
        clientX: appState.offsetLeft + appState.width / 2,
        clientY: appState.offsetTop + appState.height / 2,
      },
      {
        zoom: appState.zoom as Parameters<typeof viewportCoordsToSceneCoords>[1]['zoom'],
        offsetLeft: appState.offsetLeft,
        offsetTop: appState.offsetTop,
        scrollX: appState.scrollX,
        scrollY: appState.scrollY,
      },
    );
    const translated = placePreviewNearScenePoint(
      elementsToAdd,
      existingElements,
      viewportCenter,
    );
    positionedElements = translated.elements;
    positionedBundle = diagramBundle
      ? translateDiagramBundle(
        diagramBundle,
        translated.deltaX,
        translated.deltaY,
        translated.elements,
      )
      : undefined;
  }

  const finitePositionedElements = filterFiniteSceneElements(positionedElements);
  if (finitePositionedElements.length > 0) {
    positionedElements = finitePositionedElements;
  } else {
    positionedElements = filterFiniteSceneElements(elementsToAdd);
    positionedBundle = diagramBundle;
  }

  const viewportRepair = buildViewportRepairAppState(excalidrawAPI.getAppState());

  if (Object.keys(files).length > 0) {
    excalidrawAPI.addFiles(Object.values(files) as AddFilesArgs);
  }

  if (positionedBundle) {
    const bundleToApply: DiagramBundle = {
      ...positionedBundle,
      previewElements: positionedElements,
    };
    yjsManager.applyDiagramBundle(bundleToApply);
    const visibleElements = positionedElements.filter((element) => !element.isDeleted);
    if (visibleElements.length > 0) {
      const stagedSelection = yjsManager.getManagedSelection(
        visibleElements.map((element) => element.id),
      );
      yjsManager.stageLocalSceneApply(
        visibleElements.map((element) => element.id),
        stagedSelection,
      );
    }
    const diagramId = positionedBundle.spec.diagramId;
    const preserved = existingElements.filter((item) => {
      const ref = yjsManager.getManagedElementRef(item.id, item);
      return ref?.diagramId !== diagramId;
    });
    const selectedElementIds = Object.fromEntries(
      visibleElements.map((element) => [element.id, true as const]),
    ) as Record<string, true>;
    excalidrawAPI.updateScene({
      elements: [...preserved, ...positionedElements] as unknown as UpdateSceneArgs['elements'],
      appState: (
        viewportRepair
          ? {
            ...viewportRepair,
            selectedElementIds,
          }
          : { selectedElementIds }
      ) as UpdateSceneArgs['appState'],
      captureUpdate: CaptureUpdateAction.NEVER,
    });
  } else {
    excalidrawAPI.updateScene({
      elements: [...existingElements, ...positionedElements] as unknown as UpdateSceneArgs['elements'],
      captureUpdate: CaptureUpdateAction.NEVER,
      ...(viewportRepair
        ? { appState: viewportRepair as UpdateSceneArgs['appState'] }
        : {}),
    });
  }

  if (positionedElements.length > 0) {
    excalidrawAPI.scrollToContent(positionedElements as unknown as ScrollToContentTarget, {
      fitToViewport: true,
      animate: true,
      duration: 300,
    });
  }
}
