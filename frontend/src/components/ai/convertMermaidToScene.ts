import type { BinaryFiles, ExcalidrawElement } from '../../lib/yjs';
import { MERMAID_PREVIEW_CONFIG } from '../../lib/diagramRegistry';

type ExcalidrawSkeletons = Parameters<
  typeof import('@excalidraw/excalidraw')['convertToExcalidrawElements']
>[0];

export interface MermaidSceneData {
  elements: ExcalidrawElement[];
  files: BinaryFiles;
}

export async function convertMermaidToScene(code: string): Promise<MermaidSceneData> {
  const { parseMermaidToExcalidraw } = await import('@excalidraw/mermaid-to-excalidraw');
  const { convertToExcalidrawElements } = await import('@excalidraw/excalidraw');

  const { elements: skeletonElements, files } = await parseMermaidToExcalidraw(
    code,
    MERMAID_PREVIEW_CONFIG.parser,
  );

  const elements = convertToExcalidrawElements(
    skeletonElements as ExcalidrawSkeletons,
    MERMAID_PREVIEW_CONFIG.convert,
  );

  return {
    elements: elements as ExcalidrawElement[],
    files: (files as BinaryFiles) ?? {},
  };
}
