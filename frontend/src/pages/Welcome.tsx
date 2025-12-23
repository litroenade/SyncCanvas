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
            isDark
                ? 'bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950'
                : 'bg-gradient-to-br from-slate-50 via-white to-blue-50'
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

            {/* 主内容区域 */}
            <main className="relative z-10 flex-1 flex items-center px-6 pt-20 pb-12">

                <div className="w-full max-w-screen-2xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
                    
                    {/* ==================== 左侧 ==================== */}
                    <motion.div
                        variants={staggerContainer}
                        initial="initial"
                        animate="animate"
                        className="lg:col-span-7 text-left space-y-8 -mt-12 lg:-mt-32" 
                    >
                        <motion.div variants={fadeInUp}>
                            <span className={cn(
                                'inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-medium border',
                                isDark
                                    ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                                    : 'bg-blue-50 text-blue-600 border-blue-100'
                            )}>
                                <Sparkles size={14} />
                                AI 驱动的协作白板
                            </span>
                        </motion.div>

                        <motion.h1
                            variants={fadeInUp}
                            className={cn(
                                'text-7xl sm:text-8xl md:text-9xl font-extrabold leading-tight tracking-tight',
                                isDark ? 'text-white' : 'text-slate-900'
                            )}
                        >
                            <span className="bg-gradient-to-r from-blue-500 via-violet-500 to-purple-500 bg-clip-text text-transparent block mb-2">
                                创意协作
                            </span>
                            从这里开始
                        </motion.h1>

                        <motion.p
                            variants={fadeInUp}
                            className={cn(
                                'text-lg md:text-xl max-w-lg leading-relaxed',
                                isDark ? 'text-slate-400' : 'text-slate-600'
                            )}
                        >
                            SyncCanvas 是你的无限创意空间。
                            基于 Excalidraw 核心，支持多人实时编辑、
                            <span className={cn(
                                'font-medium',
                                isDark ? 'text-violet-400' : 'text-violet-600'
                            )}>AI 智能绘图</span>
                            与 Git 风格版本控制。
                        </motion.p>
                    </motion.div>


                    {/* ==================== 右侧 ==================== */}
                    <motion.div
                        variants={staggerContainer}
                        initial="initial"
                        animate="animate"
                        className={cn(
                            "lg:col-span-5 flex flex-col items-center lg:items-start justify-center",
                            "lg:-ml-12",
                            "gap-16",
                            "mt-12 lg:mt-32"
                        )}
                    >
                        {/* 1. 按钮组 */}
                        <motion.div
                            variants={fadeInUp}
                            className="flex flex-col gap-4 w-80 mx-auto" 
                        >
                            <motion.button
                                transition={{ duration: 0.2, ease: "easeOut" }}
                                whileHover={{ scale: 1.05, translateY: -2 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={handleGetStarted}
                                className={cn(
                                    'flex items-center justify-center gap-3 px-8 py-5 rounded-2xl',
                                    'bg-gradient-to-r from-blue-600 to-indigo-600',
                                    'text-white font-bold text-lg',
                                    'shadow-xl shadow-blue-600/20 hover:shadow-blue-600/40',
                                    'transition-shadow duration-200'
                                )}
                            >
                                开始使用
                                <ArrowRight size={20} />
                            </motion.button>

                            <motion.button
                                transition={{ duration: 0.2, ease: "easeOut" }}
                                whileHover={{ scale: 1.05, translateY: -2 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={handleQuickStart}
                                className={cn(
                                    'flex items-center justify-center gap-3 px-8 py-5 rounded-2xl',
                                    'font-bold text-lg border-2',
                                    'transition-colors duration-200',
                                    isDark
                                        ? 'border-slate-700 text-slate-300 hover:bg-slate-800'
                                        : 'border-slate-200 text-slate-700 hover:bg-white hover:shadow-lg'
                                )}
                            >
                                <Zap size={20} className="text-yellow-500" />
                                游客体验
                            </motion.button>
                        </motion.div>

                        {/* 2. 特性卡片组 */}
                        <motion.div
                            variants={fadeInUp}
                            className="grid grid-cols-3 gap-4 w-full"
                        >
                            {features.map((feature, index) => (
                                <motion.div
                                    key={index}
                                    variants={floatAnimation}
                                    style={{ animationDelay: `${index * 0.5}s` }}
                                    transition={{ duration: 0.2, ease: "easeOut" }}
                                    whileHover={{ scale: 1.05, y: -5 }} 
                                    className={cn(
                                        'aspect-square p-4 rounded-2xl backdrop-blur-sm flex flex-col items-center justify-center text-center gap-3 cursor-default',
                                        'transition-colors duration-300',
                                        isDark
                                            ? 'bg-slate-800/40 border border-slate-700/50 hover:bg-slate-800/60'
                                            : 'bg-white/60 border border-slate-200/50 hover:bg-white/90 hover:shadow-xl'
                                    )}
                                >
                                    <div className={cn(
                                        'w-12 h-12 rounded-xl flex items-center justify-center shrink-0',
                                        `bg-gradient-to-br ${feature.gradient}`,
                                        'text-white shadow-md'
                                    )}>
                                        <feature.icon size={22} />
                                    </div>
                                    
                                    <div className="flex flex-col gap-1 w-full overflow-hidden">
                                        <h3 className={cn(
                                            'font-bold text-sm truncate',
                                            isDark ? 'text-white' : 'text-slate-900'
                                        )}>
                                            {feature.title}
                                        </h3>
                                        <p className={cn(
                                            'text-[12px] leading-tight opacity-80',
                                            isDark ? 'text-slate-400' : 'text-slate-500'
                                        )}>
                                            {feature.desc}
                                        </p>
                                    </div>
                                </motion.div>
                            ))}
                        </motion.div>
                    </motion.div>

                </div>
            </main>

            {/* 底部：爱心跳动 */}
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
                    <motion.span
                        className="text-red-400 inline-block cursor-default" // inline-block 才能进行 transform 变换
                        animate={{ scale: [1, 1.2, 1] }} // 关键帧：原始大小 -> 放大1.2倍 -> 回到原始大小
                        transition={{
                            duration: 2.5, // 2.5秒完成一次循环
                            repeat: Infinity, // 无限循环
                            ease: "easeInOut" // 缓入缓出
                        }}
                    >
                        ♥
                    </motion.span>
                </span>
            </motion.footer>
        </div>
    )
}
