import React from 'react';
import { Group, Line } from 'react-konva';
import { useCanvasStore } from '../stores/useCanvasStore';

/**
 * 网格背景组件
 * 
 * 根据当前的缩放和偏移量绘制无限网格背景。
 */
export const Grid: React.FC = () => {
    const { scale, offset, showGrid } = useCanvasStore();

    if (!showGrid) return null;

    // 计算可见区域
    const stageWidth = window.innerWidth;
    const stageHeight = window.innerHeight;

    const startX = -offset.x / scale;
    const startY = -offset.y / scale;
    const endX = (stageWidth - offset.x) / scale;
    const endY = (stageHeight - offset.y) / scale;

    const gridSize = 50;
    const lines = [];

    // 绘制垂直线
    const firstX = Math.floor(startX / gridSize) * gridSize;
    for (let x = firstX; x < endX; x += gridSize) {
        lines.push(
            <Line
                key={`v${x}`}
                points={[x, startY, x, endY]}
                stroke="#ddd"
                strokeWidth={1 / scale}
            />
        );
    }

    // 绘制水平线
    const firstY = Math.floor(startY / gridSize) * gridSize;
    for (let y = firstY; y < endY; y += gridSize) {
        lines.push(
            <Line
                key={`h${y}`}
                points={[startX, y, endX, y]}
                stroke="#ddd"
                strokeWidth={1 / scale}
            />
        );
    }

    return <Group>{lines}</Group>;
};

