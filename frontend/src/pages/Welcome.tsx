/**
 * 欢迎页面 - Landing Page
 *
 * 应用启动的第一个页面，简洁展示品牌和入口
 */
import React from 'react'
import { useNavigate } from 'react-router-dom'
import { cn } from '../lib/utils'
import { useThemeStore } from '../stores/useThemeStore'
import {
    ArrowRight,
    Moon,
    Sun,
    Zap,
} from 'lucide-react'

export const Welcome: React.FC = () => {
    const navigate = useNavigate()
    const { theme, toggleTheme } = useThemeStore()

    const handleGetStarted = () => {
        const token = localStorage.getItem('token')
        const isGuest = localStorage.getItem('isGuest')
        if (token || isGuest) {
            navigate('/rooms')
        } else {
            navigate('/login')
        }
    }

    const handleQuickStart = () => {
        // 游客快速开始
        localStorage.removeItem('token')
        localStorage.removeItem('username')
        localStorage.setItem('isGuest', 'true')
        navigate('/rooms')
    }

    const isDark = theme === 'dark'

    return (
        <div className={cn(
            'min-h-screen flex flex-col',
            isDark ? 'bg-slate-900' : 'bg-slate-50'
        )}>
            {/* 顶部导航 */}
            <header className={cn(
                'flex items-center justify-between px-6 py-4',
                isDark ? 'border-slate-800' : 'border-slate-200'
            )}>
                <div className="flex items-center gap-3">
                    <div className={cn(
                        'w-9 h-9 rounded-xl flex items-center justify-center font-bold text-white',
                        'bg-gradient-to-br from-blue-500 to-indigo-600'
                    )}>
                        S
                    </div>
                    <span className={cn(
                        'font-semibold text-lg',
                        isDark ? 'text-white' : 'text-slate-900'
                    )}>
                        SyncCanvas
                    </span>
                </div>

                <button
                    onClick={toggleTheme}
                    className={cn(
                        'p-2 rounded-lg transition-colors',
                        isDark
                            ? 'hover:bg-slate-800 text-slate-400'
                            : 'hover:bg-slate-200 text-slate-600'
                    )}
                >
                    {isDark ? <Moon size={20} /> : <Sun size={20} />}
                </button>
            </header>

            {/* 主内容 */}
            <main className="flex-1 flex flex-col items-center justify-center px-6 pb-20">
                <div className="max-w-lg w-full text-center">
                    {/* 标题 */}
                    <h1 className={cn(
                        'text-4xl sm:text-5xl font-bold mb-4',
                        isDark ? 'text-white' : 'text-slate-900'
                    )}>
                        实时协作白板
                    </h1>

                    {/* 描述 */}
                    <p className={cn(
                        'text-lg mb-10',
                        isDark ? 'text-slate-400' : 'text-slate-600'
                    )}>
                        基于 Excalidraw，支持多人实时编辑、AI 智能绘图、Git 风格版本控制
                    </p>

                    {/* 按钮组 */}
                    <div className="flex flex-col sm:flex-row gap-3 justify-center">
                        <button
                            onClick={handleGetStarted}
                            className={cn(
                                'flex items-center justify-center gap-2 px-6 py-3 rounded-xl',
                                'bg-blue-600 hover:bg-blue-700 text-white font-medium',
                                'transition-colors'
                            )}
                        >
                            开始使用
                            <ArrowRight size={18} />
                        </button>

                        <button
                            onClick={handleQuickStart}
                            className={cn(
                                'flex items-center justify-center gap-2 px-6 py-3 rounded-xl',
                                'font-medium transition-colors border',
                                isDark
                                    ? 'border-slate-700 text-slate-300 hover:bg-slate-800'
                                    : 'border-slate-300 text-slate-700 hover:bg-slate-100'
                            )}
                        >
                            <Zap size={18} />
                            游客体验
                        </button>
                    </div>
                </div>

                {/* 特性简介 */}
                <div className={cn(
                    'mt-16 grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-2xl w-full text-center',
                    isDark ? 'text-slate-400' : 'text-slate-600'
                )}>
                    <div>
                        <div className={cn(
                            'text-2xl mb-2',
                            isDark ? 'text-slate-300' : 'text-slate-700'
                        )}>
                            多人协作
                        </div>
                        <p className="text-sm">实时同步，光标可见</p>
                    </div>
                    <div>
                        <div className={cn(
                            'text-2xl mb-2',
                            isDark ? 'text-slate-300' : 'text-slate-700'
                        )}>
                            AI 绘图
                        </div>
                        <p className="text-sm">自然语言生成流程图</p>
                    </div>
                    <div>
                        <div className={cn(
                            'text-2xl mb-2',
                            isDark ? 'text-slate-300' : 'text-slate-700'
                        )}>
                            版本控制
                        </div>
                        <p className="text-sm">Git 风格，随时回滚</p>
                    </div>
                </div>
            </main>

            {/* 底部 */}
            <footer className={cn(
                'text-center py-4 text-sm',
                isDark ? 'text-slate-600' : 'text-slate-400'
            )}>
                基于 Excalidraw + Yjs 构建
            </footer>
        </div>
    )
}
