/**
 * VirtualCanvas 组件
 *
 * 使用静态图片预览虚拟画布内容
 * 与主画布完全隔离
 */
import React, { useState, useEffect, useCallback } from 'react';
import { exportToCanvas } from '@excalidraw/excalidraw';
import type { ExcalidrawElement, BinaryFiles } from '../../lib/yjs';
import { cn } from '../../lib/utils';
import { Plus, Maximize2, Minimize2 } from 'lucide-react';

interface VirtualCanvasProps {
    /** 虚拟画布中的元素 */
    elements: ExcalidrawElement[];
    /** 关联的文件 */
    files?: BinaryFiles;
    /** 是否深色模式 */
    isDark: boolean;
    /** 添加到主画布回调 */
    onAddToCanvas?: (elements: ExcalidrawElement[]) => void;
    /** 是否已添加到画布 */
    addedToCanvas?: boolean;
    /** 最小高度 */
    minHeight?: number;
    /** 最大高度 */
    maxHeight?: number;
}

export const VirtualCanvas: React.FC<VirtualCanvasProps> = ({
    elements,
    files,
    isDark,
    onAddToCanvas,
    addedToCanvas = false,
    minHeight = 120,
    maxHeight = 300,
}) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [hasError, setHasError] = useState(false);

    // 生成预览图
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
                const canvas = await exportToCanvas({
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    elements: elements as any,
                    appState: {
                        viewBackgroundColor: isDark ? '#18181b' : '#ffffff',
                        exportWithDarkMode: isDark,
                    },
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    files: (files || {}) as any,
                    exportPadding: 20,
                });

                setPreviewUrl(canvas.toDataURL('image/png'));
            } catch (error) {
                console.error('生成预览失败:', error);
                setHasError(true);
                setPreviewUrl(null);
            } finally {
                setIsLoading(false);
            }
        };

        generatePreview();
    }, [elements, files, isDark]);

    // 添加到主画布
    const handleAddToCanvas = useCallback(() => {
        if (onAddToCanvas && elements.length > 0) {
            // 深拷贝元素
            const elementsCopy = JSON.parse(JSON.stringify(elements));
            onAddToCanvas(elementsCopy);
        }
    }, [onAddToCanvas, elements]);

    // 切换展开状态
    const toggleExpand = useCallback(() => {
        setIsExpanded(prev => !prev);
    }, []);

    const currentHeight = isExpanded ? maxHeight : minHeight;
    const hasElements = elements.length > 0;

    return (
        <div
            className={cn(
                'virtual-canvas-wrapper',
                'relative rounded-xl overflow-hidden',
                'border transition-all duration-300',
                isDark
                    ? 'bg-zinc-900 border-zinc-700/50'
                    : 'bg-white border-zinc-200/50'
            )}
            style={{ height: currentHeight }}
        >
            {/* 工具栏 */}
            <div
                className={cn(
                    'absolute top-2 right-2 z-10',
                    'flex items-center gap-1.5'
                )}
            >
                {/* 元素计数 */}
                {hasElements && (
                    <span className={cn(
                        'px-2 py-0.5 rounded text-xs',
                        isDark
                            ? 'bg-violet-500/20 text-violet-400'
                            : 'bg-violet-100 text-violet-600'
                    )}>
                        {elements.length} 个元素
                    </span>
                )}

                {/* 展开/收起 */}
                <button
                    onClick={toggleExpand}
                    className={cn(
                        'p-1.5 rounded-lg transition-colors',
                        isDark
                            ? 'hover:bg-zinc-700 text-zinc-400'
                            : 'hover:bg-zinc-100 text-zinc-500'
                    )}
                    title={isExpanded ? '收起' : '展开'}
                >
                    {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                </button>

                {/* 添加到主画布 */}
                {hasElements && onAddToCanvas && !addedToCanvas && (
                    <button
                        onClick={handleAddToCanvas}
                        className={cn(
                            'px-2.5 py-1.5 rounded-lg transition-colors',
                            'text-xs font-medium flex items-center gap-1',
                            'bg-gradient-to-r from-violet-500 to-purple-600',
                            'hover:from-violet-600 hover:to-purple-700',
                            'text-white shadow-md shadow-violet-500/20'
                        )}
                    >
                        <Plus size={12} />
                        添加到画布
                    </button>
                )}
                {/* 已添加标记 */}
                {hasElements && addedToCanvas && (
                    <span className="px-2.5 py-1.5 text-xs font-medium text-green-500">
                        ✓ 已添加
                    </span>
                )}
            </div>

            {/* 预览区域 */}
            <div className="w-full h-full flex items-center justify-center p-2">
                {previewUrl ? (
                    <img
                        src={previewUrl}
                        alt="虚拟画布预览"
                        className="max-w-full max-h-full object-contain"
                        style={{
                            imageRendering: 'auto',
                        }}
                    />
                ) : (
                    <p className={cn(
                        'text-sm',
                        isDark ? 'text-zinc-600' : 'text-zinc-400'
                    )}>
                        {isLoading ? '生成预览中...' :
                            hasError ? '预览生成失败' :
                                hasElements ? '准备预览...' :
                                    '虚拟画布 - AI 生成后在此预览'}
                    </p>
                )}
            </div>
        </div>
    );
};
