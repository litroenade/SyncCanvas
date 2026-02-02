/**
 * 模块名称: ThemeProvider
 * 主要功能: 主题提供者组件
 * 
 * 提供统一的主题包装，根据 useThemeStore 的状态自动应用 dark class。
 */

import React, { useEffect, ReactNode } from 'react';
import { useThemeStore } from '../../stores/useThemeStore';
import { ThemeWaveTransition } from './ThemeWaveTransition';

interface ThemeProviderProps {
    /** 子组件 */
    children: ReactNode;
}

/**
 * 主题提供者组件
 * 
 * 功能：
 * - 监听主题状态变化
 * - 自动为 document.documentElement 添加/移除 dark class
 * - Excalidraw 会自动根据 theme prop 管理画布颜色
 * - 提供主题切换动画 (ThemeWaveTransition)
 * 
 * @example
 * ```tsx
 * <ThemeProvider>
 *   <App />
 * </ThemeProvider>
 * ```
 */
export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
    const { theme } = useThemeStore();

    useEffect(() => {
        const root = document.documentElement;

        if (theme === 'dark') {
            root.classList.add('dark');
        } else {
            root.classList.remove('dark');
        }
    }, [theme]);

    return (
        <>
            <ThemeWaveTransition />
            {children}
        </>
    );
};

export default ThemeProvider;
