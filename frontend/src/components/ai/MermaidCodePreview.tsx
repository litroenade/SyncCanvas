import React, { useState, useEffect } from 'react';
import { cn } from '../../lib/utils';
import { MERMAID_PREVIEW_COPY } from '../../lib/diagramRegistry';
import { FileCode2, Loader2, AlertCircle, Copy, Check } from 'lucide-react';
import { PreviewCanvas } from './PreviewCanvas';
import type { ExcalidrawElement, BinaryFiles } from '../../lib/yjs';
import { convertMermaidToScene } from './convertMermaidToScene';

interface MermaidCodePreviewProps {
  code: string;
  isDark: boolean;
  onAddToCanvas?: (elements: ExcalidrawElement[], files: BinaryFiles) => void;
  addedToCanvas?: boolean;
}

export const MermaidCodePreview: React.FC<MermaidCodePreviewProps> = ({
  code,
  isDark,
  onAddToCanvas,
  addedToCanvas = false,
}) => {
  const [isConverting, setIsConverting] = useState(false);
  const [convertedElements, setConvertedElements] = useState<ExcalidrawElement[]>([]);
  const [files, setFiles] = useState<BinaryFiles>({});
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const convertCode = async () => {
      if (!code.trim()) return;

      setIsConverting(true);
      setError(null);

      try {
        const scene = await convertMermaidToScene(code);
        setConvertedElements(scene.elements);
        setFiles(scene.files);
      } catch (conversionError) {
        const message = (conversionError as Error).message;
        console.error('[MermaidCodePreview] Failed to convert Mermaid:', conversionError);
        setError(`${MERMAID_PREVIEW_COPY.errorPrefix}${message}`);
      } finally {
        setIsConverting(false);
      }
    };

    convertCode();
  }, [code]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (copyError) {
      console.error('Failed to copy Mermaid code:', copyError);
    }
  };

  return (
    <div className="mt-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <FileCode2 size={14} className="text-violet-400" />
          <span className={cn('text-xs font-medium', isDark ? 'text-zinc-400' : 'text-zinc-500')}>
            {MERMAID_PREVIEW_COPY.title}
          </span>
        </div>
        <button
          onClick={handleCopy}
          className={cn(
            'flex items-center gap-1 rounded px-2 py-1 text-xs transition-colors',
            isDark
              ? 'text-zinc-500 hover:bg-zinc-700 hover:text-zinc-300'
              : 'text-zinc-400 hover:bg-zinc-200 hover:text-zinc-600',
          )}
        >
          {copied ? (
            <>
              <Check size={12} className="text-green-500" />
              {MERMAID_PREVIEW_COPY.copiedLabel}
            </>
          ) : (
            <>
              <Copy size={12} />
              {MERMAID_PREVIEW_COPY.copyLabel}
            </>
          )}
        </button>
      </div>

      <div
        className={cn(
          'overflow-hidden rounded-lg border',
          isDark ? 'border-zinc-700 bg-zinc-900' : 'border-zinc-200 bg-zinc-50',
        )}
      >
        <pre
          className={cn(
            'max-h-[200px] overflow-x-auto p-3 text-xs font-mono',
            isDark ? 'text-zinc-300' : 'text-zinc-700',
          )}
        >
          <code>{code}</code>
        </pre>
      </div>

      {isConverting && (
        <div
          className={cn(
            'flex items-center gap-2 rounded-lg p-3',
            isDark ? 'bg-zinc-800/50' : 'bg-zinc-100',
          )}
        >
          <Loader2 size={14} className="animate-spin text-violet-500" />
          <span className={cn('text-xs', isDark ? 'text-zinc-400' : 'text-zinc-500')}>
            {MERMAID_PREVIEW_COPY.convertingLabel}
          </span>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-400">
          <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {!isConverting && !error && convertedElements.length > 0 && (
        <div>
          <div className={cn('mb-1.5 text-xs font-medium', isDark ? 'text-zinc-400' : 'text-zinc-500')}>
            {MERMAID_PREVIEW_COPY.previewLabel}
          </div>
          <PreviewCanvas
            elements={convertedElements}
            files={files}
            isDark={isDark}
            maxHeight={200}
            addedToCanvas={addedToCanvas}
            onAddToCanvas={onAddToCanvas ? () => onAddToCanvas(convertedElements, files) : undefined}
            onClear={undefined}
          />
        </div>
      )}
    </div>
  );
};
