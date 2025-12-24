/**
 * MermaidCodePreview 组件
 *
 * 在聊天消息中显示 Mermaid 代码块和自动转换的预览图
 */
import React, { useState, useEffect } from 'react';
import { cn } from '../../lib/utils';
import { FileCode2, Loader2, AlertCircle, Copy, Check } from 'lucide-react';
import { PreviewCanvas } from './PreviewCanvas';
import type { ExcalidrawElement, BinaryFiles } from '../../lib/yjs';

interface MermaidCodePreviewProps {
    /** Mermaid 代码 */
    code: string;
    /** 是否深色模式 */
    isDark: boolean;
    /** 添加到画布回调 */
    onAddToCanvas?: (elements: ExcalidrawElement[]) => void;
}

export const MermaidCodePreview: React.FC<MermaidCodePreviewProps> = ({
    code,
    isDark,
    onAddToCanvas,
}) => {
    const [isConverting, setIsConverting] = useState(false);
    const [convertedElements, setConvertedElements] = useState<ExcalidrawElement[]>([]);
    const [files, setFiles] = useState<BinaryFiles>({});
    const [error, setError] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);

    // 自动转换 Mermaid 代码
    useEffect(() => {
        const convertCode = async () => {
            if (!code.trim()) return;

            setIsConverting(true);
            setError(null);

            try {
                // 动态导入以减少初始加载体积
                const { parseMermaidToExcalidraw } = await import(
                    '@excalidraw/mermaid-to-excalidraw'
                );
                const { convertToExcalidrawElements } = await import('@excalidraw/excalidraw');

                // Step 1: 解析 Mermaid 代码为骨架格式
                const { elements: skeletonElements, files: newFiles } =
                    await parseMermaidToExcalidraw(code, {
                        themeVariables: {
                            fontSize: '16px',
                        },
                    });

                // Step 2: 转换为完整的 Excalidraw 元素
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                const excalidrawElements = convertToExcalidrawElements(skeletonElements as any, {
                    regenerateIds: true,
                });

                setConvertedElements(excalidrawElements as ExcalidrawElement[]);
                setFiles((newFiles as BinaryFiles) || {});
            } catch (err) {
                const message = (err as Error).message;
                console.error('[MermaidCodePreview] 转换失败:', err);
                setError(`Mermaid 解析失败: ${message}`);
            } finally {
                setIsConverting(false);
            }
        };

        convertCode();
    }, [code]);

    // 复制代码
    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(code);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('复制失败:', err);
        }
    };

    return (
        <div className="mermaid-code-preview mt-3 space-y-2">
            {/* 代码块标题 */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                    <FileCode2 size={14} className="text-violet-400" />
                    <span className={cn(
                        'text-xs font-medium',
                        isDark ? 'text-zinc-400' : 'text-zinc-500'
                    )}>
                        Mermaid 代码
                    </span>
                </div>
                <button
                    onClick={handleCopy}
                    className={cn(
                        'flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors',
                        isDark
                            ? 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700'
                            : 'text-zinc-400 hover:text-zinc-600 hover:bg-zinc-200'
                    )}
                >
                    {copied ? (
                        <>
                            <Check size={12} className="text-green-500" />
                            已复制
                        </>
                    ) : (
                        <>
                            <Copy size={12} />
                            复制
                        </>
                    )}
                </button>
            </div>

            {/* 代码块 */}
            <div className={cn(
                'rounded-lg border overflow-hidden',
                isDark ? 'bg-zinc-900 border-zinc-700' : 'bg-zinc-50 border-zinc-200'
            )}>
                <pre className={cn(
                    'p-3 text-xs font-mono overflow-x-auto max-h-[200px]',
                    isDark ? 'text-zinc-300' : 'text-zinc-700'
                )}>
                    <code>{code}</code>
                </pre>
            </div>

            {/* 转换状态和预览 */}
            {isConverting && (
                <div className={cn(
                    'flex items-center gap-2 p-3 rounded-lg',
                    isDark ? 'bg-zinc-800/50' : 'bg-zinc-100'
                )}>
                    <Loader2 size={14} className="animate-spin text-violet-500" />
                    <span className={cn(
                        'text-xs',
                        isDark ? 'text-zinc-400' : 'text-zinc-500'
                    )}>
                        正在转换为图形...
                    </span>
                </div>
            )}

            {error && (
                <div className={cn(
                    'flex items-start gap-2 p-3 rounded-lg text-xs',
                    'bg-red-500/10 text-red-400 border border-red-500/20'
                )}>
                    <AlertCircle size={14} className="flex-shrink-0 mt-0.5" />
                    <span>{error}</span>
                </div>
            )}

            {!isConverting && !error && convertedElements.length > 0 && (
                <div>
                    <div className={cn(
                        'text-xs font-medium mb-1.5',
                        isDark ? 'text-zinc-400' : 'text-zinc-500'
                    )}>
                        预览
                    </div>
                    <PreviewCanvas
                        elements={convertedElements}
                        files={files}
                        isDark={isDark}
                        maxHeight={200}
                        onAddToCanvas={onAddToCanvas ? () => onAddToCanvas(convertedElements) : undefined}
                        onClear={undefined}
                    />
                </div>
            )}
        </div>
    );
};

/**
 * 从消息内容中提取 Mermaid 代码块
 */
export function extractMermaidCode(content: string): string | null {
    // 匹配 ```mermaid ... ``` 代码块
    const mermaidBlockRegex = /```mermaid\s*([\s\S]*?)```/i;
    const match = content.match(mermaidBlockRegex);

    if (match && match[1]) {
        return match[1].trim();
    }

    return null;
}
