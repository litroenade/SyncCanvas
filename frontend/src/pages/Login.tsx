import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { config } from '../config/env';
import { useThemeStore } from '../stores/useThemeStore';
import { cn } from '../lib/utils';
import { Sun, Moon, User, Users } from 'lucide-react';
import { useCanvasStore } from '../stores/useCanvasStore';

export const Login: React.FC = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();
    const { theme, toggleTheme } = useThemeStore();
    const { setIsGuest } = useCanvasStore();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        const endpoint = '/auth/token';
        const body = new URLSearchParams({ username, password });

        try {
            const response = await fetch(`${config.apiBaseUrl}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: body,
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Authentication failed');
            }

            const data = await response.json();
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('username', username);
            localStorage.removeItem('isGuest');
            setIsGuest(false);
            navigate('/');
        } catch (err: any) {
            setError(err.message);
        }
    };

    const handleGuestLogin = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        localStorage.setItem('isGuest', 'true');
        setIsGuest(true);
        navigate('/');
    };

    return (
        <div className={cn(
            "min-h-screen flex items-center justify-center transition-all duration-500 relative overflow-hidden",
            theme === 'dark'
                ? "bg-slate-900"
                : "bg-gray-50"
        )}>
            {/* Background Gradients */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className={cn(
                    "absolute -top-[20%] -left-[10%] w-[70%] h-[70%] rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob",
                    theme === 'dark' ? "bg-purple-900" : "bg-purple-300"
                )}></div>
                <div className={cn(
                    "absolute top-[20%] -right-[10%] w-[70%] h-[70%] rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000",
                    theme === 'dark' ? "bg-indigo-900" : "bg-indigo-300"
                )}></div>
                <div className={cn(
                    "absolute -bottom-[20%] left-[20%] w-[70%] h-[70%] rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-4000",
                    theme === 'dark' ? "bg-blue-900" : "bg-blue-300"
                )}></div>
            </div>

            <button
                onClick={toggleTheme}
                className={cn(
                    "absolute top-6 right-6 p-3 rounded-full transition-all duration-300 z-10 backdrop-blur-md border",
                    theme === 'dark'
                        ? "bg-slate-800/50 text-slate-300 border-slate-700 hover:bg-slate-700/50"
                        : "bg-white/50 text-slate-600 border-white/50 hover:bg-white/80 shadow-sm"
                )}
            >
                {theme === 'dark' ? <Moon size={20} /> : <Sun size={20} />}
            </button>

            <div className={cn(
                "relative p-8 md:p-10 rounded-3xl w-full max-w-md transition-all duration-300 backdrop-blur-xl border shadow-2xl mx-4",
                theme === 'dark'
                    ? "bg-slate-800/40 border-slate-700/50 text-slate-100 shadow-black/20"
                    : "bg-white/70 border-white/50 text-slate-800 shadow-xl"
            )}>
                <div className="text-center mb-8">
                    <div className={cn(
                        "w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center text-3xl font-bold shadow-lg transform rotate-3",
                        "bg-gradient-to-br from-blue-500 to-indigo-600 text-white"
                    )}>
                        S
                    </div>
                    <h2 className={cn("text-3xl font-bold mb-2 tracking-tight", theme === 'dark' ? "text-white" : "text-slate-900")}>
                        SyncCanvas
                    </h2>
                    <p className={cn("text-sm", theme === 'dark' ? "text-slate-400" : "text-slate-500")}>
                        实时协作白板系统
                    </p>
                </div>

                {error && (
                    <div className="bg-red-500/10 text-red-500 p-4 rounded-xl mb-6 text-sm border border-red-500/20 flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-5">
                    <div className="space-y-1.5">
                        <label className={cn("block text-xs font-semibold uppercase tracking-wider ml-1", theme === 'dark' ? "text-slate-400" : "text-slate-500")}>用户名 (可随意填写)</label>
                        <div className="relative">
                            <User className={cn("absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 transition-colors", theme === 'dark' ? "text-slate-500" : "text-slate-400")} />
                            <input
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                className={cn(
                                    "w-full pl-10 pr-4 py-3 rounded-xl border outline-none transition-all duration-200",
                                    theme === 'dark'
                                        ? "bg-slate-900/50 border-slate-700 text-slate-100 focus:border-blue-500 focus:bg-slate-900/80 placeholder:text-slate-600"
                                        : "bg-white/50 border-slate-200 text-slate-900 focus:border-blue-500 focus:bg-white placeholder:text-slate-400"
                                )}
                                placeholder="输入您的昵称"
                                required
                            />
                        </div>
                    </div>
                    <div className="space-y-1.5">
                        <label className={cn("block text-xs font-semibold uppercase tracking-wider ml-1", theme === 'dark' ? "text-slate-400" : "text-slate-500")}>访问密钥</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className={cn(
                                "w-full px-4 py-3 rounded-xl border outline-none transition-all duration-200",
                                theme === 'dark'
                                    ? "bg-slate-900/50 border-slate-700 text-slate-100 focus:border-blue-500 focus:bg-slate-900/80 placeholder:text-slate-600"
                                    : "bg-white/50 border-slate-200 text-slate-900 focus:border-blue-500 focus:bg-white placeholder:text-slate-400"
                            )}
                            placeholder="输入服务端密钥 (data/settings.json)"
                            required
                        />
                    </div>
                    <button
                        type="submit"
                        className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3.5 rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 font-semibold shadow-lg shadow-blue-500/25 active:scale-[0.98]"
                    >
                        登录
                    </button>
                </form>

                <div className="relative my-8">
                    <div className="absolute inset-0 flex items-center">
                        <div className={cn("w-full border-t", theme === 'dark' ? "border-slate-700" : "border-slate-200")}></div>
                    </div>
                    <div className="relative flex justify-center text-sm">
                        <span className={cn("px-4 text-xs uppercase tracking-wider font-medium", theme === 'dark' ? "bg-slate-800 text-slate-500" : "bg-white text-slate-400")}>或者</span>
                    </div>
                </div>

                <button
                    onClick={handleGuestLogin}
                    className={cn(
                        "w-full flex items-center justify-center gap-2 py-3.5 rounded-xl border transition-all duration-200 font-medium active:scale-[0.98]",
                        theme === 'dark'
                            ? "border-slate-700 hover:bg-slate-700/50 text-slate-300"
                            : "border-slate-200 hover:bg-slate-50 text-slate-600"
                    )}
                >
                    <Users size={18} />
                    游客访问 (仅浏览)
                </button>
            </div>
        </div>
    );
};
