import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ThemeState {
    theme: 'light' | 'dark';
    isTransitioning: boolean;
    lastTransitionTime: number;
    toggleTheme: () => void;
    realToggleTheme: () => void;
    endTransition: () => void;
    setTheme: (theme: 'light' | 'dark') => void;
}

/**
 * 主题状态管理
 * 
 * 简化版本：只管理全局主题，Excalidraw 画布颜色由其内部自动管理
 */
export const useThemeStore = create<ThemeState>()(
    persist(
        (set, get) => ({
            theme: 'light',
            isTransitioning: false,
            lastTransitionTime: 0,
            
            // 用户点击切换时调用此方法
            // 它只开启过渡状态，实际的主题切换由动画组件触发 realToggleTheme 来完成
            toggleTheme: () => {
                const { isTransitioning, lastTransitionTime } = get();
                const now = Date.now();
                // 如果正在过渡，且距离上次开始不到 1.5 秒（动画1秒+缓冲），则忽略
                // 如果超过这个时间，认为是状态卡住了，强制允许新的切换
                if (isTransitioning && (now - lastTransitionTime < 1500)) return;
                
                set({ isTransitioning: true, lastTransitionTime: now });
            },

            // 真正切换主题状态（由动画组件在适当的时机调用）
            realToggleTheme: () => set((state) => ({
                theme: state.theme === 'light' ? 'dark' : 'light'
            })),

            // 动画结束
            endTransition: () => set({ isTransitioning: false }),

            setTheme: (theme) => set({ theme }),
        }),
        {
            name: 'theme-storage',
            // 只持久化 theme 字段
            partialize: (state) => ({ theme: state.theme } as any),
        }
    )
);
