import React, { useMemo } from 'react';
import { Group, Line } from 'react-konva';
import { useCanvasStore } from '../stores/useCanvasStore';

/**
 * 根据缩放级别计算合适的网格间距
 * 
 * 缩放越大，网格间距越小（显示更细的网格）
 * 缩放越小，网格间距越大（显示更粗的网格）
 */
const getAdaptiveGridSize = (scale: number): { major: number; minor: number } => {
    // 基础网格间距：20px
    const baseSize = 20;

    // 根据缩放计算阶段
    // scale < 0.3: 使用 200px 网格
    // scale < 0.5: 使用 100px 网格
    // scale < 1.0: 使用 50px 网格
    // scale < 2.0: 使用 25px 网格
    // scale >= 2.0: 使用 10px 网格
    let gridSize: number;
    if (scale < 0.3) {
        gridSize = baseSize * 10; // 200px
    } else if (scale < 0.5) {
        gridSize = baseSize * 5;  // 100px
    } else if (scale < 1.0) {
        gridSize = baseSize * 2.5; // 50px
    } else if (scale < 2.0) {
        gridSize = baseSize;      // 20px
    } else {
        gridSize = baseSize / 2;  // 10px
    }

    return {
        major: gridSize * 5, // 主网格：每5个小格一条
        minor: gridSize,     // 次网格
    };
};

/**
 * 网格背景组件
 * 
 * 根据当前的缩放和偏移量绘制自适应网格背景。
 */
export const Grid: React.FC = () => {
    const { scale, offset, showGrid } = useCanvasStore();

    const lines = useMemo(() => {
        if (!showGrid) return [];

        // 计算可见区域
        const stageWidth = window.innerWidth;
        const stageHeight = window.innerHeight;

        const startX = -offset.x / scale;
        const startY = -offset.y / scale;
        const endX = (stageWidth - offset.x) / scale;
        const endY = (stageHeight - offset.y) / scale;

        // 获取自适应网格间距
        const { major, minor } = getAdaptiveGridSize(scale);
        const result: JSX.Element[] = [];

        // 绘制次网格（细线）
        const firstMinorX = Math.floor(startX / minor) * minor;
        for (let x = firstMinorX; x < endX; x += minor) {
            // 跳过主网格位置
            if (Math.abs(x % major) < 0.1) continue;
            result.push(
                <Line
                    key={`vm${x}`}
                    points={[x, startY, x, endY]}
                    stroke="#e5e7eb"
                    strokeWidth={1 / scale}
                />
            );
        }

        const firstMinorY = Math.floor(startY / minor) * minor;
        for (let y = firstMinorY; y < endY; y += minor) {
            if (Math.abs(y % major) < 0.1) continue;
            result.push(
                <Line
                    key={`hm${y}`}
                    points={[startX, y, endX, y]}
                    stroke="#e5e7eb"
                    strokeWidth={1 / scale}
                />
            );
        }

        // 绘制主网格（粗线）
        const firstMajorX = Math.floor(startX / major) * major;
        for (let x = firstMajorX; x < endX; x += major) {
            result.push(
                <Line
                    key={`vM${x}`}
                    points={[x, startY, x, endY]}
                    stroke="#d1d5db"
                    strokeWidth={1.5 / scale}
                />
            );
        }

        const firstMajorY = Math.floor(startY / major) * major;
        for (let y = firstMajorY; y < endY; y += major) {
            result.push(
                <Line
                    key={`hM${y}`}
                    points={[startX, y, endX, y]}
                    stroke="#d1d5db"
                    strokeWidth={1.5 / scale}
                />
            );
        }

        return result;
    }, [scale, offset, showGrid]);

    if (!showGrid) return null;

    return <Group>{lines}</Group>;
};

