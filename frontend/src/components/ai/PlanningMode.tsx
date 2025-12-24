/**
 * PlanningMode 组件
 *
 * Planning 模式：先在虚拟画布预览，确认后再添加到主画布
 * 复用 Agent 对话逻辑，但工具调用结果显示在预览区
 */
import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { cn } from '../../lib/utils';
import {
    Send,
    Loader2,
    Wand2,
    AlertCircle,
    CheckCircle,
    Trash2,
    Plus,
    Zap,
    FileCode2,
} from 'lucide-react';
import { useAIStream } from '../../hooks/useAIStream';
import { ToolProgress, ToolStep } from './ToolProgress';
import { useTypingEffect } from '../../hooks/useTypingEffect';
import { PreviewCanvas } from './PreviewCanvas';
import type { ExcalidrawElement, BinaryFiles } from '../../lib/yjs';

interface PlanningModeProps {
    roomId: string;
    isDark: boolean;
    /** 预览元素 */
    elements: ExcalidrawElement[];
    /** 预览文件 */
    files: BinaryFiles;
    /** 添加元素到虚拟画布 */
    onAddElements: (elements: ExcalidrawElement[], files?: BinaryFiles) => void;
    /** 添加到主画布 */
    onAddToCanvas: () => void;
    /** 清除预览 */
    onClear: () => void;
    /** 当前模式 */
    mode?: 'agent' | 'planning' | 'mermaid';
    /** 模式切换回调 */
    onModeChange?: (mode: 'agent' | 'planning' | 'mermaid') => void;
}

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: number;
    status?: 'pending' | 'success' | 'error';
}

