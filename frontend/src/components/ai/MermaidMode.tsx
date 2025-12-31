/**
 * MermaidMode 组件
 *
 * Mermaid 模式：输入描述 -> AI 生成 Mermaid 代码 -> 预览 -> 添加到画布
 */
import React, { useState } from 'react';
import { cn } from '../../lib/utils';
import { Sparkles, Play, Loader2, FileCode2, AlertCircle, Zap, Brain } from 'lucide-react';
import { PreviewCanvas } from './PreviewCanvas';
import type { ExcalidrawElement, BinaryFiles } from '../../lib/yjs';

interface MermaidModeProps {
    roomId: string;
    isDark: boolean;
    elements: ExcalidrawElement[];
    files: BinaryFiles;
    onConvert: (code: string) => Promise<void>;
    onAddToCanvas: () => void;
    onClear: () => void;
    isConverting: boolean;
    error: string | null;
    /** 当前模式 */
    mode?: 'agent' | 'planning' | 'mermaid';
    /** 模式切换回调 */
    onModeChange?: (mode: 'agent' | 'planning' | 'mermaid') => void;
}

const EXAMPLE_MERMAID = `flowchart TD
    A[开始] --> B{判断条件}
    B -->|是| C[执行操作A]
    B -->|否| D[执行操作B]
    C --> E[结束]
    D --> E`;

const PRESET_PROMPTS = [
    { label: '登录流程', prompt: '用户登录流程，包括输入账号密码、验证、成功失败处理' },
    { label: '购物流程', prompt: '电商购物流程，从浏览商品到支付完成' },
    { label: '审批流程', prompt: '请假审批流程，包括申请、主管审批、HR审批' },
];

