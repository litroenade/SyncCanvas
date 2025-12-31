/**
 * 模块名称：MobileFAB
 * 主要功能：移动端浮动操作按钮 + 底部抽屉菜单
 * 
 * 特性：
 * - 可拖拽定位
 * - iOS 安全区域支持
 * - 流畅的动画效果
 * - 底部抽屉式菜单
 */
import React, { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Undo2,
    Redo2,
    Trash2,
    Moon,
    Sun,
    Menu,
    X,
    Home,
    History,
    Users,
    Wifi,
    WifiOff,
    Loader2,
    GripVertical,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface FabPosition {
    x: number;
    y: number;
}

interface MobileFABProps {
    isDark: boolean;
    isConnected: boolean;
    isSynced: boolean;
    collaboratorsCount: number;
    onUndo: () => void;
    onRedo: () => void;
    onToggleTheme: () => void;
    onToggleHistory: () => void;
    onClearCanvas: () => void;
    onBackToRooms: () => void;
}

const FAB_SIZE = 52;
const FAB_STORAGE_KEY = 'mobile-fab-position';
const EDGE_MARGIN = 12;
const TOP_SAFE_ZONE = 80; // 避开 Excalidraw 顶部工具栏

/**
 * 获取安全的初始位置
 */
function getSafePosition(saved?: FabPosition | null): FabPosition {
    const windowWidth = typeof window !== 'undefined' ? window.innerWidth : 400;
    const windowHeight = typeof window !== 'undefined' ? window.innerHeight : 800;

    const defaultPos = {
        x: windowWidth - FAB_SIZE - EDGE_MARGIN,
        y: windowHeight - FAB_SIZE - 100, // 距离底部留出空间
    };

    if (!saved) return defaultPos;

    // 确保在安全范围内
    return {
        x: Math.min(Math.max(EDGE_MARGIN, saved.x), windowWidth - FAB_SIZE - EDGE_MARGIN),
        y: Math.min(Math.max(TOP_SAFE_ZONE, saved.y), windowHeight - FAB_SIZE - EDGE_MARGIN),
    };
}

/**
 * 状态配置
 */
function getStatusConfig(isConnected: boolean, isSynced: boolean) {
    if (!isConnected) {
        return {
            color: 'bg-red-500',
            textColor: 'text-red-500',
            icon: WifiOff,
            text: '离线',
            pulse: false,
        };
    }
    if (!isSynced) {
        return {
            color: 'bg-amber-500',
            textColor: 'text-amber-500',
            icon: Loader2,
            text: '同步中',
            pulse: true,
            spin: true,
        };
    }
    return {
        color: 'bg-emerald-500',
        textColor: 'text-emerald-500',
        icon: Wifi,
        text: '已连接',
        pulse: false,
    };
}

export const MobileFAB: React.FC<MobileFABProps> = ({
    isDark,
    isConnected,
    isSynced,
    collaboratorsCount,
    onUndo,
    onRedo,
    onToggleTheme,
    onToggleHistory,
    onClearCanvas,
    onBackToRooms,
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const [isDragging, setIsDragging] = useState(false);
    const [position, setPosition] = useState<FabPosition>(() => {
        try {
            const saved = localStorage.getItem(FAB_STORAGE_KEY);
            return getSafePosition(saved ? JSON.parse(saved) : null);
        } catch {
            return getSafePosition(null);
        }
    });

    const dragStartRef = useRef<{ x: number; y: number; posX: number; posY: number } | null>(null);

    // 窗口大小变化时确保按钮在屏幕内
    useEffect(() => {
        const handleResize = () => {
            setPosition(prev => getSafePosition(prev));
        };

        window.addEventListener('resize', handleResize);
        window.addEventListener('orientationchange', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            window.removeEventListener('orientationchange', handleResize);
        };
    }, []);

    // 拖拽处理
    const handlePointerDown = useCallback((e: React.PointerEvent) => {
        e.preventDefault();
        e.stopPropagation();

        dragStartRef.current = {
            x: e.clientX,
            y: e.clientY,
            posX: position.x,
            posY: position.y,
        };
        setIsDragging(false);
        (e.target as HTMLElement).setPointerCapture(e.pointerId);
    }, [position]);

    const handlePointerMove = useCallback((e: React.PointerEvent) => {
        if (!dragStartRef.current) return;

        const deltaX = e.clientX - dragStartRef.current.x;
        const deltaY = e.clientY - dragStartRef.current.y;
        const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

        // 超过阈值才开始拖拽
        if (distance > 10) {
            setIsDragging(true);

            const newX = Math.min(
                Math.max(EDGE_MARGIN, dragStartRef.current.posX + deltaX),
                window.innerWidth - FAB_SIZE - EDGE_MARGIN
            );
            const newY = Math.min(
                Math.max(TOP_SAFE_ZONE, dragStartRef.current.posY + deltaY),
                window.innerHeight - FAB_SIZE - EDGE_MARGIN
            );

            setPosition({ x: newX, y: newY });
        }
    }, []);

    const handlePointerUp = useCallback((e: React.PointerEvent) => {
        (e.target as HTMLElement).releasePointerCapture(e.pointerId);

        if (isDragging) {
            // 保存位置
            localStorage.setItem(FAB_STORAGE_KEY, JSON.stringify(position));
            // 延迟重置拖拽状态，避免触发点击
            setTimeout(() => setIsDragging(false), 100);
        } else if (dragStartRef.current) {
            // 点击事件
            setIsOpen(prev => !prev);
        }

        dragStartRef.current = null;
    }, [isDragging, position]);

    // 状态配置
    const statusConfig = useMemo(
        () => getStatusConfig(isConnected, isSynced),
        [isConnected, isSynced]
    );
    const StatusIcon = statusConfig.icon;

    // 菜单项
    const menuItems = useMemo(() => [
        {
            label: '撤销',
            icon: Undo2,
            onClick: onUndo,
            closeOnClick: true,
        },
        {
            label: '重做',
            icon: Redo2,
            onClick: onRedo,
            closeOnClick: true,
        },
        {
            label: isDark ? '浅色模式' : '深色模式',
            icon: isDark ? Sun : Moon,
            onClick: onToggleTheme,
            closeOnClick: true,
        },
        {
            label: '历史版本',
            icon: History,
            onClick: onToggleHistory,
            closeOnClick: true,
        },
        {
            label: '清空画布',
            icon: Trash2,
            onClick: () => {
                if (window.confirm('确定要清空画布吗？此操作不可撤销。')) {
                    onClearCanvas();
                    setIsOpen(false);
                }
            },
            danger: true,
            closeOnClick: false,
        },
        {
            label: '返回房间',
            icon: Home,
            onClick: onBackToRooms,
            closeOnClick: true,
        },
    ], [isDark, onUndo, onRedo, onToggleTheme, onToggleHistory, onClearCanvas, onBackToRooms]);

    return (
        <>
            {/* ==================== 底部抽屉遮罩 ==================== */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="fixed inset-0 z-[200] bg-black/30 backdrop-blur-[3px]"
                        onClick={() => setIsOpen(false)}
                    />
                )}
            </AnimatePresence>

            {/* ==================== 底部抽屉菜单 ==================== */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ y: '100%' }}
                        animate={{ y: 0 }}
                        exit={{ y: '100%' }}
                        transition={{
                            type: 'spring',
                            damping: 28,
                            stiffness: 350,
                            mass: 0.8,
                        }}
                        className={cn(
                            'mobile-bottom-sheet',
                            'fixed bottom-0 left-0 right-0 z-[201]',
                            'rounded-t-[20px]',
                            'glass-panel',
                            isDark ? 'bg-zinc-900/95' : 'bg-white/95'
                        )}
                        style={{
                            paddingBottom: 'max(24px, env(safe-area-inset-bottom, 24px))',
                            maxHeight: '80vh',
                            overflowY: 'auto',
                            overflowX: 'hidden'
                        }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* 拖拽指示条 */}
                        <div className="flex justify-center pt-3 pb-2">
                            <div className={cn(
                                'w-9 h-1 rounded-full transition-colors',
                                isDark ? 'bg-zinc-600' : 'bg-zinc-300'
                            )} />
                        </div>

                        {/* 状态栏 */}
                        <div className={cn(
                            'flex items-center justify-between mx-4 mb-4 px-4 py-3 rounded-2xl',
                            isDark ? 'bg-zinc-800/60' : 'bg-zinc-100/80'
                        )}>
                            {/* 连接状态 */}
                            <div className="flex items-center gap-2.5">
                                <div className="relative">
                                    <div className={cn(
                                        'w-2.5 h-2.5 rounded-full',
                                        statusConfig.color,
                                        statusConfig.pulse && 'animate-pulse'
                                    )} />
                                    {statusConfig.pulse && (
                                        <div className={cn(
                                            'absolute inset-0 w-2.5 h-2.5 rounded-full',
                                            statusConfig.color,
                                            'animate-ping opacity-75'
                                        )} />
                                    )}
                                </div>
                                <StatusIcon
                                    size={15}
                                    className={cn(
                                        statusConfig.textColor,
                                        statusConfig.spin && 'animate-spin'
                                    )}
                                />
                                <span className={cn(
                                    'text-sm font-medium',
                                    isDark ? 'text-zinc-200' : 'text-zinc-700'
                                )}>
                                    {statusConfig.text}
                                </span>
                            </div>

                            {/* 在线人数 */}
                            {collaboratorsCount > 0 && (
                                <div className={cn(
                                    'flex items-center gap-1.5 px-2.5 py-1 rounded-full',
                                    'bg-gradient-to-r from-violet-500/20 to-purple-500/20',
                                    'border',
                                    isDark ? 'border-violet-500/30' : 'border-violet-300/50'
                                )}>
                                    <Users size={13} className="text-violet-500" />
                                    <span className={cn(
                                        'text-xs font-semibold',
                                        isDark ? 'text-violet-300' : 'text-violet-600'
                                    )}>
                                        {collaboratorsCount + 1} 人在线
                                    </span>
                                </div>
                            )}
                        </div>

                        {/* 操作按钮网格 */}
                        <div className="grid grid-cols-3 gap-2 px-4">
                            {menuItems.map((item, index) => {
                                const Icon = item.icon;
                                return (
                                    <motion.button
                                        key={index}
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: index * 0.05 }}
                                        onClick={() => {
                                            item.onClick();
                                            if (item.closeOnClick) {
                                                setIsOpen(false);
                                            }
                                        }}
                                        className={cn(
                                            'flex flex-col items-center gap-2 py-4 rounded-2xl',
                                            'transition-all duration-150',
                                            'active:scale-95',
                                            isDark
                                                ? 'hover:bg-zinc-800/80 active:bg-zinc-700/80'
                                                : 'hover:bg-zinc-100 active:bg-zinc-200',
                                            item.danger && 'text-red-500'
                                        )}
                                    >
                                        <div className={cn(
                                            'w-12 h-12 rounded-2xl flex items-center justify-center',
                                            'transition-colors',
                                            item.danger
                                                ? isDark ? 'bg-red-500/15' : 'bg-red-50'
                                                : isDark ? 'bg-zinc-800' : 'bg-zinc-100'
                                        )}>
                                            <Icon
                                                size={22}
                                                strokeWidth={1.8}
                                                className={cn(
                                                    item.danger
                                                        ? 'text-red-500'
                                                        : isDark ? 'text-zinc-200' : 'text-zinc-700'
                                                )}
                                            />
                                        </div>
                                        <span className={cn(
                                            'text-xs font-medium',
                                            item.danger
                                                ? 'text-red-500'
                                                : isDark ? 'text-zinc-400' : 'text-zinc-600'
                                        )}>
                                            {item.label}
                                        </span>
                                    </motion.button>
                                );
                            })}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ==================== FAB 浮动按钮 ==================== */}
            <motion.div
                onPointerDown={handlePointerDown}
                onPointerMove={handlePointerMove}
                onPointerUp={handlePointerUp}
                onPointerCancel={handlePointerUp}
                animate={{
                    scale: isDragging ? 1.15 : 1,
                    boxShadow: isDragging
                        ? '0 20px 40px rgba(0,0,0,0.25)'
                        : '0 8px 24px rgba(0,0,0,0.15)',
                }}
                transition={{ type: 'spring', stiffness: 400, damping: 25 }}
                className={cn(
                    'fixed z-[202] touch-none select-none',
                    'flex items-center justify-center',
                    'rounded-2xl',
                    'transition-colors duration-200',
                    isDark
                        ? 'bg-zinc-800 border border-zinc-700/80'
                        : 'bg-white border border-zinc-200/80'
                )}
                style={{
                    left: position.x,
                    top: position.y,
                    width: FAB_SIZE,
                    height: FAB_SIZE,
                    cursor: isDragging ? 'grabbing' : 'pointer',
                }}
            >
                {/* 图标 */}
                <motion.div
                    animate={{ rotate: isOpen ? 135 : 0 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                >
                    {isOpen ? (
                        <X size={24} strokeWidth={2} className={isDark ? 'text-zinc-200' : 'text-zinc-700'} />
                    ) : (
                        <Menu size={24} strokeWidth={2} className={isDark ? 'text-zinc-200' : 'text-zinc-700'} />
                    )}
                </motion.div>

                {/* 状态指示点 */}
                {!isOpen && (
                    <div className="absolute -top-1 -right-1">
                        <div className={cn(
                            'w-3.5 h-3.5 rounded-full',
                            'border-2',
                            isDark ? 'border-zinc-800' : 'border-white',
                            statusConfig.color
                        )}>
                            {statusConfig.pulse && (
                                <div className={cn(
                                    'absolute inset-0 rounded-full',
                                    statusConfig.color,
                                    'animate-ping opacity-60'
                                )} />
                            )}
                        </div>
                    </div>
                )}

                {/* 拖拽提示（长按时显示） */}
                {isDragging && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="absolute inset-0 flex items-center justify-center rounded-2xl bg-black/10"
                    >
                        <GripVertical size={20} className="text-white/80" />
                    </motion.div>
                )}
            </motion.div>
        </>
    );
};
