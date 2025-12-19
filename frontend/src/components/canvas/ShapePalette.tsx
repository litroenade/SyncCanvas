import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';
import type { ExcalidrawAPI } from '@excalidraw/excalidraw';
import { ShapeType } from './Canvas';

interface ShapePaletteProps {
  excalidrawAPI: ExcalidrawAPI | null;
  isDark?: boolean;
  isActiveShape?: ShapeType;
  onShapeSelect?: (shape: ShapeType) => void;
  className?: string;
}

// 形状配置
const SHAPE_CONFIGS = {
  rectangle: {
    label: '矩形',
    icon: (isActive: boolean, isDark: boolean) => (
      <rect 
        x="4" y="4" width="20" height="20" 
        fill="none"
        stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
        strokeWidth={isActive ? 2 : 1.5}
        rx="1" ry="1"
      />
    ),
    toolProps: {
      type: 'rectangle',
      rounded: 0,
    },
  },
  roundedRectangle: {
    label: '圆角矩形',
    icon: (isActive: boolean, isDark: boolean) => (
      <rect 
        x="4" y="4" width="20" height="20" 
        fill="none"
        stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
        strokeWidth={isActive ? 2 : 1.5}
        rx="3" ry="3"
      />
    ),
    toolProps: {
      type: 'rectangle',
      rounded: 10,
    },
  },
  ellipse: {
    label: '椭圆',
    icon: (isActive: boolean, isDark: boolean) => (
      <ellipse 
        cx="14" cy="14" rx="10" ry="10" 
        fill="none"
        stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
        strokeWidth={isActive ? 2 : 1.5}
      />
    ),
    toolProps: {
      type: 'ellipse',
    },
  },
  diamond: {
    label: '菱形',
    icon: (isActive: boolean, isDark: boolean) => (
      <polygon 
        points="14,4 24,14 14,24 4,14" 
        fill="none"
        stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
        strokeWidth={isActive ? 2 : 1.5}
      />
    ),
    toolProps: {
      type: 'diamond',
    },
  },
  triangle: {
    label: '三角形',
    icon: (isActive: boolean, isDark: boolean) => (
      <polygon 
        points="14,4 24,24 4,24" 
        fill="none"
        stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
        strokeWidth={isActive ? 2 : 1.5}
      />
    ),
    toolProps: {
      type: 'triangle',
    },
  },
  hexagon: {
    label: '六边形',
    icon: (isActive: boolean, isDark: boolean) => (
      <polygon 
        points="14,4 22,8 22,20 14,24 6,20 6,8" 
        fill="none"
        stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
        strokeWidth={isActive ? 2 : 1.5}
      />
    ),
    toolProps: {
      type: 'hexagon',
    },
  },
  star: {
    label: '星形',
    icon: (isActive: boolean, isDark: boolean) => (
      <polygon 
        points="14,2 16,8 22,8 18,12 20,18 14,15 8,18 10,12 6,8 12,8" 
        fill="none"
        stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
        strokeWidth={isActive ? 2 : 1.5}
      />
    ),
    toolProps: {
      type: 'star',
    },
  },
  cloud: {
    label: '云形',
    icon: (isActive: boolean, isDark: boolean) => (
      <path 
        d="M20,10 Q24,10 24,14 Q24,18 20,18 Q20,22 16,22 Q12,22 10,18 Q6,18 6,14 Q6,10 10,10 Q10,6 14,6 Q18,6 20,10"
        fill="none"
        stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
        strokeWidth={isActive ? 2 : 1.5}
      />
    ),
    toolProps: {
      type: 'cloud',
    },
  },
};

// 形状分组
const SHAPE_GROUPS = [
  {
    title: '基础形状',
    shapes: ['rectangle', 'roundedRectangle', 'ellipse'],
  },
  {
    title: '流程图形状',
    shapes: ['diamond', 'triangle', 'hexagon'],
  },
  {
    title: '特殊形状',
    shapes: ['star', 'cloud'],
  },
];

export const ShapePalette: React.FC<ShapePaletteProps> = ({
  excalidrawAPI,
  isDark = false,
  isActiveShape,
  onShapeSelect,
  className = "",
}) => {
  // 点击形状按钮 - 进入该形状的绘制模式
  const handleShapeClick = (shapeType: ShapeType) => {
    if (!excalidrawAPI) {
      console.warn("Excalidraw API 尚未初始化");
      return;
    }

    const config = SHAPE_CONFIGS[shapeType];
    if (!config) return;

    try {
      // 切换到对应的形状工具
      excalidrawAPI.setAppState({
        activeTool: { type: config.toolProps.type as any },
        ...(config.toolProps.rounded !== undefined && {
          currentItemRoundness: config.toolProps.rounded,
        }),
      }, false);

      console.log(`[ShapePalette] 已切换到${config.label}工具`);

      // 通知外部选中状态
      if (onShapeSelect) {
        onShapeSelect(shapeType);
      }
    } catch (error) {
      console.error('[ShapePalette] 切换工具失败:', error);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.1 }}
      className={cn(
        'fixed z-50 right-0 top-0 h-full w-64 pointer-events-auto border-l shadow-lg overflow-y-auto',
        isDark ? 'text-slate-200 bg-slate-800/95' : 'text-slate-800 bg-white/95',
        className
      )}
    >
      <div className="p-4 border-b">
        <h3 className="font-medium">形状工具</h3>
      </div>
      
      {SHAPE_GROUPS.map((group, groupIndex) => (
        <div key={groupIndex} className="p-4 border-b">
          <h4 className={cn(
            'text-sm px-1 font-semibold mb-3',
            isDark ? 'text-slate-400' : 'text-slate-600'
          )}>
            {group.title}
          </h4>
          <div className="grid grid-cols-2 gap-3">
            {group.shapes.map((shapeKey) => {
              const shape = SHAPE_CONFIGS[shapeKey as ShapeType];
              if (!shape) return null;
              
              const isActive = isActiveShape === shapeKey;
              
              return (
                <button
                  key={shapeKey}
                  onClick={() => handleShapeClick(shapeKey as ShapeType)}
                  title={shape.label}
                  className={cn(
                    'p-3 rounded-md flex flex-col items-center gap-2',
                    'cursor-pointer transition-all duration-200',
                    'hover:shadow-md active:scale-95',
                    isActive 
                      ? (isDark ? 'bg-blue-900/50 border-2 border-blue-500' : 'bg-blue-100 border-2 border-blue-400')
                      : (isDark ? 'bg-slate-700 hover:bg-slate-600' : 'bg-slate-100 hover:bg-slate-200')
                  )}
                >
                  <svg width="28" height="28" viewBox="0 0 28 28" className="pointer-events-none">
                    {shape.icon(isActive, isDark)}
                  </svg>
                  <span className="text-xs">{shape.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </motion.div>
  );
};