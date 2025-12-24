/**
 * PreviewCanvas 组件
 *
 * 虚拟白板预览组件，使用 Excalidraw 的 exportToCanvas API
 * 渲染元素的静态预览。用于 Planning 和 Mermaid 模式。
 */
import React, { useRef, useEffect, useState } from 'react';
import { exportToCanvas } from '@excalidraw/excalidraw';
import type { ExcalidrawElement, BinaryFiles } from '../../lib/yjs';
import { cn } from '../../lib/utils';
import { Loader2, Plus, Trash2 } from 'lucide-react';

interface PreviewCanvasProps {
    /** 要预览的元素 */
    elements: ExcalidrawElement[];
    /** 关联的文件 */
    files?: BinaryFiles;
    /** 是否深色模式 */
    isDark: boolean;
    /** 添加到主画布回调 */
    onAddToCanvas?: () => void;
    /** 清空预览回调 */
    onClear?: () => void;
    /** 最大高度 */
    maxHeight?: number;
}

export const PreviewCanvas: React.FC<PreviewCanvasProps> = ({
    elements,
    files,
    isDark,
    onAddToCanvas,
    onClear,
    maxHeight = 300,
}) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // 当元素变化时重新渲染预览
    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;

        // 如果没有元素，清空预览
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
                        // 保持宽高比，限制最大高度
                        const containerWidth = container.offsetWidth || 300;
                        const scale = Math.min(containerWidth / width, maxHeight / height, 1);
                        return {
                            width: width * scale,
                            height: height * scale,
                            scale: 1,
                        };
                    },
                });

                // 设置 canvas 样式
                canvas.style.width = '100%';
                canvas.style.height = 'auto';
                canvas.style.maxHeight = `${maxHeight}px`;
                canvas.style.objectFit = 'contain';

                container.replaceChildren(canvas);
            } catch (err) {
                const message = (err as Error).message;
                console.error('[PreviewCanvas] 渲染失败:', err);
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
                'preview-canvas-wrapper',
                'relative rounded-xl overflow-hidden',
                'border transition-colors duration-200',
                isDark
                    ? 'bg-zinc-800/50 border-zinc-700/50'
                    : 'bg-zinc-100/50 border-zinc-200/50'
            )}
        >
            {/* 预览区域 */}
            <div
                ref={containerRef}
                className={cn(
                    'preview-canvas',
                    'min-h-[120px] flex items-center justify-center',
                    'p-2'
                )}
                style={{ maxHeight: `${maxHeight}px` }}
            >
                {elements.length === 0 && !isLoading && (
                    <div
                        className={cn(
                            'text-sm',
                            isDark ? 'text-zinc-500' : 'text-zinc-400'
                        )}
                    >
                        预览区域 - 生成后显示
                    </div>
                )}
            </div>

            {/* 加载状态 */}
            {isLoading && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/20 backdrop-blur-sm">
                    <Loader2 className="w-6 h-6 animate-spin text-violet-500" />
                </div>
            )}

            {/* 错误显示 */}
            {error && (
                <div className="absolute bottom-0 left-0 right-0 p-2 bg-red-500/90 text-white text-xs">
                    {error}
                </div>
            )}

            {/* 操作按钮 */}
            {elements.length > 0 && !isLoading && (
                <div
                    className={cn(
                        'absolute bottom-2 right-2 flex gap-2',
                        'opacity-0 group-hover:opacity-100 transition-opacity'
                    )}
                    style={{ opacity: 1 }} // 暂时保持可见
                >
                    {onClear && (
                        <button
                            onClick={onClear}
                            className={cn(
                                'p-2 rounded-lg transition-colors',
                                'text-xs flex items-center gap-1',
                                isDark
                                    ? 'bg-zinc-700 hover:bg-zinc-600 text-zinc-300'
                                    : 'bg-zinc-200 hover:bg-zinc-300 text-zinc-600'
                            )}
                            title="清空预览"
                        >
                            <Trash2 size={14} />
                        </button>
                    )}
                    {onAddToCanvas && (
                        <button
                            onClick={onAddToCanvas}
                            className={cn(
                                'px-3 py-2 rounded-lg transition-colors',
                                'text-xs font-medium flex items-center gap-1',
                                'bg-gradient-to-r from-violet-500 to-purple-600',
                                'hover:from-violet-600 hover:to-purple-700',
                                'text-white shadow-lg shadow-violet-500/25'
                            )}
                        >
                            <Plus size={14} />
                            添加到画布
                        </button>
                    )}
                </div>
            )}
        </div>
    );
};