export const MermaidMode: React.FC<MermaidModeProps> = ({
    // roomId currently unused but reserved for future
    roomId: _roomId,
    isDark,
    elements,
    files,
    onConvert,
    onAddToCanvas,
    onClear,
    isConverting,
    error,
    mode = 'mermaid',
    onModeChange,
}) => {
    const [input, setInput] = useState('');
    const [mermaidCode, setMermaidCode] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);
    const [generateError, setGenerateError] = useState<string | null>(null);

    /**
     * 使用 AI 生成 Mermaid 代码
     */
    const handleGenerateMermaid = async (prompt?: string) => {
        const text = prompt || input;
        if (!text.trim()) return;

        setIsGenerating(true);
        setGenerateError(null);

        try {
            const token = localStorage.getItem('token');
            const response = await fetch('/api/ai/mermaid', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({ prompt: text }),
            });

            if (!response.ok) {
                throw new Error('生成失败，请重试');
            }

            const data = await response.json();
            setMermaidCode(data.code);

            // 自动转换预览
            await onConvert(data.code);
        } catch (err) {
            console.error('[MermaidMode] 生成失败:', err);
            setGenerateError((err as Error).message);
        } finally {
            setIsGenerating(false);
        }
    };

    /**
     * 手动转换当前代码
     */
    const handleConvert = () => {
        if (!mermaidCode.trim()) return;
        onConvert(mermaidCode);
    };

    /**
     * 加载示例代码
     */
    const handleLoadExample = () => {
        setMermaidCode(EXAMPLE_MERMAID);
        onConvert(EXAMPLE_MERMAID);
    };

    return (
        <div className="mermaid-mode h-full flex flex-col">
            {/* 预览区域 */}
            <div className="p-3 border-b border-zinc-700/30">
                <div className="flex items-center justify-between mb-2">
                    <span
                        className={cn(
                            'text-xs font-medium',
                            isDark ? 'text-zinc-400' : 'text-zinc-500'
                        )}
                    >
                        预览
                    </span>
                    {elements.length > 0 && (
                        <span className="text-xs text-violet-500">
                            {elements.length} 个元素
                        </span>
                    )}
                </div>
                <PreviewCanvas
                    elements={elements}
                    files={files}
                    isDark={isDark}
                    onAddToCanvas={onAddToCanvas}
                    onClear={elements.length > 0 ? onClear : undefined}
                    maxHeight={280}
                />
            </div>

            {/* Mermaid 代码编辑器 */}
            <div className="flex-1 flex flex-col p-3 gap-2 overflow-hidden">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <FileCode2
                            size={14}
                            className={isDark ? 'text-zinc-400' : 'text-zinc-500'}
                        />
                        <span
                            className={cn(
                                'text-xs font-medium',
                                isDark ? 'text-zinc-400' : 'text-zinc-500'
                            )}
                        >
                            Mermaid 代码
                        </span>
                    </div>
                    <button
                        onClick={handleLoadExample}
                        className={cn(
                            'text-xs px-2 py-1 rounded transition-colors',
                            isDark
                                ? 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
                                : 'text-zinc-500 hover:text-zinc-700 hover:bg-zinc-100'
                        )}
                    >
                        示例
                    </button>
                </div>

                <textarea
                    value={mermaidCode}
                    onChange={(e) => setMermaidCode(e.target.value)}
                    placeholder="在此输入 Mermaid 代码，或使用 AI 生成..."
                    className={cn(
                        'flex-1 min-h-[120px] resize-none',
                        'rounded-lg border p-3',
                        'text-xs font-mono',
                        'focus:outline-none focus:ring-2 focus:ring-violet-500/50',
                        'transition-colors',
                        isDark
                            ? 'bg-zinc-800/50 border-zinc-700 text-zinc-200 placeholder:text-zinc-600'
                            : 'bg-white border-zinc-200 text-zinc-800 placeholder:text-zinc-400'
                    )}
                />

                <button
                    onClick={handleConvert}
                    disabled={isConverting || !mermaidCode.trim()}
                    className={cn(
                        'w-full py-2 rounded-lg text-sm font-medium',
                        'flex items-center justify-center gap-2',
                        'transition-all duration-200',
                        isConverting || !mermaidCode.trim()
                            ? 'bg-zinc-700 text-zinc-400 cursor-not-allowed'
                            : isDark
                                ? 'bg-zinc-700 hover:bg-zinc-600 text-zinc-200'
                                : 'bg-zinc-200 hover:bg-zinc-300 text-zinc-700'
                    )}
                >
                    {isConverting ? (
                        <>
                            <Loader2 size={14} className="animate-spin" />
                            转换中...
                        </>
                    ) : (
                        <>
                            <Play size={14} />
                            转换预览
                        </>
                    )}
                </button>

                {/* 错误显示 */}
                {(error || generateError) && (
                    <div
                        className={cn(
                            'flex items-start gap-2 p-2 rounded-lg text-xs',
                            'bg-red-500/10 text-red-400 border border-red-500/20'
                        )}
                    >
                        <AlertCircle size={14} className="flex-shrink-0 mt-0.5" />
                        <span>{error || generateError}</span>
                    </div>
                )}
            </div>

            {/* AI 生成区域 */}
            <div
                className={cn(
                    'p-3 border-t',
                    isDark ? 'border-zinc-700/50' : 'border-zinc-200/50'
                )}
            >
                {/* 预设提示 */}
                <div className="flex gap-1 mb-2 flex-wrap">
                    {PRESET_PROMPTS.map((preset) => (
                        <button
                            key={preset.label}
                            onClick={() => {
                                setInput(preset.prompt);
                                handleGenerateMermaid(preset.prompt);
                            }}
                            disabled={isGenerating}
                            className={cn(
                                'px-2 py-1 rounded-full text-xs',
                                'transition-colors',
                                isDark
                                    ? 'bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200'
                                    : 'bg-zinc-100 hover:bg-zinc-200 text-zinc-500 hover:text-zinc-700'
                            )}
                        >
                            {preset.label}
                        </button>
                    ))}
                </div>

                {/* 输入框 */}
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="描述你想要的流程图..."
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey && !isGenerating) {
                                e.preventDefault();
                                handleGenerateMermaid();
                            }
                        }}
                        className={cn(
                            'flex-1 px-3 py-2 rounded-lg border',
                            'text-sm',
                            'focus:outline-none focus:ring-2 focus:ring-violet-500/50',
                            'transition-colors',
                            isDark
                                ? 'bg-zinc-800 border-zinc-700 text-zinc-200 placeholder:text-zinc-500'
                                : 'bg-white border-zinc-200 text-zinc-800 placeholder:text-zinc-400'
                        )}
                    />
                    <button
                        onClick={() => handleGenerateMermaid()}
                        disabled={isGenerating || !input.trim()}
                        className={cn(
                            'px-4 py-2 rounded-lg',
                            'flex items-center gap-2',
                            'text-sm font-medium',
                            'transition-all duration-200',
                            isGenerating || !input.trim()
                                ? 'bg-zinc-700 text-zinc-400 cursor-not-allowed'
                                : 'bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 text-white shadow-lg shadow-violet-500/25'
                        )}
                    >
                        {isGenerating ? (
                            <Loader2 size={16} className="animate-spin" />
                        ) : (
                            <Sparkles size={16} />
                        )}
                    </button>
                </div>

                {/* 模式切换按钮 */}
                {onModeChange && (
                    <div className="flex items-center gap-2 mt-2">
                        <button
                            onClick={() => onModeChange('agent')}
                            className={cn(
                                'flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs',
                                'transition-colors',
                                mode === 'agent'
                                    ? 'bg-violet-500/20 text-violet-400'
                                    : isDark
                                        ? 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'
                                        : 'text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100'
                            )}
                        >
                            <Zap size={12} />
                            Agent
                        </button>
                        <button
                            onClick={() => onModeChange('planning')}
                            className={cn(
                                'flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs',
                                'transition-colors',
                                mode === 'planning'
                                    ? 'bg-violet-500/20 text-violet-400'
                                    : isDark
                                        ? 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'
                                        : 'text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100'
                            )}
                        >
                            <Brain size={12} />
                            Planning
                        </button>
                        <button
                            className={cn(
                                'flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs',
                                'bg-violet-500/20 text-violet-400'
                            )}
                            disabled
                        >
                            <FileCode2 size={12} />
                            Mermaid
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};
