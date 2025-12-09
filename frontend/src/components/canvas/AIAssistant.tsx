/**
 * AI 助手组件
 * 
 * 提供与 LLM Agent 的交互界面，支持智能绘图命令和实时步骤反馈
 */
import React, { useState, useRef, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '../../lib/utils';
import { useAIStream } from '../../hooks/useAIStream';
import {
    Sparkles,
    Send,
    X,
    Loader2,
    ChevronUp,
    ChevronDown,
    Lightbulb,
    Wand2,
    Workflow,
    Database,
    AlertCircle,
    CheckCircle,
    Trash2,
} from 'lucide-react';

interface AIAssistantProps {
    roomId: string;
    isDark: boolean;
    isOpen: boolean;
    onClose: () => void;
}

interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system' | 'step';
    content: string;
    timestamp: number;
    status?: 'pending' | 'success' | 'error';
    stepInfo?: {
        step_number: number;
        action: string | null;
        latency_ms: number;
    };
}

// 预设提示词分类
const PRESET_CATEGORIES = [
    {
        name: '绘图',
        prompts: [
            { icon: Workflow, label: '流程图', prompt: '画一个简单的软件开发流程图，包含需求分析、设计、开发、测试、部署五个阶段' },
            { icon: Database, label: '数据流图', prompt: '画一个用户登录系统的数据流图，展示用户输入、验证、数据库查询的流程' },
            { icon: Wand2, label: '架构图', prompt: '画一个简单的微服务架构图，包含网关、用户服务、订单服务和数据库' },
        ]
    },
    {
        name: '对话',
        prompts: [
            { icon: Lightbulb, label: '解释概念', prompt: '解释一下什么是 CRDT (无冲突复制数据类型)' },
        ]
    }
];

// 扁平化预设 (用于渲染)
const PRESET_PROMPTS = PRESET_CATEGORIES.flatMap(cat => cat.prompts);

