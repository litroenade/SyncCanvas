/**
 * AgentMode 组件
 *
 * Agent 模式：现代对话气泡式聊天界面
 * 支持工具调用的折叠展示和模型选择
 */
import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { cn } from '../../lib/utils';
import {
    Loader2,
    ChevronDown,
    ChevronRight,
    Bot,
    User,
    Clock,
    XCircle,
    Wrench,
    Sparkles,
} from 'lucide-react';
import { useAIStream } from '../../hooks/useAIStream';
import { ToolProgress, ToolStep } from './ToolProgress';
import { ChatInput, ConversationMode } from './ChatInput';
import { VirtualCanvas } from './VirtualCanvas';
import { MermaidCodePreview, extractMermaidCode } from './MermaidCodePreview';
import './AgentMode.css';

interface AgentModeProps {
    roomId: string;
    isDark: boolean;
    onElementsCreated?: (elementIds: string[]) => void;
    mode: ConversationMode;
    onModeChange: (mode: ConversationMode) => void;
    /** 当用户发送第一条消息时调用，用于生成对话标题 */
    onFirstMessage?: (message: string) => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    excalidrawAPI?: any;
}

interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: number;
    status?: 'thinking' | 'working' | 'completed' | 'error';
    thinkingTime?: number;
    steps?: ToolStep[];
    model?: string;
    /** 虚拟模式返回的元素（用于 Planning 模式预览） */
    virtualElements?: Record<string, unknown>[];
    /** 消息发送时使用的模式 */
    usedMode?: ConversationMode;
}

