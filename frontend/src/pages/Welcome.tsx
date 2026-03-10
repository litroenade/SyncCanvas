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

export const Welcome: React.FC = () => {
    const navigate = useNavigate()
    const { theme, toggleTheme } = useThemeStore()

    // 用来判断鼠标是否悬停在“按钮区域”，从而控制背景圆的缩放
    const [isHoveringButtons, setIsHoveringButtons] = React.useState(false)

    // 2. [新增] 扩散状态 (控制变大盖满全屏)
    const isExpanding = false

    const [redirectPath, setRedirectPath] = React.useState<string | null>(null) // 新增：记录要去哪里
    const [introProgress, setIntroProgress] = React.useState(0)
    const [isIntroVisible, setIsIntroVisible] = React.useState(true)
    const [isIntroOpening, setIsIntroOpening] = React.useState(false)
    const [isOutroVisible, setIsOutroVisible] = React.useState(false)

    React.useEffect(() => {
        if (!isIntroVisible) {
            return
        }

        let progress = 0
        let openTimer: number | undefined
        let hideTimer: number | undefined

        const interval = window.setInterval(() => {
            progress = Math.min(100, progress + (progress < 68 ? 5 : progress < 90 ? 3 : 1))
            setIntroProgress(progress)

            if (progress >= 100) {
                window.clearInterval(interval)
                openTimer = window.setTimeout(() => setIsIntroOpening(true), 160)
                hideTimer = window.setTimeout(() => setIsIntroVisible(false), 1120)
            }
        }, 78)

        return () => {
            window.clearInterval(interval)
            if (openTimer) {
                window.clearTimeout(openTimer)
            }
            if (hideTimer) {
                window.clearTimeout(hideTimer)
            }
        }
    }, [isIntroVisible])

    React.useEffect(() => {
        if (!isOutroVisible || !redirectPath) {
            return
        }

        const timer = window.setTimeout(() => {
            navigate(redirectPath)
        }, 1320)

        return () => window.clearTimeout(timer)
    }, [isOutroVisible, navigate, redirectPath])

    const handleTransition = (path: string) => {
        if (isOutroVisible) {
            return
        }

        setRedirectPath(path)
        setIsOutroVisible(true)
    }

    // 修改原有的点击函数，改为调用 handleTransition
    const handleGetStarted = () => {
        handleTransition('/login')
    }

    const handleQuickStart = () => {
        localStorage.removeItem('token')
        localStorage.removeItem('username')
        localStorage.setItem('isGuest', 'true')
        handleTransition('/rooms')
    }

    const isDark = theme === 'dark'
    const isHeroRevealed = isIntroOpening || !isIntroVisible

        const features = [
        {
            icon: Users,
            title: '多人协作',
            desc: '实时同步，光标可见',
            gradient: 'from-blue-500 to-cyan-500',
            layout: 'self-start w-40 h-40 md:w-44 md:h-44 lg:left-[-29rem] lg:bottom-[-5rem] lg:w-44 lg:h-44 lg:-rotate-[3deg]',
            iconWrapper: 'w-11 h-11 lg:w-12 lg:h-12',
            iconSize: 20,
            revealX: 320,
            revealY: 110,
            revealDelay: 0.16
        },
        {
            icon: Sparkles,
            title: 'AI 绘图',
            desc: '自然语言生成图表',
            gradient: 'from-violet-500 to-purple-500',
            layout: 'self-center -mt-5 w-48 h-48 md:w-52 md:h-52 lg:left-[-14rem] lg:bottom-[-2.5rem] lg:w-52 lg:h-52 lg:rotate-[1.5deg]',
            iconWrapper: 'w-12 h-12 lg:w-14 lg:h-14',
            iconSize: 24,
            revealX: 270,
            revealY: 40,
            revealDelay: 0.24
        },
        {
            icon: GitBranch,
            title: '版本控制',
            desc: 'Git 风格，随时回滚',
            gradient: 'from-orange-500 to-rose-500',
            layout: 'self-end -mt-5 w-56 h-56 md:w-60 md:h-60 lg:left-[1rem] lg:bottom-[0.5rem] lg:w-60 lg:h-60 lg:rotate-[4deg]',
            iconWrapper: 'w-14 h-14 lg:w-16 lg:h-16',
            iconSize: 28,
            revealX: 210,
            revealY: -42,
            revealDelay: 0.32
        },
    ]
        const actionButtons = [
        {
            key: 'quick-start',
            label: '游客体验',
            icon: <Zap size={22} className="text-yellow-500" />,
            onClick: handleQuickStart,
            layout: 'self-end mt-3 w-full max-w-[20.5rem] md:max-w-[22.5rem] lg:left-[9.4rem] lg:top-[19.625rem] lg:w-[17.1rem] lg:h-[5.15rem] lg:-rotate-[2deg]',
            className: isDark
                ? 'border-slate-700 text-slate-300 hover:bg-slate-800'
                : 'border-slate-200 text-slate-700 hover:bg-white hover:shadow-lg',
            revealX: 250,
            revealY: 120,
            revealDelay: 0.28
        },
        {
            key: 'get-started',
            label: '开始使用',
            icon: <ArrowRight size={22} />,
            onClick: handleGetStarted,
            layout: 'self-end -mt-1 w-full max-w-[22.5rem] md:max-w-[24.5rem] lg:left-[13.5rem] lg:top-[12.625rem] lg:w-[19.5rem] lg:h-[5.65rem] lg:rotate-[2deg]',
            className: 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-xl shadow-blue-600/20 hover:shadow-blue-600/40',
            revealX: 300,
            revealY: -32,
            revealDelay: 0.18
        }
    ]

    return (
        <div className={cn(
            'min-h-screen flex flex-col overflow-hidden relative',
            isDark
                ? 'bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950'
                : 'bg-gradient-to-br from-slate-50 via-white to-blue-50'
        )}>
            {isIntroVisible && (
                <div
                    className="absolute inset-0 z-[100] overflow-hidden"
                >
                    <motion.div
                        className={cn(
                            'absolute z-[120] w-[5.4rem] -translate-x-1/2 text-center text-[1.08rem] font-semibold font-mono tabular-nums tracking-[0.03em] will-change-transform drop-shadow-[0_0_10px_rgba(99,102,241,0.35)]',
                            isDark ? 'text-slate-200' : 'text-slate-700'
                        )}
                        style={{ top: 'calc(50% - 2.4rem)' }}
                        animate={{
                            left: `clamp(2.6rem, ${introProgress}%, calc(100% - 2.6rem))`,
                            opacity: isIntroOpening ? 0 : 1
                        }}
                        transition={{ duration: 0.18, ease: 'easeOut' }}
                    >
                        {introProgress}%
                    </motion.div>

                    <motion.div
                        className={cn(
                            'absolute inset-x-0 top-0 h-1/2',
                            isDark ? 'bg-slate-950' : 'bg-slate-50'
                        )}
                        animate={{ y: isIntroOpening ? '-100%' : '0%' }}
                        transition={{ duration: 0.82, ease: [0.16, 1, 0.3, 1] }}
                    >
                        <div className={cn(
                            'absolute bottom-0 left-0 h-[5px] w-full overflow-hidden',
                            isDark ? 'bg-slate-800' : 'bg-slate-200'
                        )}>
                            <motion.div
                                className="absolute inset-y-0 left-0 bg-gradient-to-r from-blue-500 via-indigo-500 to-violet-500 shadow-[0_0_28px_rgba(79,70,229,0.45)]"
                                animate={{ width: `${introProgress}%` }}
                                transition={{ duration: 0.18, ease: 'easeOut' }}
                            />
                        </div>
                    </motion.div>

                    <motion.div
                        className={cn(
                            'absolute inset-x-0 bottom-0 h-1/2',
                            isDark ? 'bg-slate-950' : 'bg-slate-50'
                        )}
                        animate={{ y: isIntroOpening ? '100%' : '0%' }}
                        transition={{ duration: 0.82, ease: [0.16, 1, 0.3, 1] }}
                    >
                        <div className={cn(
                            'absolute top-0 left-0 h-[5px] w-full overflow-hidden',
                            isDark ? 'bg-slate-800' : 'bg-slate-200'
                        )}>
                            <motion.div
                                className="absolute inset-y-0 left-0 bg-gradient-to-r from-blue-500 via-indigo-500 to-violet-500 shadow-[0_0_28px_rgba(79,70,229,0.45)]"
                                animate={{ width: `${introProgress}%` }}
                                transition={{ duration: 0.18, ease: 'easeOut' }}
                            />
                        </div>
                    </motion.div>
                </div>
            )}

            {isOutroVisible && (
                <div className="absolute inset-0 z-[140] overflow-hidden pointer-events-auto">
                    <motion.div
                        initial={{ y: '-100%' }}
                        animate={{ y: '0%' }}
                        transition={{ duration: 0.78, ease: [0.16, 1, 0.3, 1] }}
                        className={cn(
                            'absolute inset-x-0 top-0 h-1/2',
                            isDark ? 'bg-slate-950' : 'bg-slate-50'
                        )}
                    >
                        <motion.div
                            initial={{ scaleX: 1 }}
                            animate={{ scaleX: 0 }}
                            transition={{ duration: 0.46, delay: 0.78, ease: [0.32, 0, 0.2, 1] }}
                            style={{ transformOrigin: 'center center' }}
                            className="absolute bottom-0 left-0 h-[5px] w-full bg-gradient-to-r from-blue-500 via-indigo-500 to-violet-500 shadow-[0_0_28px_rgba(79,70,229,0.45)]"
                        />
                    </motion.div>
                    <motion.div
                        initial={{ y: '100%' }}
                        animate={{ y: '0%' }}
                        transition={{ duration: 0.78, ease: [0.16, 1, 0.3, 1] }}
                        className={cn(
                            'absolute inset-x-0 bottom-0 h-1/2',
                            isDark ? 'bg-slate-950' : 'bg-slate-50'
                        )}
                    >
                        <motion.div
                            initial={{ scaleX: 1 }}
                            animate={{ scaleX: 0 }}
                            transition={{ duration: 0.46, delay: 0.78, ease: [0.32, 0, 0.2, 1] }}
                            style={{ transformOrigin: 'center center' }}
                            className="absolute top-0 left-0 h-[5px] w-full bg-gradient-to-r from-blue-500 via-indigo-500 to-violet-500 shadow-[0_0_28px_rgba(79,70,229,0.45)]"
                        />
                    </motion.div>
                </div>
            )}
            {/* 背景装饰 */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                {/* 1. 右上角：四分之一圆 (最终完美版：变色+柔和) */}
                <motion.div
                    initial={{ scale: 1, opacity: 0.3 }}
                    animate={{
                        // 1. 大小：扩散时变大，平时根据鼠标悬停变动
                        scale: isExpanding ? 40 : (isHoveringButtons ? 1.6 : 1),

                        // 2. 透明度：扩散时变成实心(1)，平时保持通透(0.3)
                        opacity: isExpanding ? 1 : 0.3,

                        // 3. 【核心修改】背景颜色动态变化：
                        // 这里使用 Hex 颜色代码以确保平滑过渡
                        backgroundColor: isDark
                            ? (isExpanding ? '#172554' : '#2563EB')
                            : (isExpanding ? '#BFDBFE' : '#60A5FA'),
                    }}
                    transition={{
                        duration: isExpanding ? 0.5 : 0.6,
                        // 贝塞尔曲线：前慢后快，极速冲击
                        ease: isExpanding ? [0.7, 0, 0.84, 0] : 'easeInOut'
                    }}
                    // 动画结束跳转
                    onAnimationComplete={() => {
                        if (isExpanding && redirectPath) {
                            navigate(redirectPath)
                        }
                    }}
                    className={cn(
                        'absolute -top-[200px] -right-[200px] w-[600px] h-[600px] rounded-full blur-[80px]',
                        'pointer-events-auto',
                        isExpanding ? 'z-50' : 'z-0',
                    )}
                />

                {/* 2. 左下角：保持原样 (静态) */}
                <div className={cn(
                    'absolute -bottom-40 -left-40 w-96 h-96 rounded-full blur-3xl opacity-30',
                    isDark ? 'bg-violet-600' : 'bg-violet-400'
                )} />

                {/* 3. 网格背景：保持原样 (SVG) */}
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
            <main className="relative z-10 flex-1 flex items-center px-6 pt-12 pb-8 lg:pt-6 lg:pb-4 pointer-events-none">
                <div className="w-full max-w-screen-2xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
                    {/* ==================== 左侧 ==================== */}
                    <motion.div
                        variants={staggerContainer}
                        initial="initial"
                        animate="animate"
                        className="lg:col-span-7 text-left space-y-8 -mt-12 lg:-mt-32 pointer-events-auto"
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

                        <motion.div
                            animate={isHeroRevealed ? { x: 0, opacity: 1 } : { x: -72, opacity: 0 }}
                            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1], delay: 0.08 }}
                            className="block"
                        >
                            <span className="bg-gradient-to-r from-blue-500 via-violet-500 to-purple-500 bg-clip-text text-transparent block mb-2 text-7xl sm:text-8xl md:text-9xl font-extrabold leading-tight tracking-tight">
                                创意协作
                            </span>
                        </motion.div>

                        <motion.div
                            animate={isHeroRevealed ? { x: 0, opacity: 1 } : { x: -92, opacity: 0 }}
                            transition={{ duration: 0.76, ease: [0.16, 1, 0.3, 1], delay: 0.16 }}
                            className={cn(
                                'text-7xl sm:text-8xl md:text-9xl font-extrabold leading-tight tracking-tight',
                                isDark ? 'text-white' : 'text-slate-900'
                            )}
                        >
                            从这里开始
                        </motion.div>

                        <motion.p
                            animate={isHeroRevealed ? { x: 0, opacity: 1 } : { x: -64, opacity: 0 }}
                            transition={{ duration: 0.82, ease: [0.16, 1, 0.3, 1], delay: 0.24 }}
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
                            'lg:col-span-5 flex justify-center pointer-events-auto',
                            'mt-8 lg:-mt-4 lg:-ml-10'
                        )}
                    >
                        <motion.div
                            variants={fadeInUp}
                            onMouseEnter={() => setIsHoveringButtons(true)}
                            onMouseLeave={() => setIsHoveringButtons(false)}
                            className={cn(
                                'relative flex w-full max-w-[28rem] flex-col items-stretch pb-2',
                                'lg:block lg:w-[45rem] lg:max-w-none lg:h-[44rem] lg:pb-0'
                            )}
                        >
                            {actionButtons.map((button, index) => (
                                <motion.div
                                    key={button.key}
                                    animate={isHeroRevealed
                                        ? { x: 0, y: 0, opacity: 1 }
                                        : { x: button.revealX, y: button.revealY, opacity: 0 }}
                                    transition={{
                                        duration: 0.92,
                                        ease: [0.16, 1, 0.3, 1],
                                        delay: button.revealDelay
                                    }}
                                    className={cn(
                                        'relative z-20 lg:absolute',
                                        button.layout
                                    )}
                                >
                                    <motion.div
                                        animate={isHeroRevealed ? { y: [0, -8, 0] } : { y: 0 }}
                                        transition={{
                                            duration: 3.2,
                                            repeat: isHeroRevealed ? Infinity : 0,
                                            ease: 'easeInOut',
                                            delay: index * 0.4
                                        }}
                                        whileHover={{ scale: 1.03, y: -4 }}
                                        whileTap={{ scale: 0.97 }}
                                        className="h-full w-full"
                                    >
                                        <button
                                            onClick={button.onClick}
                                            className={cn(
                                                'flex h-full w-full items-center justify-center gap-2.5 rounded-[1.55rem] px-6.5 py-4 text-[0.98rem] font-bold transition-all duration-200',
                                                'border-2 backdrop-blur-sm',
                                                button.key === 'get-started' ? 'border-transparent' : '',
                                                button.className
                                            )}
                                        >
                                            {button.key === 'quick-start' && button.icon}
                                            {button.label}
                                            {button.key === 'get-started' && button.icon}
                                        </button>
                                    </motion.div>
                                </motion.div>
                            ))}

                            {features.map((feature, index) => (
                                <motion.div
                                    key={index}
                                    animate={isHeroRevealed
                                        ? { x: 0, y: 0, opacity: 1 }
                                        : { x: feature.revealX, y: feature.revealY, opacity: 0 }}
                                    transition={{
                                        duration: 0.96,
                                        ease: [0.16, 1, 0.3, 1],
                                        delay: feature.revealDelay
                                    }}
                                    className={cn(
                                        'relative lg:absolute',
                                        feature.layout
                                    )}
                                >
                                    <motion.div
                                        animate={isHeroRevealed ? { y: [0, -10, 0] } : { y: 0 }}
                                        transition={{
                                            duration: 3,
                                            repeat: isHeroRevealed ? Infinity : 0,
                                            ease: 'easeInOut',
                                            delay: index * 0.5
                                        }}
                                        whileHover={{ scale: 1.04, y: -5 }}
                                        className={cn(
                                            'flex h-full w-full flex-col items-center justify-center gap-2.5 rounded-[1.6rem] p-4.5 text-center cursor-default',
                                            'backdrop-blur-sm transition-colors duration-300',
                                            isDark
                                                ? 'bg-slate-800/40 border border-slate-700/50 hover:bg-slate-800/60'
                                                : 'bg-white/60 border border-slate-200/60 hover:bg-white/90 hover:shadow-xl'
                                        )}
                                    >
                                        <div className={cn(
                                            'rounded-[1.4rem] flex items-center justify-center shrink-0 text-white shadow-md',
                                            feature.iconWrapper,
                                            `bg-gradient-to-br ${feature.gradient}`
                                        )}>
                                            <feature.icon size={feature.iconSize} />
                                        </div>

                                        <div className="flex flex-col gap-2 w-full overflow-hidden">
                                            <h3 className={cn(
                                                'font-bold text-[1.4rem] lg:text-[1.55rem] leading-none',
                                                isDark ? 'text-white' : 'text-slate-900'
                                            )}>
                                                {feature.title}
                                            </h3>
                                            <p className={cn(
                                                'text-[12px] lg:text-[13px] leading-relaxed opacity-80',
                                                isDark ? 'text-slate-400' : 'text-slate-500'
                                            )}>
                                                {feature.desc}
                                            </p>
                                        </div>
                                    </motion.div>
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
                        className="text-red-400 inline-block cursor-default"
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{
                            duration: 2.5,
                            repeat: Infinity,
                            ease: 'easeInOut'
                        }}
                    >
                        ♥
                    </motion.span>
                </span>
            </motion.footer>
        </div>
    )
}












































