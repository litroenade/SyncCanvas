/**
 * useVirtualCanvas Hook
 *
 * 管理虚拟画布状态，用于 Planning 和 Mermaid 模式的预览功能。
 * 支持元素的增删改查以及 Mermaid 代码转换。
 */
import { useState, useCallback } from 'react';
import type { ExcalidrawElement, BinaryFiles } from '../lib/yjs';

export interface UseVirtualCanvasReturn {
    /** 当前虚拟画布中的元素 */
    elements: ExcalidrawElement[];
    /** 关联的文件 (图片等) */
    files: BinaryFiles;
    /** 添加元素到虚拟画布 */
    addElements: (newElements: ExcalidrawElement[], newFiles?: BinaryFiles) => void;
    /** 更新元素 */
    updateElements: (updates: Partial<ExcalidrawElement>[]) => void;
    /** 删除元素 */
    removeElements: (ids: string[]) => void;
    /** 清空虚拟画布 */
    clearElements: () => void;
    /** 将 Mermaid 代码转换为 Excalidraw 元素 */
    convertMermaid: (code: string) => Promise<void>;
    /** 是否正在转换中 */
    isConverting: boolean;
    /** 转换错误信息 */
    conversionError: string | null;
}

/**
 * 虚拟画布状态管理 Hook
 *
 * 用于在侧边栏中预览 AI 生成的图表，支持增量添加和 Mermaid 转换
 */
export function useVirtualCanvas(): UseVirtualCanvasReturn {
    const [elements, setElements] = useState<ExcalidrawElement[]>([]);
    const [files, setFiles] = useState<BinaryFiles>({});
    const [isConverting, setIsConverting] = useState(false);
    const [conversionError, setConversionError] = useState<string | null>(null);

    /**
     * 添加元素到虚拟画布
     */
    const addElements = useCallback(
        (newElements: ExcalidrawElement[], newFiles?: BinaryFiles) => {
            setElements((prev) => [...prev, ...newElements]);
            if (newFiles) {
                setFiles((prev) => ({ ...prev, ...newFiles }));
            }
        },
        []
    );

    /**
     * 更新指定元素
     */
    const updateElements = useCallback((updates: Partial<ExcalidrawElement>[]) => {
        setElements((prev) =>
            prev.map((el) => {
                const update = updates.find((u) => u.id === el.id);
                return update ? { ...el, ...update } : el;
            })
        );
    }, []);

    /**
     * 删除指定元素
     */
    const removeElements = useCallback((ids: string[]) => {
        setElements((prev) => prev.filter((el) => !ids.includes(el.id)));
    }, []);

    /**
     * 清空虚拟画布
     */
    const clearElements = useCallback(() => {
        setElements([]);
        setFiles({});
        setConversionError(null);
    }, []);

    /**
     * 将 Mermaid 代码转换为 Excalidraw 元素
     */
    const convertMermaid = useCallback(async (code: string) => {
        if (!code.trim()) {
            setConversionError('请输入 Mermaid 代码');
            return;
        }

        setIsConverting(true);
        setConversionError(null);

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
                        fontSize: '20px',
                    },
                });

            // Step 2: 转换为完整的 Excalidraw 元素
            // 使用 as any 因为 parseMermaidToExcalidraw 返回的骨架格式与 convertToExcalidrawElements 期望的类型兼容
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const excalidrawElements = convertToExcalidrawElements(skeletonElements as any, {
                regenerateIds: true,
            });

            setElements(excalidrawElements as ExcalidrawElement[]);
            setFiles((newFiles as BinaryFiles) || {});
        } catch (err) {
            const message = (err as Error).message;
            console.error('[useVirtualCanvas] Mermaid 转换失败:', err);
            setConversionError(`Mermaid 解析失败: ${message}`);
        } finally {
            setIsConverting(false);
        }
    }, []);

    return {
        elements,
        files,
        addElements,
        updateElements,
        removeElements,
        clearElements,
        convertMermaid,
        isConverting,
        conversionError,
    };
}
