/**
 * 模块名称: ThemeProvider
 * 主要功能: 主题提供者组件
 * 
 * 提供统一的主题包装，根据 useThemeStore 的状态自动应用 dark class。
 */

import React, { useEffect, ReactNode } from 'react';
import { useThemeStore } from '../../stores/useThemeStore';

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
 * - 同步更新 Excalidraw 背景色配置
 * 
 * @example
 * ```tsx
 * <ThemeProvider>
 *   <App />
 * </ThemeProvider>
 * ```
 */
export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
    const { theme, setExcalidrawConfig } = useThemeStore();

    useEffect(() => {
        const root = document.documentElement;

        if (theme === 'dark') {
            root.classList.add('dark');
            setExcalidrawConfig({ viewBackgroundColor: '#1e1e1e' });
        } else {
            root.classList.remove('dark');
            setExcalidrawConfig({ viewBackgroundColor: '#ffffff' });
        }
    }, [theme, setExcalidrawConfig]);

    return <>{children}</>;
};

export default ThemeProvider;
