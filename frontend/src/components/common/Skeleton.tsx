/**
 * 骨架屏组件
 *
 * 用于页面加载时显示占位效果，提升用户体验
 */
import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

interface SkeletonProps {
    className?: string;
    variant?: 'text' | 'circular' | 'rectangular' | 'rounded';
    width?: string | number;
    height?: string | number;
    animation?: 'pulse' | 'wave' | 'none';
}

/**
 * 基础骨架屏组件
 */
export const Skeleton: React.FC<SkeletonProps> = ({
    className,
    variant = 'text',
    width,
    height,
    animation = 'pulse',
}) => {
    const baseClasses = cn(
        'bg-gradient-to-r from-zinc-200 via-zinc-300 to-zinc-200',
        'dark:from-zinc-800 dark:via-zinc-700 dark:to-zinc-800',
        {
            'rounded-full': variant === 'circular',
            'rounded-none': variant === 'rectangular',
            'rounded-xl': variant === 'rounded',
            'rounded h-4': variant === 'text',
        },
        className
    );

    const style: React.CSSProperties = {
        width: width,
        height: height,
    };

    if (animation === 'pulse') {
        return (
            <motion.div
                className={baseClasses}
                style={style}
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
            />
        );
    }

    if (animation === 'wave') {
        return (
            <div className={cn(baseClasses, 'overflow-hidden relative')} style={style}>
                <motion.div
                    className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent dark:via-white/10"
                    animate={{ x: ['-100%', '100%'] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                />
            </div>
        );
    }

    return <div className={baseClasses} style={style} />;
};

/**
 * 房间卡片骨架屏
 */
export const RoomCardSkeleton: React.FC<{ isDark?: boolean }> = ({ isDark }) => {
    return (
        <div
            className={cn(
                'p-5 rounded-2xl border',
                isDark
                    ? 'bg-slate-800/50 border-slate-700'
                    : 'bg-white border-slate-200'
            )}
        >
            {/* 头部: 图标 + 操作按钮 */}
            <div className="flex items-start justify-between mb-4">
                <Skeleton
                    variant="rounded"
                    width={48}
                    height={48}
                    animation="wave"
                />
                <div className="flex gap-1">
                    <Skeleton variant="rounded" width={32} height={32} />
                    <Skeleton variant="rounded" width={32} height={32} />
                </div>
            </div>

            {/* 房间名称 */}
            <Skeleton variant="text" className="h-6 w-3/4 mb-3" animation="wave" />

            {/* 统计信息 */}
            <div className="flex gap-3 mb-2">
                <Skeleton variant="rounded" width={60} height={20} />
                <Skeleton variant="rounded" width={50} height={20} />
            </div>

            {/* 画布统计 */}
            <div className="flex gap-3 mt-2">
                <Skeleton variant="text" className="h-3 w-12" />
                <Skeleton variant="text" className="h-3 w-12" />
            </div>

            {/* 创建时间 */}
            <Skeleton variant="text" className="h-3 w-24 mt-2" />
        </div>
    );
};

/**
 * 房间列表骨架屏
 */
export const RoomListSkeleton: React.FC<{ count?: number; isDark?: boolean }> = ({
    count = 6,
    isDark,
}) => {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: count }).map((_, index) => (
                <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                >
                    <RoomCardSkeleton isDark={isDark} />
                </motion.div>
            ))}
        </div>
    );
};
