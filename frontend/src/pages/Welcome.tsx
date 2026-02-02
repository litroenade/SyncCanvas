/**
 * 欢迎页面 - Landing Page
 *
 * 应用启动的第一个页面，现代化设计，视觉冲击力强
 */
import React from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { cn } from '../lib/utils'
import { useThemeStore } from '../stores/useThemeStore'
import {
    ArrowRight,
    Moon,
    Sun,
    Zap,
    Users,
    Sparkles,
    GitBranch,
    Layers,
} from 'lucide-react'

// 动画配置
const fadeInUp = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.5 }
}

const staggerContainer = {
    animate: {
        transition: {
            staggerChildren: 0.1
        }
    }
}

const floatAnimation = {
    animate: {
        y: [0, -10, 0],
        transition: {
            duration: 3,
            repeat: Infinity,
            ease: "easeInOut" as const
        }
    }
}

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
        localStorage.removeItem('token')
        localStorage.removeItem('username')
        localStorage.setItem('isGuest', 'true')
        navigate('/rooms')
    }

    const isDark = theme === 'dark'

    const features = [
        {
            icon: Users,
            title: '多人协作',
            desc: '实时同步，光标可见',
            gradient: 'from-blue-500 to-cyan-500'
        },
        {
            icon: Sparkles,
            title: 'AI 绘图',
            desc: '自然语言生成图表',
            gradient: 'from-violet-500 to-purple-500'
        },
        {
            icon: GitBranch,
            title: '版本控制',
            desc: 'Git 风格，随时回滚',
            gradient: 'from-orange-500 to-rose-500'
        },
    ]

    return (
        <div className={cn(
            'min-h-screen flex flex-col overflow-hidden relative',
            (isDark
                ? 'bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950'
                : 'bg-gradient-to-br from-slate-50 via-white to-blue-50')
        )}>
            {/* 背景装饰 */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                {/* 渐变光晕 */}
                <div className={cn(
                    'absolute -top-40 -right-40 w-96 h-96 rounded-full blur-3xl opacity-30',
                    isDark ? 'bg-blue-600' : 'bg-blue-400'
                )} />
                <div className={cn(
                    'absolute -bottom-40 -left-40 w-96 h-96 rounded-full blur-3xl opacity-30',
                    isDark ? 'bg-violet-600' : 'bg-violet-400'
                )} />

                {/* 网格背景 */}
                <div
                    className={cn(
                        'absolute inset-0 opacity-[0.02]',
                        isDark && 'opacity-[0.05]'
                    )}
                    style={{
                        backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23${isDark ? 'fff' : '000'}' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`
                    }}
                />
            </div>

            {/* 顶部导航 */}
            <motion.header
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                    'relative z-10 flex items-center justify-between px-6 py-4 md:px-12',
                    isDark ? 'border-slate-800' : 'border-slate-200'
                )}
            >
                <div className="flex items-center gap-3">
                    <motion.div
                        whileHover={{ scale: 1.05, rotate: 5 }}
                        className={cn(
                            'w-10 h-10 rounded-xl flex items-center justify-center font-bold text-white shadow-lg',
                            'bg-gradient-to-br from-blue-500 via-indigo-500 to-violet-600'
                        )}
                    >
                        <Layers size={20} />
                    </motion.div>
                    <span className={cn(
                        'font-bold text-xl tracking-tight',
                        isDark ? 'text-white' : 'text-slate-900'
                    )}>
                        SyncCanvas
                    </span>
                </div>

                <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={toggleTheme}
                    className={cn(
                        'p-2.5 rounded-xl transition-all duration-300',
                        isDark
                            ? 'bg-slate-800/50 hover:bg-slate-700/50 text-yellow-400 border border-slate-700'
                            : 'bg-white/50 hover:bg-white text-slate-600 border border-slate-200 shadow-sm'
                    )}
                >
                    {isDark ? <Sun size={18} /> : <Moon size={18} />}
                </motion.button>
            </motion.header>

            {/* 主内容 */}
            <main className="relative z-10 flex-1 flex flex-col items-center justify-center px-6 pb-20">
                <motion.div
                    className="max-w-2xl w-full text-center"
                    variants={staggerContainer}
                    initial="initial"
                    animate="animate"
                >
                    {/* 徽章 */}
                    <motion.div
                        variants={fadeInUp}
                        className="mb-6"
                    >
                        <span className={cn(
                            'inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-medium',
                            isDark
                                ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                                : 'bg-blue-50 text-blue-600 border border-blue-100'
                        )}>
                            <Sparkles size={14} />
                            AI 驱动的协作白板
                        </span>
                    </motion.div>

                    {/* 标题 */}
                    <motion.h1
                        variants={fadeInUp}
                        className={cn(
                            'text-4xl sm:text-5xl md:text-6xl font-extrabold mb-6 leading-tight',
                            isDark ? 'text-white' : 'text-slate-900'
                        )}
                    >
                        <span className="bg-gradient-to-r from-blue-500 via-violet-500 to-purple-500 bg-clip-text text-transparent">
                            创意协作
                        </span>
                        <br />
                        从这里开始
                    </motion.h1>

                    {/* 描述 */}
                    <motion.p
                        variants={fadeInUp}
                        className={cn(
                            'text-lg md:text-xl mb-10 max-w-lg mx-auto leading-relaxed',
                            isDark ? 'text-slate-400' : 'text-slate-600'
                        )}
                    >
                        基于 Excalidraw，支持多人实时编辑、
                        <span className={cn(
                            'font-medium',
                            isDark ? 'text-violet-400' : 'text-violet-600'
                        )}>AI 智能绘图</span>
                        、Git 风格版本控制
                    </motion.p>

                    {/* 按钮组 */}
                    <motion.div
                        variants={fadeInUp}
                        className="flex flex-col sm:flex-row gap-4 justify-center mb-16"
                    >
                        <motion.button
                            whileHover={{ scale: 1.02, boxShadow: "0 20px 40px -15px rgba(59, 130, 246, 0.5)" }}
                            whileTap={{ scale: 0.98 }}
                            onClick={handleGetStarted}
                            className={cn(
                                'flex items-center justify-center gap-2 px-8 py-4 rounded-2xl',
                                'bg-gradient-to-r from-blue-500 via-blue-600 to-indigo-600',
                                'text-white font-semibold text-lg',
                                'shadow-xl shadow-blue-500/25',
                                'transition-all duration-300'
                            )}
                        >
                            开始使用
                            <ArrowRight size={20} />
                        </motion.button>

                        <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={handleQuickStart}
                            className={cn(
                                'flex items-center justify-center gap-2 px-8 py-4 rounded-2xl',
                                'font-semibold text-lg transition-all duration-300 border-2',
                                isDark
                                    ? 'border-slate-700 text-slate-300 hover:bg-slate-800/50 hover:border-slate-600'
                                    : 'border-slate-200 text-slate-700 hover:bg-white hover:border-slate-300 hover:shadow-lg'
                            )}
                        >
                            <Zap size={20} className="text-yellow-500" />
                            游客体验
                        </motion.button>
                    </motion.div>

                    {/* 特性卡片 */}
                    <motion.div
                        variants={fadeInUp}
                        className="grid grid-cols-1 sm:grid-cols-3 gap-4"
                    >
                        {features.map((feature, index) => (
                            <motion.div
                                key={index}
                                variants={floatAnimation}
                                animate="animate"
                                style={{ animationDelay: `${index * 0.5}s` }}
                                whileHover={{ scale: 1.05, y: -5 }}
                                className={cn(
                                    'p-6 rounded-2xl backdrop-blur-sm transition-all duration-300',
                                    isDark
                                        ? 'bg-slate-800/30 border border-slate-700/50 hover:border-slate-600'
                                        : 'bg-white/60 border border-slate-200/50 hover:border-slate-300 hover:shadow-xl'
                                )}
                            >
                                <div className={cn(
                                    'w-12 h-12 rounded-xl flex items-center justify-center mb-4 mx-auto',
                                    `bg-gradient-to-br ${feature.gradient}`,
                                    'text-white shadow-lg'
                                )}>
                                    <feature.icon size={24} />
                                </div>
                                <h3 className={cn(
                                    'font-bold text-lg mb-2',
                                    isDark ? 'text-white' : 'text-slate-900'
                                )}>
                                    {feature.title}
                                </h3>
                                <p className={cn(
                                    'text-sm',
                                    isDark ? 'text-slate-400' : 'text-slate-500'
                                )}>
                                    {feature.desc}
                                </p>
                            </motion.div>
                        ))}
                    </motion.div>
                </motion.div>
            </main>

            {/* 底部 */}
            <motion.footer
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
                className={cn(
                    'relative z-10 text-center py-6 text-sm',
                    isDark ? 'text-slate-600' : 'text-slate-400'
                )}
            >
                <span className="inline-flex items-center gap-2">
                    基于 Excalidraw + Yjs 构建
                    <span className="text-red-400">♥</span>
                </span>
            </motion.footer>
        </div>
    )
}
