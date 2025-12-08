/**
 * 欢迎页面 - Landing Page
 * 
 * 应用启动的第一个页面，展示品牌和核心功能
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '../lib/utils';
import { useThemeStore } from '../stores/useThemeStore';
import {
    ArrowRight,
    Sparkles,
    Users,
    Moon,
    Sun,
    Zap,
    Shield,
    GitBranch,
} from 'lucide-react';

const features = [
    {
        icon: Users,
        title: '实时协作',
        description: '多人同时编辑，光标实时同步',
        gradient: 'from-blue-500 to-cyan-500',
    },
    {
        icon: GitBranch,
        title: '版本控制',
        description: 'Git 风格的历史记录，随时回滚',
        gradient: 'from-purple-500 to-pink-500',
    },
    {
        icon: Sparkles,
        title: 'AI 助手',
        description: '智能绘图，一键生成流程图',
        gradient: 'from-amber-500 to-orange-500',
    },
    {
        icon: Shield,
        title: '安全可靠',
        description: '房间密码保护，数据安全存储',
        gradient: 'from-emerald-500 to-teal-500',
    },
];

export const Welcome: React.FC = () => {
    const navigate = useNavigate();
    const { theme, toggleTheme } = useThemeStore();
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
        // 检查是否已登录，自动跳转
        const token = localStorage.getItem('token');
        const isGuest = localStorage.getItem('isGuest');
        if (token || isGuest) {
            // 已有登录状态，但让用户选择是否继续
        }
    }, []);

    const handleGetStarted = () => {
        const token = localStorage.getItem('token');
        const isGuest = localStorage.getItem('isGuest');
        if (token || isGuest) {
            navigate('/rooms');
        } else {
            navigate('/login');
        }
    };

    const handleQuickStart = () => {
        // 游客快速开始
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        localStorage.setItem('isGuest', 'true');
        navigate('/rooms');
    };

    const isDark = theme === 'dark';

    return (
        <div className={cn(
            'min-h-screen relative overflow-hidden transition-colors duration-500',
            isDark ? 'bg-slate-950' : 'bg-white'
        )}>
            {/* 背景装饰 */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                {/* 渐变光斑 */}
                <div className={cn(
                    'absolute -top-[40%] -left-[20%] w-[80%] h-[80%] rounded-full blur-[120px]',
                    isDark ? 'bg-blue-900/30' : 'bg-blue-200/50'
                )} />
                <div className={cn(
                    'absolute top-[20%] -right-[20%] w-[60%] h-[60%] rounded-full blur-[100px]',
                    isDark ? 'bg-purple-900/20' : 'bg-purple-200/40'
                )} />
                <div className={cn(
                    'absolute -bottom-[30%] left-[20%] w-[70%] h-[70%] rounded-full blur-[120px]',
                    isDark ? 'bg-indigo-900/20' : 'bg-indigo-200/30'
                )} />

                {/* 网格背景 */}
                <div className={cn(
                    'absolute inset-0 bg-[linear-gradient(rgba(0,0,0,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(0,0,0,0.03)_1px,transparent_1px)]',
                    'bg-[size:60px_60px]',
                    isDark && 'bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)]'
                )} />
            </div>

            {/* 主题切换按钮 */}
            <button
                onClick={toggleTheme}
                className={cn(
                    'fixed top-6 right-6 z-50 p-3 rounded-full transition-all duration-300',
                    'backdrop-blur-md border',
                    isDark
                        ? 'bg-slate-800/50 border-slate-700 text-slate-300 hover:bg-slate-700/50'
                        : 'bg-white/50 border-slate-200 text-slate-600 hover:bg-white/80 shadow-sm'
                )}
            >
                {isDark ? <Moon size={20} /> : <Sun size={20} />}
            </button>

            {/* 主内容 */}
            <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
                {/* Hero Section */}
                <div className="pt-20 sm:pt-32 pb-16 sm:pb-24 text-center">
                    <AnimatePresence>
                        {mounted && (
                            <>
                                {/* Logo */}
                                <motion.div
                                    initial={{ scale: 0.5, opacity: 0 }}
                                    animate={{ scale: 1, opacity: 1 }}
                                    transition={{ type: 'spring', duration: 0.8 }}
                                    className="mb-8"
                                >
                                    <div className={cn(
                                        'inline-flex items-center justify-center w-20 h-20 rounded-3xl',
                                        'bg-gradient-to-br from-blue-500 via-indigo-500 to-purple-600',
                                        'text-white text-4xl font-bold shadow-2xl shadow-blue-500/30',
                                        'transform rotate-3'
                                    )}>
                                        S
                                    </div>
                                </motion.div>

                                {/* 标题 */}
                                <motion.h1
                                    initial={{ y: 20, opacity: 0 }}
                                    animate={{ y: 0, opacity: 1 }}
                                    transition={{ delay: 0.2, duration: 0.6 }}
                                    className={cn(
                                        'text-4xl sm:text-6xl lg:text-7xl font-bold tracking-tight mb-6',
                                        isDark ? 'text-white' : 'text-slate-900'
                                    )}
                                >
                                    <span className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent">
                                        SyncCanvas
                                    </span>
                                </motion.h1>

                                {/* 副标题 */}
                                <motion.p
                                    initial={{ y: 20, opacity: 0 }}
                                    animate={{ y: 0, opacity: 1 }}
                                    transition={{ delay: 0.3, duration: 0.6 }}
                                    className={cn(
                                        'text-lg sm:text-xl max-w-2xl mx-auto mb-10',
                                        isDark ? 'text-slate-400' : 'text-slate-600'
                                    )}
                                >
                                    下一代实时协作白板平台，支持 AI 智能绘图与 Git 风格版本控制
                                </motion.p>

                                {/* CTA 按钮 */}
                                <motion.div
                                    initial={{ y: 20, opacity: 0 }}
                                    animate={{ y: 0, opacity: 1 }}
                                    transition={{ delay: 0.4, duration: 0.6 }}
                                    className="flex flex-col sm:flex-row gap-4 justify-center items-center"
                                >
                                    <button
                                        onClick={handleGetStarted}
                                        className={cn(
                                            'group flex items-center gap-2 px-8 py-4 rounded-2xl',
                                            'bg-gradient-to-r from-blue-600 to-indigo-600',
                                            'text-white font-semibold text-lg',
                                            'shadow-xl shadow-blue-500/30',
                                            'hover:shadow-2xl hover:shadow-blue-500/40',
                                            'hover:scale-[1.02] active:scale-[0.98]',
                                            'transition-all duration-200'
                                        )}
                                    >
                                        开始使用
                                        <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
                                    </button>

                                    <button
                                        onClick={handleQuickStart}
                                        className={cn(
                                            'flex items-center gap-2 px-8 py-4 rounded-2xl',
                                            'font-semibold text-lg',
                                            'border-2 transition-all duration-200',
                                            'hover:scale-[1.02] active:scale-[0.98]',
                                            isDark
                                                ? 'border-slate-700 text-slate-300 hover:bg-slate-800/50'
                                                : 'border-slate-200 text-slate-700 hover:bg-slate-50'
                                        )}
                                    >
                                        <Zap size={20} />
                                        快速体验
                                    </button>
                                </motion.div>
                            </>
                        )}
                    </AnimatePresence>
                </div>

                {/* Features Section */}
                <motion.div
                    initial={{ y: 40, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.6, duration: 0.8 }}
                    className="pb-20 sm:pb-32"
                >
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                        {features.map((feature, index) => (
                            <motion.div
                                key={feature.title}
                                initial={{ y: 20, opacity: 0 }}
                                animate={{ y: 0, opacity: 1 }}
                                transition={{ delay: 0.7 + index * 0.1, duration: 0.5 }}
                                className={cn(
                                    'group p-6 rounded-3xl transition-all duration-300',
                                    'border backdrop-blur-sm',
                                    isDark
                                        ? 'bg-slate-900/50 border-slate-800 hover:border-slate-700 hover:bg-slate-800/50'
                                        : 'bg-white/50 border-slate-200 hover:border-slate-300 hover:bg-white/80 shadow-sm hover:shadow-md'
                                )}
                            >
                                <div className={cn(
                                    'w-12 h-12 rounded-2xl flex items-center justify-center mb-4',
                                    'bg-gradient-to-br',
                                    feature.gradient,
                                    'text-white shadow-lg group-hover:scale-110 transition-transform duration-300'
                                )}>
                                    <feature.icon size={24} />
                                </div>
                                <h3 className={cn(
                                    'text-lg font-semibold mb-2',
                                    isDark ? 'text-white' : 'text-slate-900'
                                )}>
                                    {feature.title}
                                </h3>
                                <p className={cn(
                                    'text-sm',
                                    isDark ? 'text-slate-400' : 'text-slate-600'
                                )}>
                                    {feature.description}
                                </p>
                            </motion.div>
                        ))}
                    </div>
                </motion.div>

                {/* 底部装饰 */}
                <div className={cn(
                    'text-center pb-8 text-sm',
                    isDark ? 'text-slate-600' : 'text-slate-400'
                )}>
                    <p>基于 Excalidraw + Yjs 构建</p>
                </div>
            </div>
        </div>
    );
};
