import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useThemeStore } from '../../stores/useThemeStore';

export const ThemeWaveTransition: React.FC = () => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const { theme, isTransitioning, realToggleTheme, endTransition } = useThemeStore();
    const [isActive, setIsActive] = useState(false);
    
    // 颜色配置 - 使用 HSL 以匹配 index.css
    const COLORS = {
        light: '#f9fafb', // gray-50 (used in Rooms) / blue-50 (eff6ff in Login) -> Average or standard?
                          // Let's use gray-50 (#f9fafb) or Slate-50?
                          // Login uses bg-blue-50 (#eff6ff). Rooms uses bg-gray-50 (#f9fafb).
                          // This inconsistency is hard to mask perfectly.
                          // I'll stick to a neutral white/off-white. #f9fafb is safer.
        dark: '#0f172a'   // Slate-900 (Used in both Login and Rooms)
    };

    // 1. 监听 store 的过渡状态，激活组件渲染
    useEffect(() => {
        if (isTransitioning) {
            setIsActive(true);
        }
    }, [isTransitioning]);

    // 2. 组件激活渲染后，执行动画逻辑
    useLayoutEffect(() => {
        if (!isActive) return;

        // 在 isActive 变为 true 的那次渲染中，React 已经挂载了 canvasRef
        const canvas = canvasRef.current;
        if (!canvas) {
            console.error('Canvas ref not found, ending transition immediately');
            endTransition();
            setIsActive(false);
            return;
        }

        const ctx = canvas.getContext('2d');
        if (!ctx) {
            console.error('Canvas context not available, ending transition immediately');
            endTransition();
            setIsActive(false);
            return;
        }

        // 设置画布尺寸
        const updateSize = () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        };
        updateSize();
        
        // 确定源颜色和目标颜色
        const isToDark = theme === 'light'; 
        const startColor = isToDark ? COLORS.light : COLORS.dark;
        const endColor = isToDark ? COLORS.dark : COLORS.light;

        let startTime: number | null = null;
        const DURATION = 1000; // 1秒

        // 保存原始背景，以便恢复
        const originalBodyBg = document.body.style.backgroundColor;
        const originalDocBg = document.documentElement.style.backgroundColor;
        
        // 1. 预绘制第一帧
        ctx.fillStyle = startColor;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // 2. 添加全局 class，配合 index.css 将页面级容器背景设为透明
        document.body.classList.add('theme-transitioning');

        // 3. 立即切换 DOM 主题
        realToggleTheme();

        const animate = (timestamp: number) => {
            if (!startTime) startTime = timestamp;
            const elapsed = timestamp - startTime;
            const progress = Math.min(elapsed / DURATION, 1);

            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // 绘制底色 background
            ctx.fillStyle = startColor;
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // 绘制波浪
            ctx.fillStyle = endColor;
            
            const w = canvas.width;
            const h = canvas.height;
            const maxRadius = Math.sqrt(w*w + h*h) * 1.5;
            
            const ease = (t: number) => t < .5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
            const easedProgress = ease(progress);
            
            const currentRadius = easedProgress * maxRadius;

            ctx.beginPath();
            ctx.moveTo(0, 0); 

            for (let a = -0.1; a <= Math.PI / 2 + 0.1; a += 0.05) {
                let r = currentRadius;
                if (r > 0) {
                    const amp = 40 + 20 * Math.sin(progress * 10);
                    const freq = 12; 
                    const wave = amp * Math.sin(a * freq - progress * 15);
                    r += wave;
                }
                const x = r * Math.cos(a);
                const y = r * Math.sin(a);
                ctx.lineTo(x, y);
            }

            ctx.lineTo(0, 0); 
            ctx.fill();

            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                // 动画结束 - 清理
                document.body.classList.remove('theme-transitioning');
                
                endTransition();
                setIsActive(false);
            }
        };

        const animationId = requestAnimationFrame(animate);
        window.addEventListener('resize', updateSize);
        
        return () => {
            window.removeEventListener('resize', updateSize);
            cancelAnimationFrame(animationId);
            document.body.classList.remove('theme-transitioning');
        };
    }, [isActive]); 

    if (!isActive) return null;

    return (
        <canvas
            ref={canvasRef}
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                pointerEvents: 'none', 
                zIndex: -1 
            }}
        />
    );
};