export const AIAssistant: React.FC<AIAssistantProps> = ({
    roomId,
    isDark,
    isOpen,
    onClose,
}) => {
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState<Message[]>([]);
    const [isExpanded, setIsExpanded] = useState(true);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // 使用 WebSocket 流式 AI
    const {
        isLoading,
        steps,
        response,
        error,
        sendRequest,
        reset,
    } = useAIStream({ roomId, autoConnect: isOpen });

    // 滚动到底部
    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages, steps, scrollToBottom]);

    // 自动聚焦输入框
    useEffect(() => {
        if (isOpen && inputRef.current) {
            setTimeout(() => inputRef.current?.focus(), 100);
        }
    }, [isOpen]);

    // 监听步骤更新
    useEffect(() => {
        if (steps.length > 0) {
            const latestStep = steps[steps.length - 1];
            // 更新最后一条助手消息的内容为当前步骤
            setMessages(prev => {
                // 兼容性写法：从后往前查找
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

        // 使用 WebSocket 发送请求
        await sendRequest(text);
    }, [input, isLoading, sendRequest, reset]);

    // 处理按键
    const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    }, [handleSend]);

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 20, scale: 0.95 }}
                transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                className={cn(
                    'fixed z-[100] shadow-2xl rounded-2xl overflow-hidden',
                    'border backdrop-blur-xl',
                    isDark
                        ? 'bg-zinc-900/95 border-zinc-700/50'
                        : 'bg-white/95 border-zinc-200/50'
                )}
                style={{
                    right: 'max(16px, env(safe-area-inset-right, 16px))',
                    bottom: 'max(80px, calc(env(safe-area-inset-bottom, 16px) + 64px))',
                    width: 'min(400px, calc(100vw - 32px))',
                    maxHeight: 'min(500px, calc(100vh - 160px))',
                }}
            >
                {/* 头部 */}
                {/* 头部 */}
                <div className={cn(
                    'flex items-center justify-between px-4 py-3 border-b',
                    isDark ? 'border-zinc-700/50' : 'border-zinc-200/50'
                )}>
                    <div className="flex items-center gap-2">
                        <div className={cn(
                            'w-8 h-8 rounded-xl flex items-center justify-center',
                            'bg-gradient-to-br from-violet-500 to-purple-600',
                            'text-white'
                        )}>
                            <Sparkles size={16} />
                        </div>
                        <div>
                            <h3 className={cn(
                                'text-sm font-semibold',
                                isDark ? 'text-white' : 'text-zinc-900'
                            )}>
                                AI 助手
                            </h3>
                            <p className={cn(
                                'text-[10px]',
                                isDark ? 'text-zinc-500' : 'text-zinc-400'
                            )}>
                                智能绘图 · 对话 · 信息获取
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-1">
                        {messages.length > 0 && (
                            <button
                                onClick={() => setMessages([])}
                                title="清除对话"
                                className={cn(
                                    'p-1.5 rounded-lg transition-colors',
                                    isDark
                                        ? 'hover:bg-zinc-800 text-zinc-400 hover:text-red-400'
                                        : 'hover:bg-zinc-100 text-zinc-500 hover:text-red-500'
                                )}
                            >
                                <Trash2 size={14} />
                            </button>
                        )}
                        <button
                            onClick={() => setIsExpanded(!isExpanded)}
                            className={cn(
                                'p-1.5 rounded-lg transition-colors',
                                isDark
                                    ? 'hover:bg-zinc-800 text-zinc-400'
                                    : 'hover:bg-zinc-100 text-zinc-500'
                            )}
                        >
                            {isExpanded ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
                        </button>
                        <button
                            onClick={onClose}
                            className={cn(
                                'p-1.5 rounded-lg transition-colors',
                                isDark
                                    ? 'hover:bg-zinc-800 text-zinc-400'
                                    : 'hover:bg-zinc-100 text-zinc-500'
                            )}
                        >
                            <X size={16} />
                        </button>
                    </div>
                </div>

                <AnimatePresence>
                    {isExpanded && (
                        <motion.div
                            initial={{ height: 0 }}
                            animate={{ height: 'auto' }}
                            exit={{ height: 0 }}
                            className="overflow-hidden"
                        >
                            {/* 消息列表 */}
                            <div className={cn(
                                'max-h-[280px] overflow-y-auto p-3 space-y-3',
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
                                            描述你想要的图形，AI 将帮你绘制
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
                                                'max-w-[85%] px-3 py-2 rounded-2xl text-sm',
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
                                                    <span>{msg.content}</span>
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                )}
                                <div ref={messagesEndRef} />
                            </div>

                            {/* 预设提示 */}
                            {messages.length === 0 && (
                                <div className={cn(
                                    'px-3 pb-3 grid grid-cols-2 gap-2',
                                    isDark ? 'border-zinc-700/50' : 'border-zinc-200/50'
                                )}>
                                    {PRESET_PROMPTS.map((preset, index) => (
                                        <button
                                            key={index}
                                            onClick={() => handleSend(preset.prompt)}
                                            disabled={isLoading}
                                            className={cn(
                                                'flex items-center gap-2 px-3 py-2 rounded-xl',
                                                'text-left text-xs font-medium',
                                                'transition-all duration-200',
                                                'active:scale-[0.98]',
                                                isDark
                                                    ? 'bg-zinc-800/50 hover:bg-zinc-800 text-zinc-300'
                                                    : 'bg-zinc-100/50 hover:bg-zinc-100 text-zinc-600',
                                                isLoading && 'opacity-50 cursor-not-allowed'
                                            )}
                                        >
                                            <preset.icon size={14} className="text-violet-500" />
                                            {preset.label}
                                        </button>
                                    ))}
                                </div>
                            )}

                            {/* 输入框 */}
                            <div className={cn(
                                'px-3 pb-3 pt-2 border-t',
                                isDark ? 'border-zinc-700/50' : 'border-zinc-200/50'
                            )}>
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
                                            'max-h-[100px] min-h-[24px]',
                                            isDark ? 'text-white' : 'text-zinc-900',
                                            isLoading && 'opacity-50'
                                        )}
                                        style={{
                                            height: 'auto',
                                            overflowY: input.split('\n').length > 3 ? 'auto' : 'hidden',
                                        }}
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
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.div>
        </AnimatePresence>
    );
};

