import React, { useRef, useEffect, useState } from 'react';
import { exportToCanvas } from '@excalidraw/excalidraw';
import type { ExcalidrawElement, BinaryFiles } from '../../lib/yjs';
import { cn } from '../../lib/utils';
import { PREVIEW_CANVAS_COPY } from '../../lib/diagramRegistry';
import { Check, Loader2, Plus, Trash2 } from 'lucide-react';

interface PreviewCanvasProps {
  elements: ExcalidrawElement[];
  files?: BinaryFiles;
  isDark: boolean;
  onAddToCanvas?: () => void;
  addedToCanvas?: boolean;
  onClear?: () => void;
  maxHeight?: number;
}

export const PreviewCanvas: React.FC<PreviewCanvasProps> = ({
  elements,
  files,
  isDark,
  onAddToCanvas,
  addedToCanvas = false,
  onClear,
  maxHeight = 300,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    if (elements.length === 0) {
      container.replaceChildren();
      setError(null);
      return;
    }

    const renderPreview = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const canvas = await exportToCanvas({
          elements,
          files: files || null,
          exportPadding: 20,
          maxWidthOrHeight:
            Math.max(container.offsetWidth, maxHeight) * window.devicePixelRatio,
          getDimensions: (width: number, height: number) => {
            const containerWidth = container.offsetWidth || 300;
            const scale = Math.min(containerWidth / width, maxHeight / height, 1);
            return {
              width: width * scale,
              height: height * scale,
              scale: 1,
            };
          },
        });

        canvas.style.width = '100%';
        canvas.style.height = 'auto';
        canvas.style.maxHeight = `${maxHeight}px`;
        canvas.style.objectFit = 'contain';

        container.replaceChildren(canvas);
      } catch (renderError) {
        const message = (renderError as Error).message;
        console.error('[PreviewCanvas] Failed to render preview:', renderError);
        setError(message);
      } finally {
        setIsLoading(false);
      }
    };

    renderPreview();
  }, [elements, files, maxHeight]);

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-xl border transition-colors duration-200',
        isDark ? 'border-zinc-700/50 bg-zinc-800/50' : 'border-zinc-200/50 bg-zinc-100/50',
      )}
    >
      <div
        ref={containerRef}
        className="preview-canvas flex min-h-[120px] items-center justify-center p-2"
        style={{ maxHeight: `${maxHeight}px` }}
      >
        {elements.length === 0 && !isLoading && (
          <div className={cn('text-sm', isDark ? 'text-zinc-500' : 'text-zinc-400')}>
            {PREVIEW_CANVAS_COPY.emptyState}
          </div>
        )}
      </div>

      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/20 backdrop-blur-sm">
          <Loader2 className="h-6 w-6 animate-spin text-violet-500" />
        </div>
      )}

      {error && (
        <div className="absolute right-0 bottom-0 left-0 bg-red-500/90 p-2 text-xs text-white">
          {error}
        </div>
      )}

      {elements.length > 0 && !isLoading && (
        <div className="absolute right-2 bottom-2 flex gap-2">
          {onClear && (
            <button
              onClick={onClear}
              className={cn(
                'flex items-center gap-1 rounded-lg p-2 text-xs transition-colors',
                isDark
                  ? 'bg-zinc-700 text-zinc-300 hover:bg-zinc-600'
                  : 'bg-zinc-200 text-zinc-600 hover:bg-zinc-300',
              )}
              title={PREVIEW_CANVAS_COPY.clearTitle}
            >
              <Trash2 size={14} />
            </button>
          )}
          {onAddToCanvas && !addedToCanvas && (
            <button
              onClick={onAddToCanvas}
              className="flex items-center gap-1 rounded-lg bg-gradient-to-r from-violet-500 to-purple-600 px-3 py-2 text-xs font-medium text-white shadow-lg shadow-violet-500/25 transition-colors hover:from-violet-600 hover:to-purple-700"
            >
              <Plus size={14} />
              {PREVIEW_CANVAS_COPY.addToCanvasLabel}
            </button>
          )}
          {onAddToCanvas && addedToCanvas && (
            <span className="flex items-center gap-1 rounded-lg bg-emerald-500/10 px-3 py-2 text-xs font-medium text-emerald-500">
              <Check size={14} />
              {PREVIEW_CANVAS_COPY.addedLabel}
            </span>
          )}
        </div>
      )}
    </div>
  );
};
