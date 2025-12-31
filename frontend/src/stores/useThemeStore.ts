import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ThemeState {
    theme: 'light' | 'dark';
    toggleTheme: () => void;
    setTheme: (theme: 'light' | 'dark') => void;
}

/**
 * 主题状态管理
 * 
 * 简化版本：只管理全局主题，Excalidraw 画布颜色由其内部自动管理
 */
export const useThemeStore = create<ThemeState>()(
    persist(
        (set) => ({
            theme: 'light',
            toggleTheme: () => set((state) => ({
                theme: state.theme === 'light' ? 'dark' : 'light'
            })),
            setTheme: (theme) => set({ theme }),
        }),
        {
            name: 'theme-storage',
        }
    )
);