export const PlanningMode: React.FC<PlanningModeProps> = ({
    roomId,
    isDark,
    elements,
    files,
    onAddElements,
    onAddToCanvas,
    onClear,
    mode = 'planning',
    onModeChange,
}) => {
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState<Message[]>([]);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // 使用 WebSocket 流式 AI - Planning 模式同样使用 Agent，但我们只关注创建的元素
    const {
        isLoading,
        steps,
        response,
        error,
        sendRequest,
        reset,
        virtualElements,
    } = useAIStream({ roomId, autoConnect: true });

    // 将 AI 步骤转换为 ToolProgress 格式
    const toolSteps: ToolStep[] = useMemo(() => {
        return steps.map((step, index) => ({
            stepNumber: index + 1,
            thought: step.thought,
            action: step.action || undefined,
            actionInput: step.action_input ?? undefined,
            observation: step.observation ?? undefined,
            success: step.success,
            latencyMs: step.latency_ms,
            status: step.success === false ? 'error' as const :
                step.observation ? 'done' as const :
                    step.action ? 'running' as const : 'pending' as const,
        }));
    }, [steps]);

    // 打字机效果
    const { displayText: typedResponse, isTyping, skip: skipTyping } = useTypingEffect(
        response || '',
        { speed: 20 }
    );

    // 滚动到底部
    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages, steps, typedResponse, scrollToBottom]);

    // 监听步骤更新
    useEffect(() => {
        if (steps.length > 0) {
            const latestStep = steps[steps.length - 1];
            setMessages(prev => {
                let lastAssistantIndex = -1;
                for (let i = prev.length - 1; i >= 0; i--) {
                    if (prev[i].role === 'assistant' && prev[i].status === 'pending') {
                        lastAssistantIndex = i;
                        break;
                    }
                }
                if (lastAssistantIndex === -1) return prev;

                return prev.map((msg, i) =>
                    i === lastAssistantIndex
                        ? {
                            ...msg,
                            content: latestStep.action
                                ? `正在执行: ${latestStep.action}...`
                                : latestStep.thought || '思考中...',
                        }
                        : msg
                );
            });
        }
    }, [steps]);

    // 监听完成响应
    useEffect(() => {
        if (response) {
            setMessages(prev => prev.map(msg =>
                msg.role === 'assistant' && msg.status === 'pending'
                    ? { ...msg, content: response, status: 'success' as const }
                    : msg
            ));
        }
    }, [response]);

    // 监听错误
    useEffect(() => {
        if (error) {
            setMessages(prev => prev.map(msg =>
                msg.role === 'assistant' && msg.status === 'pending'
                    ? { ...msg, content: error, status: 'error' as const }
                    : msg
            ));
        }
    }, [error]);

    // 监听虚拟模式返回的元素 - Planning 模式使用 virtual_mode
    // 当 AI 返回完成时，将 virtualElements 添加到预览画布
    useEffect(() => {
        if (virtualElements && virtualElements.length > 0) {
            console.log('[PlanningMode] 收到虚拟元素:', virtualElements.length);
            // 转换为 ExcalidrawElement 格式并添加到预览
            const newElements = virtualElements.map(el => ({
                ...el,
                id: el.id || `virtual-${Date.now()}-${Math.random().toString(36).slice(2)}`,
            })) as ExcalidrawElement[];
            onAddElements(newElements);
        }
    }, [virtualElements, onAddElements]);

    // 发送消息
    const handleSend = useCallback(async (prompt?: string) => {
        const text = prompt || input.trim();
        if (!text || isLoading) return;

        const userMessage: Message = {
            id: `user-${Date.now()}`,
            role: 'user',
            content: text,
            timestamp: Date.now(),
        };

        const assistantMessage: Message = {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: '正在连接...',
            timestamp: Date.now(),
            status: 'pending',
        };

        setMessages(prev => [...prev, userMessage, assistantMessage]);
        setInput('');
        reset();

        await sendRequest(text, { theme: isDark ? 'dark' : 'light', virtual_mode: true });
    }, [input, isLoading, sendRequest, reset, isDark]);

    // 处理按键
    const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    }, [handleSend]);

    return (
        <div className="planning-mode h-full flex flex-col">
            {/* 预览区域 */}
            <div className="p-3 border-b border-zinc-700/30">
                <div className="flex items-center justify-between mb-2">
                    <span className={cn(
                        'text-xs font-medium',
                        isDark ? 'text-zinc-400' : 'text-zinc-500'
                    )}>
                        预览画布
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
                    maxHeight={250}
                />
            </div>

            {/* 消息列表 */}
            <div className={cn(
                'flex-1 overflow-y-auto p-3 space-y-3',
                messages.length === 0 && 'min-h-[100px]'
            )}>
                {messages.length === 0 ? (
                    <div className="text-center py-6">
                        <Wand2 size={32} className={cn(
                            'mx-auto mb-3 opacity-30',
                            isDark ? 'text-zinc-500' : 'text-zinc-400'
                        )} />
                        <p className={cn(
                            'text-sm',
                            isDark ? 'text-zinc-500' : 'text-zinc-400'
                        )}>
                            描述图形，AI 将在预览区生成
                        </p>
                        <p className={cn(
                            'text-xs mt-1',
                            isDark ? 'text-zinc-600' : 'text-zinc-400'
                        )}>
                            确认后再添加到主画布
                        </p>
                    </div>
                ) : (
                    messages.map((msg) => (
                        <div
                            key={msg.id}
                            className={cn(
                                'flex',
                                msg.role === 'user' ? 'justify-end' : 'justify-start'
                            )}
                        >
                            <div className={cn(
                                'max-w-[90%] px-3 py-2 rounded-2xl text-sm',
                                msg.role === 'user'
                                    ? 'bg-gradient-to-r from-violet-500 to-purple-500 text-white'
                                    : isDark
                                        ? 'bg-zinc-800 text-zinc-200'
                                        : 'bg-zinc-100 text-zinc-700'
                            )}>
                                <div className="flex items-start gap-2">
                                    {msg.role === 'assistant' && msg.status === 'pending' && (
                                        <Loader2 size={14} className="animate-spin mt-0.5 text-violet-500" />
                                    )}
                                    {msg.role === 'assistant' && msg.status === 'success' && (
                                        <CheckCircle size={14} className="mt-0.5 text-emerald-500" />
                                    )}
                                    {msg.role === 'assistant' && msg.status === 'error' && (
                                        <AlertCircle size={14} className="mt-0.5 text-red-500" />
                                    )}
                                    <span>
                                        {msg.role === 'assistant' && msg.status === 'success' && isTyping
                                            ? typedResponse
                                            : msg.content}
                                        {msg.role === 'assistant' && msg.status === 'success' && isTyping && (
                                            <span
                                                className="inline-block w-1 h-4 ml-0.5 bg-current animate-pulse cursor-pointer"
                                                onClick={skipTyping}
                                                title="点击跳过"
                                            />
                                        )}
                                    </span>
                                </div>
                            </div>
                        </div>
                    ))
                )}

                {/* 工具执行进度 */}
                {toolSteps.length > 0 && (
                    <ToolProgress
                        steps={toolSteps}
                        isRunning={isLoading}
                        className="mt-2"
                    />
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* 输入区域 */}
            <div className={cn(
                'p-3 border-t',
                isDark ? 'border-zinc-700/50' : 'border-zinc-200/50'
            )}>
                {/* 操作按钮 */}
                {messages.length > 0 && (
                    <div className="flex items-center gap-2 mb-2">
                        <button
                            onClick={() => setMessages([])}
                            className={cn(
                                'flex items-center gap-1 px-2 py-1 rounded-lg text-xs',
                                'transition-colors',
                                isDark
                                    ? 'text-zinc-500 hover:text-red-400 hover:bg-zinc-800'
                                    : 'text-zinc-400 hover:text-red-500 hover:bg-zinc-100'
                            )}
                        >
                            <Trash2 size={12} />
                            清除对话
                        </button>
                        {elements.length > 0 && (
                            <button
                                onClick={onAddToCanvas}
                                className={cn(
                                    'flex items-center gap-1 px-2 py-1 rounded-lg text-xs',
                                    'bg-violet-500/20 text-violet-400 hover:bg-violet-500/30',
                                    'transition-colors'
                                )}
                            >
                                <Plus size={12} />
                                添加到画布
                            </button>
                        )}
                    </div>
                )}

                {/* 输入框 */}
                <div className={cn(
                    'flex items-end gap-2 p-2 rounded-xl border',
                    isDark
                        ? 'bg-zinc-800/50 border-zinc-700/50'
                        : 'bg-zinc-50 border-zinc-200/50'
                )}>
                    <textarea
                        ref={inputRef}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="描述你想要的图形..."
                        disabled={isLoading}
                        rows={1}
                        className={cn(
                            'flex-1 resize-none bg-transparent outline-none',
                            'text-sm placeholder:text-zinc-400',
                            'max-h-[80px] min-h-[24px]',
                            isDark ? 'text-white' : 'text-zinc-900',
                            isLoading && 'opacity-50'
                        )}
                    />
                    <button
                        onClick={() => handleSend()}
                        disabled={!input.trim() || isLoading}
                        className={cn(
                            'p-2 rounded-lg transition-all duration-200',
                            'active:scale-95',
                            input.trim() && !isLoading
                                ? 'bg-gradient-to-r from-violet-500 to-purple-500 text-white'
                                : isDark
                                    ? 'bg-zinc-700 text-zinc-500'
                                    : 'bg-zinc-200 text-zinc-400'
                        )}
                    >
                        {isLoading ? (
                            <Loader2 size={16} className="animate-spin" />
                        ) : (
                            <Send size={16} />
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
                            className={cn(
                                'flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs',
                                'bg-violet-500/20 text-violet-400'
                            )}
                            disabled
                        >
                            <Wand2 size={12} />
                            Planning
                        </button>
                        <button
                            onClick={() => onModeChange('mermaid')}
                            className={cn(
                                'flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs',
                                'transition-colors',
                                mode === 'mermaid'
                                    ? 'bg-violet-500/20 text-violet-400'
                                    : isDark
                                        ? 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'
                                        : 'text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100'
                            )}
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
