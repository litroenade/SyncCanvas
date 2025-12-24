/**
 * AISidebar 组件
 *
 * AI 侧边栏主容器，统一聊天界面
 * 模式选择（Agent/Planning/Mermaid）只影响 AI 行为，不改变 UI
 * 支持拖拽调整宽度，收起/展开动画
 */
import React, { useState, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '../../lib/utils';
import { Bot, X, GripVertical } from 'lucide-react';
import { AgentMode } from './AgentMode';
import { ConversationMode } from './ChatInput';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ExcalidrawAPI = any;

interface AISidebarProps {
    /** 房间 ID */
    roomId: string;
    /** 是否深色模式 */
    isDark: boolean;
    /** 是否展开 */
    isOpen: boolean;
    /** 切换展开状态 */
    onToggle: () => void;
    /** Excalidraw API 引用（保留用于未来虚拟画布功能） */
    excalidrawAPI: ExcalidrawAPI | null;
}

type AIMode = ConversationMode;  // 'agent' | 'planning' | 'mermaid'

const MIN_WIDTH = 360;
const MAX_WIDTH = 800;
const DEFAULT_WIDTH = 450;
const STORAGE_KEY = 'ai-sidebar-mode';

export const AISidebar: React.FC<AISidebarProps> = ({
    roomId,
    isDark,
    isOpen,
    onToggle,
    excalidrawAPI,
}) => {
    // 从 localStorage 加载上次使用的模式，默认 Ask (planning) 模式
    const [mode, setMode] = useState<AIMode>(() => {
        const saved = localStorage.getItem(STORAGE_KEY) as AIMode | null;
        return saved && ['agent', 'planning', 'mermaid'].includes(saved) ? saved : 'planning';
    });
    const [width, setWidth] = useState(DEFAULT_WIDTH);
    const [isResizing, setIsResizing] = useState(false);
    const sidebarRef = useRef<HTMLDivElement>(null);

    // 保存模式到 localStorage
    useEffect(() => {
        localStorage.setItem(STORAGE_KEY, mode);
    }, [mode]);

    // 处理拖拽调整宽度
    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        setIsResizing(true);
    }, []);

    useEffect(() => {
        if (!isResizing) return;

        const handleMouseMove = (e: MouseEvent) => {
            const newWidth = window.innerWidth - e.clientX;
            setWidth(Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, newWidth)));
        };

        const handleMouseUp = () => {
            setIsResizing(false);
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);

        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isResizing]);

    return (
        <>
            {/* 始终可见的边缘标签 - 用于展开侧边栏 */}
            {!isOpen && (
                <button
                    onClick={onToggle}
                    className={cn(
                        'fixed z-[50] flex items-center gap-2',
                        'py-3 px-2 rounded-l-xl',
                        'transition-all duration-300',
                        'shadow-lg hover:shadow-xl',
                        isDark
                            ? 'bg-zinc-800/90 hover:bg-zinc-700 text-zinc-300 border border-r-0 border-zinc-700/50'
                            : 'bg-white/90 hover:bg-zinc-50 text-zinc-700 border border-r-0 border-zinc-200',
                        'backdrop-blur-xl'
                    )}
                    style={{ right: 0, top: '50%', transform: 'translateY(-50%)' }}
                >
                    <Bot size={20} className="text-violet-500" />
                </button>
            )}

            <AnimatePresence>
                {isOpen && (
                    <motion.aside
                        ref={sidebarRef}
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width, opacity: 1 }}
                        exit={{ width: 0, opacity: 0 }}
                        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                        className={cn(
                            'ai-sidebar',
                            'fixed right-0 top-0 bottom-0 z-[45]',
                            'h-full flex flex-col',
                            'border-l',
                            isDark
                                ? 'bg-zinc-900/95 border-zinc-700/50'
                                : 'bg-white/95 border-zinc-200/50',
                            'backdrop-blur-xl'
                        )}
                        style={{
                            '--sidebar-width': `${width}px`,
                        } as React.CSSProperties}
                    >
                        {/* 拖拽调整宽度手柄 */}
                        <div
                            className={cn(
                                'absolute left-0 top-0 bottom-0 w-1 cursor-ew-resize',
                                'hover:bg-violet-500/50 transition-colors',
                                'flex items-center justify-center',
                                isResizing && 'bg-violet-500/50'
                            )}
                            onMouseDown={handleMouseDown}
                        >
                            <GripVertical
                                size={12}
                                className={cn(
                                    'opacity-0 hover:opacity-100 transition-opacity',
                                    isDark ? 'text-zinc-500' : 'text-zinc-400'
                                )}
                            />
                        </div>

                        {/* 头部 */}
                        <div
                            className={cn(
                                'flex items-center justify-between',
                                'px-4 py-3 border-b',
                                isDark ? 'border-zinc-700/50' : 'border-zinc-200/50'
                            )}
                        >
                            <div className="flex items-center gap-2">
                                <div
                                    className={cn(
                                        'p-1.5 rounded-lg',
                                        'bg-gradient-to-br from-violet-500 to-purple-600'
                                    )}
                                >
                                    <Bot size={16} className="text-white" />
                                </div>
                                <span
                                    className={cn(
                                        'font-semibold text-sm',
                                        isDark ? 'text-zinc-100' : 'text-zinc-800'
                                    )}
                                >
                                    AI 助手
                                </span>
                            </div>
                            <button
                                onClick={onToggle}
                                className={cn(
                                    'p-1.5 rounded-lg transition-colors',
                                    isDark
                                        ? 'hover:bg-zinc-700 text-zinc-400'
                                        : 'hover:bg-zinc-100 text-zinc-500'
                                )}
                            >
                                <X size={18} />
                            </button>
                        </div>

                        {/* 聊天界面 - 统一的聊天体验，模式只影响 AI 行为 */}
                        <div className="flex-1 overflow-hidden">
                            <AgentMode
                                roomId={roomId}
                                isDark={isDark}
                                mode={mode}
                                onModeChange={setMode}
                                excalidrawAPI={excalidrawAPI}
                            />
                        </div>
                    </motion.aside>
                )}
            </AnimatePresence>
        </>
    );
};
