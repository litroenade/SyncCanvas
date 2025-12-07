import React, { useEffect, useState, useRef } from 'react';
import { useCanvasStore } from '../stores/useCanvasStore';

/**
 * 自定义画笔光标
 * 
 * 当选择画笔或橡皮擦工具时，显示一个跟随鼠标的圆圈，
 * 圆圈大小对应笔触大小，颜色对应笔触颜色。
 */
export const BrushCursor: React.FC = () => {
    const {
        currentTool,
        currentStrokeWidth,
        currentStrokeColor,
        scale
    } = useCanvasStore();

    const [isVisible, setIsVisible] = useState(false);
    const cursorRef = useRef<HTMLDivElement>(null);

    // 仅在画笔和橡皮擦模式下启用
    const isBrushTool = currentTool === 'freedraw' || currentTool === 'eraser';

    useEffect(() => {
        if (!isBrushTool) {
            setIsVisible(false);
            return;
        }

        // Show cursor immediately when tool is active
        setIsVisible(true);

        const handleMouseMove = (e: MouseEvent) => {
            // Update position
            if (cursorRef.current) {
                cursorRef.current.style.transform = `translate(${e.clientX}px, ${e.clientY}px)`;
            }

            // Optional: Hide if hovering over UI elements like sidebar/toolbar which have high z-index and pointer-events
            // But simple logic is often better: just show it if tool is active.
            // The system cursor is hidden by Canvas.tsx style.
            
            // If we are over the UI (Toolbar/Sidebar), we might want to see the system cursor.
            // Canvas.tsx sets cursor: 'none' on the wrapper div.
            // Areas outside wrapper (if any) or fixed elements on top (Toolbar) might show system cursor.
            // Let's rely on CSS mostly.
        };

        const handleMouseLeave = () => {
            setIsVisible(false);
        };
        
        const handleMouseEnter = () => {
            setIsVisible(true);
        };

        window.addEventListener('mousemove', handleMouseMove);
        document.body.addEventListener('mouseleave', handleMouseLeave);
        document.body.addEventListener('mouseenter', handleMouseEnter);

        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            document.body.removeEventListener('mouseleave', handleMouseLeave);
            document.body.removeEventListener('mouseenter', handleMouseEnter);
        };
    }, [isBrushTool]);

    if (!isBrushTool) return null;

    // 计算光标大小 (像素)
    // 橡皮擦默认稍大一点
    let size = (currentStrokeWidth || 2) * scale;
    if (currentTool === 'eraser') {
        size = Math.max(20 * scale, size);
    }
    // 限制最小/最大尺寸，避免太小看不见或太大遮挡
    size = Math.max(10, Math.min(size, 200));

    const color = currentTool === 'eraser' ? '#ffffff' : (currentStrokeColor || '#000000');
    const borderColor = currentTool === 'eraser' ? '#000000' : '#ffffff';

    return (
        <div
            ref={cursorRef}
            className="fixed top-0 left-0 pointer-events-none z-[9999] rounded-full border shadow-sm will-change-transform"
            style={{
                width: size,
                height: size,
                backgroundColor: currentTool === 'eraser' ? 'rgba(255, 255, 255, 0.5)' : color,
                borderColor: borderColor,
                borderWidth: '1px',
                borderStyle: 'solid',
                opacity: isVisible ? 0.8 : 0,
                // 使用 margin 负值使光标居中于鼠标点 (或者在 transform 中处理，这里用 translate(-50%, -50%))
                marginTop: -size / 2,
                marginLeft: -size / 2,
                transition: 'width 0.1s, height 0.1s, opacity 0.1s', // 平滑大小变化，但位置变化不加 transition 以免延迟
            }}
        />
    );
};
