import React from 'react';
import { useCanvasStore, Shape } from '../stores/useCanvasStore';
import { yjsManager } from '../lib/yjs';
import { cn } from '../lib/utils';
import { useThemeStore } from '../stores/useThemeStore';

// 直接使用 yjsManager 的操作
const updateShape = (id: string, attrs: Partial<Shape>) => {
    const shapesMap = yjsManager.shapesMap;
    if (!shapesMap) {
        console.warn('Yjs 未连接，无法更新图形');
        return;
    }
    const currentShape = shapesMap.get(id) as Shape | undefined;
    if (currentShape) {
        const updatedShape = { ...currentShape, ...attrs };
        shapesMap.set(id, updatedShape);
    }
};

const COLORS = [
    '#000000', '#ffffff', '#ef4444', '#f97316', '#f59e0b', '#84cc16', '#10b981',
    '#06b6d4', '#3b82f6', '#6366f1', '#8b5cf6', '#d946ef', '#f43f5e'
];

export const PropertiesPanel: React.FC = () => {
    const { selectedIds, shapes } = useCanvasStore();
    const { theme } = useThemeStore();

    if (selectedIds.length === 0) return null;

    // Only show properties for the first selected item for simplicity, 
    // or handle multi-edit if possible. Here we focus on single/first item.
    const shape = shapes[selectedIds[0]];
    if (!shape) return null;

    const handleColorChange = (key: 'fill' | 'strokeColor', color: string) => {
        selectedIds.forEach(id => {
            updateShape(id, { [key]: color });
        });
    };

    const handleStrokeWidthChange = (width: number) => {
        selectedIds.forEach(id => {
            updateShape(id, { strokeWidth: width });
        });
    };

    return (
        <div className={cn(
            "fixed top-20 right-4 p-4 rounded-xl shadow-lg border w-64 backdrop-blur-md transition-colors z-30",
            theme === 'dark'
                ? "bg-slate-900/90 border-slate-700 text-slate-100"
                : "bg-white/90 border-slate-200 text-slate-800"
        )}>
            <h3 className="text-sm font-semibold mb-3">属性</h3>

            {/* Stroke Color */}
            <div className="mb-4">
                <label className="text-xs font-medium mb-2 block opacity-70">描边颜色</label>
                <div className="flex flex-wrap gap-1.5">
                    {COLORS.map(color => (
                        <button
                            key={color}
                            onClick={() => handleColorChange('strokeColor', color)}
                            className={cn(
                                "w-6 h-6 rounded-full border transition-transform hover:scale-110",
                                shape.strokeColor === color ? "ring-2 ring-blue-500 ring-offset-2" : "border-slate-200 dark:border-slate-600"
                            )}
                            style={{ backgroundColor: color }}
                        />
                    ))}
                </div>
            </div>

            {/* Fill Color */}
            <div className="mb-4">
                <label className="text-xs font-medium mb-2 block opacity-70">填充颜色</label>
                <div className="flex flex-wrap gap-1.5">
                    <button
                        onClick={() => handleColorChange('fill', 'transparent')}
                        className={cn(
                            "w-6 h-6 rounded-full border flex items-center justify-center text-[10px] transition-transform hover:scale-110",
                            shape.fill === 'transparent' ? "ring-2 ring-blue-500 ring-offset-2" : "border-slate-200 dark:border-slate-600"
                        )}
                    >
                        🚫
                    </button>
                    {COLORS.map(color => (
                        <button
                            key={color}
                            onClick={() => handleColorChange('fill', color)}
                            className={cn(
                                "w-6 h-6 rounded-full border transition-transform hover:scale-110",
                                shape.fill === color ? "ring-2 ring-blue-500 ring-offset-2" : "border-slate-200 dark:border-slate-600"
                            )}
                            style={{ backgroundColor: color }}
                        />
                    ))}
                </div>
            </div>

            {/* Stroke Width */}
            <div className="mb-2">
                <label className="text-xs font-medium mb-2 block opacity-70">线条粗细: {shape.strokeWidth || 1}px</label>
                <input
                    type="range"
                    min="0"
                    max="20"
                    value={shape.strokeWidth || 1}
                    onChange={(e) => handleStrokeWidthChange(parseInt(e.target.value))}
                    className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer dark:bg-slate-700"
                />
            </div>
        </div>
    );
};
