/**
 * ChatInput 组件
 *
 * 聊天输入栏 - 严格按照参考设计
 *
 * 布局：
 * - 上方附件按钮（可选）
 * - 输入框 + 麦克风 + 发送按钮
 * - 下方：模式选择 + 模型选择器
 */
import React, { useRef, useEffect, useCallback, useState } from 'react';
import { cn } from '../../lib/utils';
import {
    Send,
    Loader2,
    Plus,
    ChevronUp,
    Check,
    Sparkles,
    Zap,
    Brain,
    FileCode2,
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { configApi, ModelGroup } from '../../services/api/config';

export type ConversationMode = 'agent' | 'planning' | 'mermaid';

interface ChatInputProps {
    /** 是否深色模式 */
    isDark: boolean;
    /** 输入值 */
    input: string;
    /** 设置输入值 */
    setInput: (value: string) => void;
    /** 是否加载中 */
    isLoading: boolean;
    /** 发送消息回调 */
    onSend: () => void;
    /** 占位符文本 */
    placeholder?: string;
    /** 当前模式 */
    mode: ConversationMode;
    /** 模式变更回调 */
    onModeChange: (mode: ConversationMode) => void;
}

export const ChatInput: React.FC<ChatInputProps> = ({
    isDark,
    input,
    setInput,
    isLoading,
    onSend,
    placeholder = '描述你想要的图形...',
    mode,
    onModeChange,
}) => {
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const queryClient = useQueryClient();
    const [modelMenuOpen, setModelMenuOpen] = useState(false);
    const [modeMenuOpen, setModeMenuOpen] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);
    const modeMenuRef = useRef<HTMLDivElement>(null);

    // 获取模型组
    const { data: modelGroups = {} } = useQuery<Record<string, ModelGroup>>({
        queryKey: ['model-groups'],
        queryFn: configApi.getModelGroups,
        staleTime: 60000,
    });

    const { data: currentModels } = useQuery({
        queryKey: ['current-models'],
        queryFn: configApi.getCurrentModels,
        staleTime: 30000,
    });

    const switchMutation = useMutation({
        mutationFn: (groupName: string) => configApi.switchModelGroup(groupName),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['current-models'] });
            setModelMenuOpen(false);
        },
    });

    const groupNames = Object.keys(modelGroups);
    const currentGroupName = currentModels?.current || '';
    const currentGroup = currentGroupName ? modelGroups[currentGroupName] : null;
    const displayModelName = currentGroup?.chat_model?.model || '默认模型';

    // 点击外部关闭菜单
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setModelMenuOpen(false);
            }
            if (modeMenuRef.current && !modeMenuRef.current.contains(e.target as Node)) {
                setModeMenuOpen(false);
            }
        };
        if (modelMenuOpen || modeMenuOpen) {
            document.addEventListener('mousedown', handleClickOutside);
            return () => document.removeEventListener('mousedown', handleClickOutside);
        }
    }, [modelMenuOpen, modeMenuOpen]);

    // 自动聚焦
    useEffect(() => {
        setTimeout(() => inputRef.current?.focus(), 100);
    }, []);

    // 自动调整高度
    useEffect(() => {
        const textarea = inputRef.current;
        if (textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
        }
    }, [input]);

    // 处理按键
    const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            onSend();
        }
    }, [onSend]);

    const modes = [
        {
            id: 'planning' as const,
            label: 'Ask',
            description: '先预览后添加，适合复杂任务和协作',
            icon: Brain,
        },
        {
            id: 'agent' as const,
            label: 'Agent',
            description: '直接在画布上执行任务，适合快速绘图',
            icon: Zap,
        },
        {
            id: 'mermaid' as const,
            label: 'Mermaid',
            description: '用 Mermaid 代码生成图表',
            icon: FileCode2,
        },
    ];

    const currentModeData = modes.find(m => m.id === mode) || modes[0];

    return (
        <div className={cn(
            'chat-input-container',
            'p-3 border-t',
            isDark ? 'border-zinc-800 bg-zinc-900' : 'border-zinc-200 bg-white'
        )}>
            {/* 输入框区域 */}
            <div className={cn(
                'flex items-end gap-2 px-3 py-2.5 rounded-2xl border',
                isDark
                    ? 'bg-zinc-800 border-zinc-700 focus-within:border-zinc-600'
                    : 'bg-zinc-50 border-zinc-200 focus-within:border-zinc-300',
                'transition-colors'
            )}>
                <textarea
                    ref={inputRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={placeholder}
                    disabled={isLoading}
                    rows={1}
                    className={cn(
                        'flex-1 resize-none bg-transparent outline-none',
                        'text-sm leading-relaxed',
                        'max-h-[120px] min-h-[24px]',
                        isDark
                            ? 'text-zinc-100 placeholder:text-zinc-500'
                            : 'text-zinc-900 placeholder:text-zinc-400',
                        isLoading && 'opacity-50'
                    )}
                />


                {/* 发送按钮 */}
                <button
                    onClick={onSend}
                    disabled={!input.trim() || isLoading}
                    className={cn(
                        'p-2 rounded-xl transition-all duration-200 flex-shrink-0',
                        input.trim() && !isLoading
                            ? 'bg-violet-500 hover:bg-violet-600 text-white'
                            : isDark
                                ? 'bg-zinc-700 text-zinc-500'
                                : 'bg-zinc-200 text-zinc-400'
                    )}
                    title="发送"
                >
                    {isLoading ? (
                        <Loader2 size={18} className="animate-spin" />
                    ) : (
                        <Send size={18} />
                    )}
                </button>
            </div>

            {/* 底部栏：+ | 模式选择 | 模型选择器 */}
            <div className="flex items-center gap-2 mt-2">
                {/* 附加按钮 */}
                <button
                    className={cn(
                        'p-1 rounded transition-colors',
                        isDark
                            ? 'text-zinc-500 hover:text-zinc-300'
                            : 'text-zinc-400 hover:text-zinc-600'
                    )}
                    title="添加附件"
                >
                    <Plus size={16} />
                </button>

                {/* 模式选择器 */}
                <div className="relative" ref={modeMenuRef}>
                    <button
                        onClick={() => setModeMenuOpen(!modeMenuOpen)}
                        className={cn(
                            'flex items-center gap-1 px-2 py-1 rounded-lg text-xs transition-colors',
                            isDark
                                ? 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
                                : 'text-zinc-500 hover:text-zinc-700 hover:bg-zinc-100'
                        )}
                    >
                        <ChevronUp
                            size={12}
                            className={cn(
                                'transition-transform',
                                !modeMenuOpen && 'rotate-180'
                            )}
                        />
                        <span>{currentModeData.label}</span>
                    </button>

                    {/* 模式菜单 */}
                    {modeMenuOpen && (
                        <div className={cn(
                            'absolute bottom-full left-0 mb-1 w-72 rounded-xl shadow-xl border overflow-hidden z-50',
                            isDark
                                ? 'bg-zinc-900 border-zinc-700'
                                : 'bg-white border-zinc-200'
                        )}>
                            <div className={cn(
                                'px-3 py-2 text-xs font-medium border-b',
                                isDark ? 'text-zinc-400 border-zinc-700' : 'text-zinc-500 border-zinc-200'
                            )}>
                                Conversation mode
                            </div>
                            {modes.map((modeItem) => (
                                <button
                                    key={modeItem.id}
                                    onClick={() => {
                                        onModeChange(modeItem.id);
                                        setModeMenuOpen(false);
                                    }}
                                    className={cn(
                                        'w-full px-3 py-2.5 text-left transition-colors',
                                        mode === modeItem.id
                                            ? isDark ? 'bg-violet-500/20' : 'bg-violet-50'
                                            : isDark ? 'hover:bg-zinc-800' : 'hover:bg-zinc-50'
                                    )}
                                >
                                    <div className="flex items-center gap-2">
                                        <modeItem.icon size={14} className={cn(
                                            mode === modeItem.id ? 'text-violet-500' :
                                                isDark ? 'text-zinc-400' : 'text-zinc-500'
                                        )} />
                                        <span className={cn(
                                            'text-sm font-medium',
                                            isDark ? 'text-zinc-200' : 'text-zinc-700'
                                        )}>
                                            {modeItem.label}
                                        </span>
                                        {mode === modeItem.id && (
                                            <Check size={14} className="text-violet-500 ml-auto" />
                                        )}
                                    </div>
                                    <div className={cn(
                                        'text-xs mt-1 ml-5',
                                        isDark ? 'text-zinc-500' : 'text-zinc-400'
                                    )}>
                                        {modeItem.description}
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {/* 模型选择器 */}
                <div className="relative" ref={menuRef}>
                    <button
                        onClick={() => setModelMenuOpen(!modelMenuOpen)}
                        className={cn(
                            'flex items-center gap-1 px-2 py-1 rounded-lg text-xs transition-colors',
                            isDark
                                ? 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
                                : 'text-zinc-500 hover:text-zinc-700 hover:bg-zinc-100'
                        )}
                    >
                        <ChevronUp
                            size={12}
                            className={cn(
                                'transition-transform',
                                !modelMenuOpen && 'rotate-180'
                            )}
                        />
                        <span className="max-w-[180px] truncate">
                            {currentGroupName || displayModelName}
                        </span>
                    </button>

                    {/* 模型菜单 */}
                    {modelMenuOpen && (
                        <div className={cn(
                            'absolute bottom-full left-0 mb-1 w-64 rounded-xl shadow-xl border overflow-hidden z-50',
                            isDark
                                ? 'bg-zinc-900 border-zinc-700'
                                : 'bg-white border-zinc-200'
                        )}>
                            <div className={cn(
                                'px-3 py-2 text-xs font-medium border-b',
                                isDark ? 'text-zinc-400 border-zinc-700' : 'text-zinc-500 border-zinc-200'
                            )}>
                                选择模型组
                            </div>
                            <div className="max-h-48 overflow-y-auto py-1">
                                {groupNames.length === 0 ? (
                                    <div className={cn(
                                        'px-3 py-3 text-xs text-center',
                                        isDark ? 'text-zinc-500' : 'text-zinc-400'
                                    )}>
                                        暂无模型配置
                                    </div>
                                ) : (
                                    groupNames.map((name) => {
                                        const group = modelGroups[name];
                                        const isSelected = name === currentGroupName;

                                        return (
                                            <button
                                                key={name}
                                                onClick={() => switchMutation.mutate(name)}
                                                className={cn(
                                                    'w-full flex items-center gap-2 px-3 py-2 text-left transition-colors',
                                                    isSelected
                                                        ? isDark ? 'bg-violet-500/20' : 'bg-violet-50'
                                                        : isDark ? 'hover:bg-zinc-800' : 'hover:bg-zinc-50'
                                                )}
                                            >
                                                <Sparkles size={12} className={cn(
                                                    isSelected ? 'text-violet-500' :
                                                        isDark ? 'text-zinc-500' : 'text-zinc-400'
                                                )} />
                                                <div className="flex-1 min-w-0">
                                                    <div className={cn(
                                                        'text-sm font-medium truncate',
                                                        isDark ? 'text-zinc-200' : 'text-zinc-700'
                                                    )}>
                                                        {name}
                                                    </div>
                                                    <div className={cn(
                                                        'text-xs truncate',
                                                        isDark ? 'text-zinc-500' : 'text-zinc-400'
                                                    )}>
                                                        {group.chat_model?.model || '未配置'}
                                                    </div>
                                                </div>
                                                {isSelected && (
                                                    <Check size={14} className="text-violet-500 flex-shrink-0" />
                                                )}
                                            </button>
                                        );
                                    })
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