export const AgentMode: React.FC<AgentModeProps> = ({
    roomId,
    isDark,
    onElementsCreated,
    mode,
    onModeChange,
    onFirstMessage,
    excalidrawAPI,
}) => {
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set());
    const [thinkingStartTime, setThinkingStartTime] = useState<number | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // 使用 WebSocket 流式 AI
    const {
        isLoading,
        steps,
        response,
        error,
        sendRequest,
        reset,
        elementsCreated,
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

    // 滚动到底部
    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages, scrollToBottom]);

    // 切换消息展开状态
    const toggleMessage = useCallback((messageId: string) => {
        setExpandedMessages(prev => {
            const next = new Set(prev);
            if (next.has(messageId)) {
                next.delete(messageId);
            } else {
                next.add(messageId);
            }
            return next;
        });
    }, []);

    // 监听步骤更新
    useEffect(() => {
        if (isLoading && steps.length > 0) {
            setMessages(prev => {
                const lastMessage = prev[prev.length - 1];
                if (!lastMessage || lastMessage.role !== 'assistant' || lastMessage.status === 'completed') {
                    return prev;
                }

                return prev.map((msg, i) =>
                    i === prev.length - 1
                        ? { ...msg, steps: toolSteps, status: 'working' as const }
                        : msg
                );
            });
        }
    }, [steps, toolSteps, isLoading]);

    // 监听完成响应
    useEffect(() => {
        if (response && !isLoading) {
            const thinkingTime = thinkingStartTime
                ? Math.floor((Date.now() - thinkingStartTime) / 1000)
                : 0;

            setMessages(prev => prev.map((msg, i) =>
                i === prev.length - 1 && msg.role === 'assistant'
                    ? {
                        ...msg,
                        status: 'completed' as const,
                        content: response,
                        thinkingTime,
                        // 保存虚拟元素用于 Planning 模式预览
                        virtualElements: virtualElements && virtualElements.length > 0
                            ? virtualElements
                            : undefined,
                    }
                    : msg
            ));
            setThinkingStartTime(null);
        }
    }, [response, isLoading, thinkingStartTime, virtualElements]);

    // 监听错误
    useEffect(() => {
        if (error) {
            setMessages(prev => prev.map((msg, i) =>
                i === prev.length - 1 && msg.role === 'assistant'
                    ? { ...msg, status: 'error' as const, content: error }
                    : msg
            ));
            setThinkingStartTime(null);
        }
    }, [error]);

    // 当 AI 创建元素后通知父组件
    useEffect(() => {
        if (elementsCreated?.length > 0 && onElementsCreated) {
            onElementsCreated(elementsCreated);
        }
    }, [elementsCreated, onElementsCreated]);

    // 发送消息
    const handleSend = useCallback(async () => {
        const text = input.trim();
        if (!text || isLoading) return;

        // 如果是第一条消息，触发标题生成
        if (messages.length === 0 && onFirstMessage) {
            onFirstMessage(text);
        }

        // 添加用户消息
        const userMessage: ChatMessage = {
            id: `user-${Date.now()}`,
            role: 'user',
            content: text,
            timestamp: Date.now(),
        };

        // 添加 AI 占位消息
        const assistantMessage: ChatMessage = {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: '',
            timestamp: Date.now(),
            status: 'thinking',
        };

        setMessages(prev => [...prev, userMessage, assistantMessage]);
        setExpandedMessages(prev => new Set([...prev, assistantMessage.id]));
        setInput('');
        setThinkingStartTime(Date.now());
        reset();

        // 发送请求，传递当前模式
        await sendRequest(text, {
            theme: isDark ? 'dark' : 'light',
            mode,  // 传递当前选择的模式 (agent/planning/mermaid)
        });
    }, [input, isLoading, sendRequest, reset, isDark, mode, messages.length, onFirstMessage]);

    // 渲染消息
    const renderMessage = (message: ChatMessage) => {
        const isUser = message.role === 'user';
        const isExpanded = expandedMessages.has(message.id);
        const hasSteps = message.steps && message.steps.length > 0;

        return (
            <div
                key={message.id}
                className={cn(
                    'message-container flex gap-3 mb-4',
                    isUser ? 'flex-row-reverse' : 'flex-row'
                )}
            >
                {/* 头像 */}
                <div className={cn(
                    'flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center',
                    isUser
                        ? 'bg-gradient-to-br from-blue-500 to-cyan-500'
                        : 'bg-gradient-to-br from-violet-500 to-purple-600'
                )}>
                    {isUser ? (
                        <User size={16} className="text-white" />
                    ) : (
                        <Bot size={16} className="text-white" />
                    )}
                </div>

                {/* 消息内容 */}
                <div className={cn(
                    'flex-1 min-w-0',
                    isUser ? 'text-right' : 'text-left'
                )}>
                    {/* 消息气泡 */}
                    <div className={cn(
                        'inline-block max-w-[85%] rounded-2xl px-4 py-3',
                        isUser
                            ? isDark
                                ? 'bg-blue-600 text-white'
                                : 'bg-blue-500 text-white'
                            : isDark
                                ? 'bg-zinc-800 text-zinc-100'
                                : 'bg-white text-zinc-800 border border-zinc-200'
                    )}>
                        {/* AI 消息状态 */}
                        {!isUser && message.status && message.status !== 'completed' && (
                            <div className="flex items-center gap-2 mb-2">
                                {message.status === 'thinking' && (
                                    <>
                                        <Sparkles size={14} className="text-violet-400 animate-pulse" />
                                        <span className="text-xs text-violet-400">正在思考...</span>
                                    </>
                                )}
                                {message.status === 'working' && (
                                    <>
                                        <Loader2 size={14} className="text-blue-400 animate-spin" />
                                        <span className="text-xs text-blue-400">正在执行...</span>
                                    </>
                                )}
                                {message.status === 'error' && (
                                    <>
                                        <XCircle size={14} className="text-red-400" />
                                        <span className="text-xs text-red-400">执行出错</span>
                                    </>
                                )}
                            </div>
                        )}

                        {/* 消息文本 */}
                        <div className={cn(
                            'text-sm leading-relaxed whitespace-pre-wrap break-words',
                            !isUser && !message.content && 'min-h-[20px]'
                        )}>
                            {message.content || (message.status === 'thinking' ? '...' : '')}
                        </div>

                        {/* 思考时间 */}
                        {!isUser && message.thinkingTime && message.status === 'completed' && (
                            <div className={cn(
                                'flex items-center gap-1 mt-2 text-xs',
                                isDark ? 'text-zinc-500' : 'text-zinc-400'
                            )}>
                                <Clock size={12} />
                                <span>思考了 {message.thinkingTime} 秒</span>
                            </div>
                        )}
                    </div>

                    {/* 工具调用折叠区域 */}
                    {!isUser && hasSteps && (
                        <div className={cn(
                            'mt-2',
                            isUser ? 'text-right' : 'text-left'
                        )}>
                            <button
                                onClick={() => toggleMessage(message.id)}
                                className={cn(
                                    'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors',
                                    isDark
                                        ? 'bg-zinc-800/50 hover:bg-zinc-700/50 text-zinc-400'
                                        : 'bg-zinc-100 hover:bg-zinc-200 text-zinc-600'
                                )}
                            >
                                <Wrench size={12} />
                                <span>{message.steps!.length} 个工具调用</span>
                                {isExpanded ? (
                                    <ChevronDown size={12} />
                                ) : (
                                    <ChevronRight size={12} />
                                )}
                            </button>

                            {/* 展开的工具进度 */}
                            {isExpanded && (
                                <div className={cn(
                                    'mt-2 p-3 rounded-xl',
                                    isDark ? 'bg-zinc-800/30' : 'bg-zinc-50'
                                )}>
                                    <ToolProgress
                                        steps={message.steps!}
                                        className={isDark ? 'dark' : ''}
                                    />
                                </div>
                            )}
                        </div>
                    )}

                    {/* Planning 模式内嵌预览图 */}
                    {!isUser && message.virtualElements && message.virtualElements.length > 0 && (
                        <div className="mt-3">
                            <VirtualCanvas
                                key={`virtual-${message.id}`}
                                elements={message.virtualElements as unknown as import('../../lib/yjs').ExcalidrawElement[]}
                                files={{}}
                                isDark={isDark}
                                minHeight={150}
                                maxHeight={300}
                                onAddToCanvas={(elementsToAdd) => {
                                    if (!excalidrawAPI) {
                                        console.warn('excalidrawAPI 不可用');
                                        return;
                                    }
                                    const existingElements = excalidrawAPI.getSceneElements();
                                    excalidrawAPI.updateScene({
                                        elements: [...existingElements, ...elementsToAdd],
                                    });
                                    excalidrawAPI.scrollToContent(elementsToAdd, {
                                        fitToViewport: true,
                                        animate: true,
                                        duration: 300,
                                    });
                                    // 添加后清空该消息的虚拟元素，防止重复添加
                                    setMessages(prev => prev.map(msg =>
                                        msg.id === message.id
                                            ? { ...msg, virtualElements: undefined }
                                            : msg
                                    ));
                                }}
                            />
                        </div>
                    )}

                    {/* Mermaid 模式：检测代码块并显示代码+预览 */}
                    {!isUser && message.status === 'completed' && (() => {
                        const mermaidCode = extractMermaidCode(message.content);
                        if (mermaidCode) {
                            return (
                                <MermaidCodePreview
                                    code={mermaidCode}
                                    isDark={isDark}
                                    onAddToCanvas={(elements) => {
                                        if (!excalidrawAPI) {
                                            console.warn('excalidrawAPI 不可用');
                                            return;
                                        }
                                        const existingElements = excalidrawAPI.getSceneElements();
                                        excalidrawAPI.updateScene({
                                            elements: [...existingElements, ...elements],
                                        });
                                        excalidrawAPI.scrollToContent(elements, {
                                            fitToViewport: true,
                                            animate: true,
                                            duration: 300,
                                        });
                                    }}
                                />
                            );
                        }
                        return null;
                    })()}
                </div>
            </div>
        );
    };

    return (
        <div className="agent-mode h-full flex flex-col">
            {/* 消息列表 */}
            <div className={cn(
                'flex-1 overflow-y-auto p-4',
                messages.length === 0 && 'flex items-center justify-center'
            )}>
                {messages.length === 0 ? (
                    /* 空状态欢迎界面 */
                    <div className="text-center py-8 px-4 max-w-sm">
                        <div className={cn(
                            'inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4',
                            'bg-gradient-to-br from-violet-500/20 to-purple-600/20',
                            'border',
                            isDark ? 'border-violet-500/20' : 'border-violet-200'
                        )}>
                            <Sparkles size={32} className="text-violet-500" />
                        </div>
                        <h2 className={cn(
                            'text-lg font-semibold mb-2',
                            isDark ? 'text-zinc-100' : 'text-zinc-900'
                        )}>
                            AI Canvas Agent
                        </h2>
                        <p className={cn(
                            'text-sm',
                            isDark ? 'text-zinc-400' : 'text-zinc-500'
                        )}>
                            描述你想要的图形，AI 将分析需求并直接在画布上创建元素
                        </p>

                        {/* 快速提示 */}
                        <div className="mt-6 space-y-2">
                            {[
                                '画一个简单的流程图',
                                '创建一个前后端架构图',
                                '画一个数据流图',
                            ].map((prompt, index) => (
                                <button
                                    key={index}
                                    onClick={() => {
                                        setInput(prompt);
                                        setTimeout(() => handleSend(), 100);
                                    }}
                                    disabled={isLoading}
                                    className={cn(
                                        'w-full px-4 py-2.5 rounded-xl text-sm text-left transition-all',
                                        'border',
                                        isDark
                                            ? 'bg-zinc-800/50 border-zinc-700 hover:bg-zinc-700/50 text-zinc-300'
                                            : 'bg-white border-zinc-200 hover:bg-zinc-50 text-zinc-700',
                                        isLoading && 'opacity-50 cursor-not-allowed'
                                    )}
                                >
                                    {prompt}
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    <>
                        {messages.map(renderMessage)}
                        <div ref={messagesEndRef} />
                    </>
                )}
            </div>

            {/* 底部输入栏 */}
            <ChatInput
                isDark={isDark}
                input={input}
                setInput={setInput}
                isLoading={isLoading}
                onSend={handleSend}
                placeholder="描述你想要的图形..."
                mode={mode}
                onModeChange={onModeChange}
            />
        </div>
    );
};
