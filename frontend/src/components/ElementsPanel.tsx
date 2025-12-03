/**
 * 模块名称: ElementsPanel
 * 主要功能: 元素面板，显示画布上所有图形元素及其位置信息
 */

import React from 'react';
import { 
    Square, Circle, Triangle, Type, ArrowRight, 
    Minus, Pencil, Image, MapPin
} from 'lucide-react';
import { useCanvasStore } from '../stores/useCanvasStore';
import { cn } from '../lib/utils';
import { useThemeStore } from '../stores/useThemeStore';

/**
 * 元素面板组件
 * 
 * 显示画布上的所有元素及其位置信息，点击可定位到元素
 */
export const ElementsPanel: React.FC = () => {
    const { shapes, selectedIds, setSelectedId, setOffset, scale } = useCanvasStore();
    const { theme } = useThemeStore();

    // 按类型分组
    const shapesByType = Object.values(shapes).reduce((acc, shape) => {
        const type = shape.type;
        if (!acc[type]) acc[type] = [];
        acc[type].push(shape);
        return acc;
    }, {} as Record<string, typeof shapes[keyof typeof shapes][]>);

    // 获取类型图标
    const getIconForType = (type: string) => {
        const iconClass = cn("w-4 h-4", theme === 'dark' ? "text-slate-400" : "text-slate-500");
        switch (type) {
            case 'rect': return <Square className={iconClass} />;
            case 'circle': return <Circle className={iconClass} />;
            case 'diamond': return <Triangle className={iconClass} />;
            case 'text': return <Type className={iconClass} />;
            case 'arrow': return <ArrowRight className={iconClass} />;
            case 'line': return <Minus className={iconClass} />;
            case 'freedraw': return <Pencil className={iconClass} />;
            case 'image': return <Image className={iconClass} />;
            default: return <Square className={iconClass} />;
        }
    };

    // 获取类型显示名称
    const getTypeName = (type: string) => {
        const names: Record<string, string> = {
            'rect': '矩形',
            'circle': '圆形',
            'diamond': '菱形',
            'text': '文本',
            'arrow': '箭头',
            'line': '直线',
            'freedraw': '画笔',
            'image': '图片',
        };
        return names[type] || type;
    };

    // 定位到元素
    const locateElement = (shape: typeof shapes[keyof typeof shapes]) => {
        setSelectedId(shape.id);
        
        // 计算元素中心点
        let centerX = shape.x || 0;
        let centerY = shape.y || 0;
        
        if (shape.width) centerX += shape.width / 2;
        if (shape.height) centerY += shape.height / 2;
        
        // 获取视口中心
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        
        // 计算新的偏移量，使元素居中
        const newOffsetX = viewportWidth / 2 - centerX * scale;
        const newOffsetY = viewportHeight / 2 - centerY * scale;
        
        setOffset({ x: newOffsetX, y: newOffsetY });
    };

    // 格式化坐标
    const formatCoord = (n: number | undefined) => {
        if (n === undefined) return '0';
        return Math.round(n).toString();
    };

    const totalCount = Object.values(shapes).length;

    if (totalCount === 0) {
        return (
            <div className={cn(
                "flex flex-col items-center justify-center py-8 text-sm",
                theme === 'dark' ? "text-slate-500" : "text-slate-400"
            )}>
                <Square className="w-8 h-8 mb-2 opacity-40" />
                <span>暂无元素</span>
                <span className="text-xs mt-1 opacity-70">在画布上绘制来添加元素</span>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full">
            {/* 统计栏 */}
            <div className={cn(
                "flex items-center justify-between px-3 py-2 border-b text-xs",
                theme === 'dark' ? "border-slate-700 text-slate-400" : "border-slate-200 text-slate-500"
            )}>
                <span>共 {totalCount} 个元素</span>
                <span>{Object.keys(shapesByType).length} 种类型</span>
            </div>

            {/* 元素列表 */}
            <div className="flex-1 overflow-y-auto">
                {Object.entries(shapesByType).map(([type, typeShapes]) => (
                    <div key={type} className="mb-1">
                        {/* 类型标题 */}
                        <div className={cn(
                            "flex items-center gap-2 px-3 py-1.5 text-xs font-medium sticky top-0",
                            theme === 'dark' 
                                ? "bg-slate-900/90 text-slate-400 border-b border-slate-800" 
                                : "bg-slate-50/90 text-slate-500 border-b border-slate-200"
                        )}>
                            {getIconForType(type)}
                            <span>{getTypeName(type)}</span>
                            <span className={cn(
                                "ml-auto px-1.5 py-0.5 rounded text-[10px]",
                                theme === 'dark' ? "bg-slate-800 text-slate-500" : "bg-slate-200 text-slate-600"
                            )}>
                                {typeShapes.length}
                            </span>
                        </div>

                        {/* 类型下的元素 */}
                        {typeShapes.map((shape) => {
                            const isSelected = selectedIds.includes(shape.id);
                            return (
                                <div
                                    key={shape.id}
                                    onClick={() => locateElement(shape)}
                                    className={cn(
                                        "flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors text-xs",
                                        isSelected
                                            ? theme === 'dark'
                                                ? "bg-blue-900/30 text-blue-300"
                                                : "bg-blue-50 text-blue-700"
                                            : theme === 'dark'
                                                ? "hover:bg-slate-800 text-slate-300"
                                                : "hover:bg-slate-100 text-slate-600"
                                    )}
                                >
                                    {/* 颜色预览 */}
                                    <div 
                                        className="w-3 h-3 rounded-sm border"
                                        style={{ 
                                            backgroundColor: shape.fill || 'transparent',
                                            borderColor: shape.strokeColor || '#666'
                                        }}
                                    />

                                    {/* 位置信息 */}
                                    <div className="flex-1 flex items-center gap-1">
                                        <MapPin size={10} className={theme === 'dark' ? "text-slate-500" : "text-slate-400"} />
                                        <span className="font-mono">
                                            ({formatCoord(shape.x)}, {formatCoord(shape.y)})
                                        </span>
                                    </div>

                                    {/* 尺寸信息 (如果有) */}
                                    {(shape.width || shape.height) && (
                                        <span className={cn(
                                            "font-mono text-[10px]",
                                            theme === 'dark' ? "text-slate-500" : "text-slate-400"
                                        )}>
                                            {formatCoord(shape.width)}×{formatCoord(shape.height)}
                                        </span>
                                    )}

                                    {/* 文本预览 */}
                                    {shape.type === 'text' && shape.text && (
                                        <span className={cn(
                                            "truncate max-w-[60px] text-[10px]",
                                            theme === 'dark' ? "text-slate-500" : "text-slate-400"
                                        )}>
                                            "{shape.text}"
                                        </span>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                ))}
            </div>
        </div>
    );
};
