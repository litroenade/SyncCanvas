import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import { config } from '../config/env';
import { useThemeStore } from '../stores/useThemeStore';
import { cn } from '../lib/utils';
import { Sun, Moon, User, Users } from 'lucide-react';

const BASE_ROTATION_X = -8;
const BASE_ROTATION_Y = 10;
const INTERACTIVE_SELECTOR = 'button, input, textarea, select, a, label, [data-no-card-drag="true"]';

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

export const Login: React.FC = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isCardHovered, setIsCardHovered] = useState(false);
    const [isDraggingCard, setIsDraggingCard] = useState(false);
    const [isFormFocused, setIsFormFocused] = useState(false);
    const [hasManualRotation, setHasManualRotation] = useState(false);
    const [cardRotation, setCardRotation] = useState({ x: BASE_ROTATION_X, y: BASE_ROTATION_Y });
    const navigate = useNavigate();
    const { theme, toggleTheme } = useThemeStore();
    const prefersReducedMotion = useReducedMotion();
    const formRef = useRef<HTMLFormElement>(null);
    const cardRef = useRef<HTMLDivElement>(null);
    const pointerRef = useRef({ x: 0, y: 0 });
    const manualRotationRef = useRef(false);
    const hoveredRef = useRef(false);
    const formFocusedRef = useRef(false);
    const dragStateRef = useRef({
        active: false,
        startX: 0,
        startY: 0,
        startRotateX: BASE_ROTATION_X,
        startRotateY: BASE_ROTATION_Y,
    });

    const setRotationTarget = (nextX: number, nextY: number) => {
        if (prefersReducedMotion) {
            setCardRotation({ x: 0, y: 0 });
            return;
        }

        setCardRotation({ x: nextX, y: nextY });
    };

    const setManualRotationState = (next: boolean) => {
        manualRotationRef.current = next;
        setHasManualRotation(next);
    };

    const setHoveredState = (next: boolean) => {
        hoveredRef.current = next;
        setIsCardHovered(next);
    };

    const setFormFocusedState = (next: boolean) => {
        formFocusedRef.current = next;
        setIsFormFocused(next);
    };

    const updateRotationFromPointer = (clientX: number, clientY: number, cardElement?: HTMLDivElement | null) => {
        pointerRef.current = { x: clientX, y: clientY };

        if (prefersReducedMotion || dragStateRef.current.active || formFocusedRef.current || manualRotationRef.current) {
            return;
        }

        const activeCard = cardElement ?? cardRef.current;
        if (!activeCard) {
            return;
        }

        const rect = activeCard.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const normalizedX = clamp((clientX - centerX) / (rect.width / 2), -1.35, 1.35);
        const normalizedY = clamp((clientY - centerY) / (rect.height / 2), -1.35, 1.35);
        const easedX = Math.sign(normalizedX) * Math.pow(Math.abs(normalizedX), 0.88);
        const easedY = Math.sign(normalizedY) * Math.pow(Math.abs(normalizedY), 0.88);
        const rotationX = clamp(-easedY * 18, -18, 18);
        const rotationY = clamp(easedX * 22, -22, 22);

        setRotationTarget(rotationX, rotationY);
    };

    useEffect(() => {
        if (typeof window === 'undefined') {
            return;
        }

        pointerRef.current = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
        setRotationTarget(prefersReducedMotion ? 0 : BASE_ROTATION_X, prefersReducedMotion ? 0 : BASE_ROTATION_Y);

        const handlePointerMove = (event: PointerEvent) => {
            if (!hoveredRef.current) {
                updateRotationFromPointer(event.clientX, event.clientY);
            }
        };

        window.addEventListener('pointermove', handlePointerMove);
        return () => {
            window.removeEventListener('pointermove', handlePointerMove);
            document.body.style.userSelect = '';
            document.body.style.cursor = '';
        };
    }, [prefersReducedMotion]);

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
                body,
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Authentication failed');
            }

            const data = await response.json();
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('username', username);
            localStorage.removeItem('isGuest');
            navigate('/rooms');
        } catch (err: any) {
            setError(err.message);
        }
    };

    const handleGuestLogin = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        localStorage.setItem('isGuest', 'true');
        navigate('/rooms');
    };

    const handleCardPointerEnter = (event: React.PointerEvent<HTMLDivElement>) => {
        setHoveredState(true);
        if (!dragStateRef.current.active && !formFocusedRef.current && !manualRotationRef.current) {
            updateRotationFromPointer(event.clientX, event.clientY, event.currentTarget);
        }
    };

    const handleCardPointerLeave = (event: React.PointerEvent<HTMLDivElement>) => {
        setHoveredState(false);
        if (!dragStateRef.current.active && !formFocusedRef.current && !manualRotationRef.current) {
            updateRotationFromPointer(event.clientX, event.clientY, event.currentTarget);
        }
    };

    const handleCardPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
        if (prefersReducedMotion) {
            return;
        }

        const target = event.target as HTMLElement;
        if (target.closest(INTERACTIVE_SELECTOR)) {
            return;
        }

        dragStateRef.current = {
            active: true,
            startX: event.clientX,
            startY: event.clientY,
            startRotateX: cardRotation.x,
            startRotateY: cardRotation.y,
        };

        document.body.style.userSelect = 'none';
        document.body.style.cursor = 'grabbing';
        setManualRotationState(true);
        setIsDraggingCard(true);
        event.currentTarget.setPointerCapture(event.pointerId);
    };

    const handleCardPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
        if (prefersReducedMotion) {
            return;
        }

        if (!dragStateRef.current.active) {
            if (hoveredRef.current && !formFocusedRef.current && !manualRotationRef.current) {
                updateRotationFromPointer(event.clientX, event.clientY, event.currentTarget);
            }
            return;
        }

        const deltaX = event.clientX - dragStateRef.current.startX;
        const deltaY = event.clientY - dragStateRef.current.startY;

        setRotationTarget(
            dragStateRef.current.startRotateX - deltaY * 0.42,
            dragStateRef.current.startRotateY + deltaX * 0.42
        );
    };

    const finishCardDrag = (event?: React.PointerEvent<HTMLDivElement>) => {
        if (!dragStateRef.current.active) {
            return;
        }

        dragStateRef.current.active = false;
        document.body.style.userSelect = '';
        document.body.style.cursor = '';
        setIsDraggingCard(false);
        if (event && event.currentTarget.hasPointerCapture(event.pointerId)) {
            event.currentTarget.releasePointerCapture(event.pointerId);
        }
    };

    const handleCardDoubleClick = () => {
        setManualRotationState(false);
        setRotationTarget(0, 0);
    };

    const handleFormFocusCapture = () => {
        setFormFocusedState(true);
    };

    const handleFormBlurCapture = () => {
        window.requestAnimationFrame(() => {
            const stillFocused = formRef.current?.contains(document.activeElement) ?? false;
            setFormFocusedState(stillFocused);

            if (stillFocused || manualRotationRef.current) {
                return;
            }

            if (cardRef.current) {
                updateRotationFromPointer(pointerRef.current.x, pointerRef.current.y, cardRef.current);
            }
        });
    };

    const autoAxisX = cardRotation.x / 18;
    const autoAxisY = cardRotation.y / 22;
    const autoAngle = Math.hypot(cardRotation.x, cardRotation.y);
    const cardTransform = hasManualRotation || isDraggingCard
        ? `rotateX(${cardRotation.x}deg) rotateY(${cardRotation.y}deg)`
        : `rotate3d(${autoAxisX}, ${autoAxisY}, 0, ${autoAngle}deg)`;

    return (
        <div className={cn(
            'min-h-screen flex items-center justify-center transition-all duration-500 relative overflow-hidden',
            theme === 'dark'
                ? 'bg-slate-900'
                : 'bg-gray-50'
        )}>
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <motion.div
                    animate={{
                        scale: [1, 1.2, 1],
                        x: [0, 50, 0],
                        y: [0, 30, 0],
                    }}
                    transition={{
                        duration: 20,
                        repeat: Infinity,
                        ease: 'easeInOut'
                    }}
                    className={cn(
                        'absolute -top-[20%] -left-[10%] w-[70%] h-[70%] rounded-full mix-blend-multiply filter blur-[100px] opacity-20',
                        theme === 'dark' ? 'bg-purple-900' : 'bg-purple-300'
                    )}
                />
                <motion.div
                    animate={{
                        scale: [1, 1.1, 1],
                        x: [0, -30, 0],
                        y: [0, 50, 0],
                    }}
                    transition={{
                        duration: 15,
                        repeat: Infinity,
                        ease: 'easeInOut',
                        delay: 2
                    }}
                    className={cn(
                        'absolute top-[20%] -right-[10%] w-[70%] h-[70%] rounded-full mix-blend-multiply filter blur-[100px] opacity-20',
                        theme === 'dark' ? 'bg-indigo-900' : 'bg-indigo-300'
                    )}
                />
                <motion.div
                    animate={{
                        scale: [1, 1.3, 1],
                        x: [0, 40, 0],
                        y: [0, -40, 0],
                    }}
                    transition={{
                        duration: 18,
                        repeat: Infinity,
                        ease: 'easeInOut',
                        delay: 4
                    }}
                    className={cn(
                        'absolute -bottom-[20%] left-[20%] w-[70%] h-[70%] rounded-full mix-blend-multiply filter blur-[100px] opacity-20',
                        theme === 'dark' ? 'bg-blue-900' : 'bg-blue-300'
                    )}
                />
            </div>

            <button
                onClick={toggleTheme}
                className={cn(
                    'absolute top-6 right-6 p-3 rounded-full transition-all duration-300 z-10 backdrop-blur-md border',
                    theme === 'dark'
                        ? 'bg-slate-800/50 text-slate-300 border-slate-700 hover:bg-slate-700/50'
                        : 'bg-white/50 text-slate-600 border-white/50 hover:bg-white/80 shadow-sm'
                )}
            >
                {theme === 'dark' ? <Moon size={20} /> : <Sun size={20} />}
            </button>

            <div className="relative mx-4 w-full max-w-md [perspective:1800px]">
                <motion.div
                    initial={{ opacity: 0, y: 20, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: isDraggingCard ? 1.01 : 1 }}
                    transition={{ duration: 0.42, delay: 0.18, ease: [0.22, 1, 0.36, 1] }}
                >
                    <div
                        ref={cardRef}
                        onPointerEnter={handleCardPointerEnter}
                        onPointerLeave={handleCardPointerLeave}
                        onPointerDown={handleCardPointerDown}
                        onPointerMove={handleCardPointerMove}
                        onPointerUp={finishCardDrag}
                        onPointerCancel={finishCardDrag}
                        onDoubleClick={handleCardDoubleClick}
                        style={{
                            transformStyle: 'preserve-3d',
                            transform: cardTransform,
                            transition: isDraggingCard ? 'none' : 'transform 220ms ease',
                        }}
                        className={cn(
                            'relative p-8 md:p-10 rounded-3xl w-full backdrop-blur-xl border shadow-2xl',
                            !prefersReducedMotion && !isDraggingCard && 'cursor-grab',
                            isDraggingCard && 'cursor-grabbing',
                            theme === 'dark'
                                ? 'bg-slate-800/40 border-slate-700/50 text-slate-100 shadow-black/20'
                                : 'bg-white/70 border-white/50 text-slate-800 shadow-xl'
                        )}
                    >
                        <div
                            aria-hidden="true"
                            className={cn(
                                'pointer-events-none absolute inset-0 rounded-3xl border',
                                theme === 'dark' ? 'border-slate-700/20 bg-slate-900/10' : 'border-white/30 bg-white/12'
                            )}
                            style={{ transform: 'translateZ(-20px) scale(0.985)' }}
                        />

                        <div className="relative select-none" style={{ transform: 'translateZ(26px)' }}>
                            <div className="text-center mb-8" style={{ transform: 'translateZ(34px)' }}>
                                <div className={cn(
                                    'w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center text-3xl font-bold shadow-lg',
                                    'bg-gradient-to-br from-blue-500 to-indigo-600 text-white'
                                )}>
                                    S
                                </div>
                                <h2 className={cn('text-3xl font-bold mb-2 tracking-tight', theme === 'dark' ? 'text-white' : 'text-slate-900')}>
                                    SyncCanvas
                                </h2>
                                <p className={cn('text-sm', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
                                    实时协作白板系统
                                </p>
                            </div>

                            {error && (
                                <div className="bg-red-500/10 text-red-500 p-4 rounded-xl mb-6 text-sm border border-red-500/20 flex items-center gap-2 animate-in fade-in slide-in-from-top-2" style={{ transform: 'translateZ(28px)' }}>
                                    <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                                    {error}
                                </div>
                            )}

                            <form
                                ref={formRef}
                                onSubmit={handleSubmit}
                                onFocusCapture={handleFormFocusCapture}
                                onBlurCapture={handleFormBlurCapture}
                                className="space-y-5"
                                style={{ transform: 'translateZ(42px)' }}
                            >
                                <div className="space-y-1.5">
                                    <label className={cn('block text-xs font-semibold uppercase tracking-wider ml-1', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
                                        用户名称（可随意填写）
                                    </label>
                                    <div className="relative">
                                        <User className={cn('absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 transition-colors', theme === 'dark' ? 'text-slate-500' : 'text-slate-400')} />
                                        <input
                                            type="text"
                                            value={username}
                                            onChange={(event) => setUsername(event.target.value)}
                                            className={cn(
                                                'w-full select-text pl-10 pr-4 py-3 rounded-xl border outline-none transition-all duration-200',
                                                theme === 'dark'
                                                    ? 'bg-slate-900/50 border-slate-700 text-slate-100 focus:border-blue-500 focus:bg-slate-900/80 placeholder:text-slate-600'
                                                    : 'bg-white/50 border-slate-200 text-slate-900 focus:border-blue-500 focus:bg-white placeholder:text-slate-400'
                                            )}
                                            placeholder="输入您的昵称"
                                            required
                                        />
                                    </div>
                                </div>
                                <div className="space-y-1.5">
                                    <label className={cn('block text-xs font-semibold uppercase tracking-wider ml-1', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
                                        访问密钥
                                    </label>
                                    <input
                                        type="password"
                                        value={password}
                                        onChange={(event) => setPassword(event.target.value)}
                                        className={cn(
                                            'w-full select-text px-4 py-3 rounded-xl border outline-none transition-all duration-200',
                                            theme === 'dark'
                                                ? 'bg-slate-900/50 border-slate-700 text-slate-100 focus:border-blue-500 focus:bg-slate-900/80 focus:ring-2 focus:ring-blue-500/20 placeholder:text-slate-600'
                                                : 'bg-white/50 border-slate-200 text-slate-900 focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-500/20 placeholder:text-slate-400'
                                        )}
                                        placeholder="输入服务器密钥"
                                        required
                                    />
                                </div>
                                <motion.button
                                    whileHover={{ scale: 1.02, boxShadow: '0 10px 20px -10px rgba(59, 130, 246, 0.5)' }}
                                    whileTap={{ scale: 0.98 }}
                                    type="submit"
                                    className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3.5 rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 font-semibold shadow-lg shadow-blue-500/25"
                                >
                                    登录
                                </motion.button>
                            </form>

                            <div className="relative my-8" style={{ transform: 'translateZ(30px)' }}>
                                <div className="absolute inset-0 flex items-center">
                                    <div className={cn('w-full border-t', theme === 'dark' ? 'border-slate-700' : 'border-slate-200')} />
                                </div>
                                <div className="relative flex justify-center text-sm">
                                    <span className={cn('px-4 text-xs uppercase tracking-wider font-medium', theme === 'dark' ? 'bg-slate-800 text-slate-500' : 'bg-white text-slate-400')}>
                                        或者
                                    </span>
                                </div>
                            </div>

                            <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={handleGuestLogin}
                                className={cn(
                                    'w-full flex items-center justify-center gap-2 py-3.5 rounded-xl border transition-all duration-200 font-medium',
                                    theme === 'dark'
                                        ? 'border-slate-700 hover:bg-slate-700/50 text-slate-300'
                                        : 'border-slate-200 hover:bg-slate-50 text-slate-600'
                                )}
                                style={{ transform: 'translateZ(44px)' }}
                            >
                                <Users size={18} />
                                游客访问（仅浏览）
                            </motion.button>
                        </div>
                    </div>
                </motion.div>
            </div>
        </div>
    );
};
