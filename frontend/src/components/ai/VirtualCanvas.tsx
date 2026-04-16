import React, { useState, useEffect, useCallback } from 'react';
import { exportToCanvas } from '@excalidraw/excalidraw';
import type { ExcalidrawElement, BinaryFiles } from '../../lib/yjs';
import { cn } from '../../lib/utils';
import { VIRTUAL_CANVAS_COPY } from '../../lib/diagramRegistry';
import { Plus, Maximize2, Minimize2 } from 'lucide-react';
import {
  primeManagedPreviewDrag,
  type ManagedPreviewDragPayload,
} from '../../lib/managedPreviewDrag';

interface VirtualCanvasProps {
  elements: ExcalidrawElement[];
  files?: BinaryFiles;
  isDark: boolean;
  onAddToCanvas?: (elements: ExcalidrawElement[]) => void;
  addedToCanvas?: boolean;
  minHeight?: number;
  maxHeight?: number;
  dragPayload?: ManagedPreviewDragPayload;
}

export const VirtualCanvas: React.FC<VirtualCanvasProps> = ({
  elements,
  files,
  isDark,
  onAddToCanvas,
  addedToCanvas = false,
  minHeight = 120,
  maxHeight = 300,
  dragPayload,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  type ExportToCanvasOptions = Parameters<typeof exportToCanvas>[0];

  useEffect(() => {
    if (!elements || elements.length === 0) {
      setPreviewUrl(null);
      setIsLoading(false);
      setHasError(false);
      return;
    }

    const generatePreview = async () => {
      setIsLoading(true);
      setHasError(false);
      try {
        const visibleElements = elements.filter(
          (element) => !element.isDeleted,
        ) as ExportToCanvasOptions['elements'];
        const previewFiles = (files ?? {}) as ExportToCanvasOptions['files'];
        const canvas = await exportToCanvas({
          elements: visibleElements,
          appState: {
            viewBackgroundColor: isDark ? '#18181b' : '#ffffff',
            exportWithDarkMode: isDark,
          },
          files: previewFiles,
          exportPadding: 20,
        });

        setPreviewUrl(canvas.toDataURL('image/png'));
      } catch (error) {
        console.error('Failed to generate virtual canvas preview:', error);
        setHasError(true);
        setPreviewUrl(null);
      } finally {
        setIsLoading(false);
      }
    };

    generatePreview();
  }, [elements, files, isDark]);

  const handleAddToCanvas = useCallback(() => {
    if (!onAddToCanvas || elements.length === 0) return;
    const elementsCopy = JSON.parse(JSON.stringify(elements));
    onAddToCanvas(elementsCopy);
  }, [elements, onAddToCanvas]);

  const handleDragStart = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    if (!dragPayload || addedToCanvas || elements.length === 0) {
      event.preventDefault();
      return;
    }
    primeManagedPreviewDrag(event.dataTransfer, dragPayload);
  }, [addedToCanvas, dragPayload, elements.length]);

  const currentHeight = isExpanded ? maxHeight : minHeight;
  const hasElements = elements.length > 0;
  const canDragToCanvas = Boolean(dragPayload) && hasElements && !addedToCanvas;

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-xl border transition-all duration-300',
        isDark ? 'border-zinc-700/50 bg-zinc-900' : 'border-zinc-200/50 bg-white',
      )}
      style={{ height: currentHeight }}
    >
      <div className="absolute top-2 right-2 z-10 flex items-center gap-1.5">
        {hasElements && (
          <span
            className={cn(
              'rounded px-2 py-0.5 text-xs',
              isDark ? 'bg-violet-500/20 text-violet-400' : 'bg-violet-100 text-violet-600',
            )}
          >
            {elements.length} elements
          </span>
        )}

        <button
          onClick={() => setIsExpanded((prev) => !prev)}
          className={cn(
            'rounded-lg p-1.5 transition-colors',
            isDark ? 'text-zinc-400 hover:bg-zinc-700' : 'text-zinc-500 hover:bg-zinc-100',
          )}
          title={isExpanded ? VIRTUAL_CANVAS_COPY.collapseTitle : VIRTUAL_CANVAS_COPY.expandTitle}
        >
          {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
        </button>

        {hasElements && onAddToCanvas && !addedToCanvas && (
          <button
            onClick={handleAddToCanvas}
            className={cn(
              'flex items-center gap-1 rounded-lg bg-gradient-to-r from-violet-500 to-purple-600 px-2.5 py-1.5 text-xs font-medium text-white shadow-md shadow-violet-500/20 transition-colors hover:from-violet-600 hover:to-purple-700',
            )}
          >
            <Plus size={12} />
            {VIRTUAL_CANVAS_COPY.addToCanvasLabel}
          </button>
        )}

        {hasElements && addedToCanvas && (
          <span className="px-2.5 py-1.5 text-xs font-medium text-green-500">
            {VIRTUAL_CANVAS_COPY.addedLabel}
          </span>
        )}
      </div>

      <div
        className={cn(
          'flex h-full w-full items-center justify-center p-2',
          canDragToCanvas && 'cursor-grab active:cursor-grabbing',
        )}
        draggable={canDragToCanvas}
        onDragStart={handleDragStart}
        title={canDragToCanvas ? VIRTUAL_CANVAS_COPY.dragPreviewTitle : undefined}
      >
        {previewUrl ? (
          <img
            src={previewUrl}
            alt={VIRTUAL_CANVAS_COPY.imageAlt}
            className="max-h-full max-w-full object-contain"
            draggable={false}
            style={{ imageRendering: 'auto' }}
          />
        ) : (
          <p className={cn('text-sm', isDark ? 'text-zinc-600' : 'text-zinc-400')}>
            {isLoading
              ? VIRTUAL_CANVAS_COPY.generatingLabel
              : hasError
                ? VIRTUAL_CANVAS_COPY.generationFailedLabel
                : hasElements
                  ? VIRTUAL_CANVAS_COPY.preparingLabel
                  : VIRTUAL_CANVAS_COPY.emptyState}
          </p>
        )}
      </div>
    </div>
  );
};
