/**
 * 类draw.io点即用线条/箭头工具栏
 * 点击对应线条样式按钮，直接在画布绘制该样式的线条/箭头
 */
import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';
import type { ExcalidrawAPI } from '@excalidraw/excalidraw';

export type LineType = 
  | 'straight' // 直线
  | 'dashed' // 虚线
  | 'arrow' // 单箭头
  | 'doubleArrow' // 双箭头
  | 'dotLine' // 点线
  | 'arrowDashed' // 虚线箭头
  | 'curved' // 曲线
  | 'curvedArrow' // 曲线箭头
  | 'angled' // 折线
  | 'angledArrow'; // 折线箭头

interface LinePaletteProps {
  excalidrawAPI: ExcalidrawAPI | null;
  isDark?: boolean;
  isActiveLine?: LineType;
  onLineSelect?: (line: LineType) => void;
  lineTypes: LineType[];
  className?: string;
}

// 线条配置映射（定义每种线条的绘制参数）
const LINE_CONFIGS = {
  straight: {
    label: '直线',
    icon: (isActive: boolean, isDark: boolean) => (
      <line x1="4" y1="10" x2="24" y2="10" 
        stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
        strokeWidth={isActive ? 2 : 1.5}
        strokeLinecap="round"
      />
    ),
    toolProps: {
      type: 'arrow',
      strokeDasharray: null,
      startArrowhead: null,
      endArrowhead: null,
      strokeWidth: 2,
    },
  },
  dashed: {
    label: '虚线',
    icon: (isActive: boolean, isDark: boolean) => (
      <line x1="4" y1="10" x2="24" y2="10" 
        stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
        strokeWidth={isActive ? 2 : 1.5}
        strokeDasharray="4,2"
        strokeLinecap="round"
      />
    ),
    toolProps: {
      type: 'arrow',
      strokeDasharray: '4,2',
      startArrowhead: null,
      endArrowhead: null,
      strokeWidth: 2,
    },
  },
  arrow: {
    label: '单箭头',
    icon: (isActive: boolean, isDark: boolean) => (
      <g>
        <line x1="4" y1="10" x2="20" y2="10" 
          stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
          strokeWidth={isActive ? 2 : 1.5}
          strokeLinecap="round"
        />
        <polygon points="20,10 14,6 14,14" 
          fill={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
          stroke="none"
        />
      </g>
    ),
    toolProps: {
      type: 'arrow',
      strokeDasharray: null,
      startArrowhead: null,
      endArrowhead: 'arrow',
      strokeWidth: 2,
    },
  },
  doubleArrow: {
    label: '双箭头',
    icon: (isActive: boolean, isDark: boolean) => (
      <g>
        <line x1="8" y1="10" x2="20" y2="10" 
          stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
          strokeWidth={isActive ? 2 : 1.5}
          strokeLinecap="round"
        />
        <polygon points="20,10 14,6 14,14" 
          fill={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
          stroke="none"
        />
        <polygon points="8,10 14,6 14,14" 
          fill={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
          stroke="none"
          transform="rotate(180 11 10)"
        />
      </g>
    ),
    toolProps: {
      type: 'arrow',
      strokeDasharray: null,
      startArrowhead: 'arrow',
      endArrowhead: 'arrow',
      strokeWidth: 2,
    },
  },
  dotLine: {
    label: '点线',
    icon: (isActive: boolean, isDark: boolean) => (
      <line x1="4" y1="10" x2="24" y2="10" 
        stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
        strokeWidth={isActive ? 2 : 1.5}
        strokeDasharray="1,3"
        strokeLinecap="round"
      />
    ),
    toolProps: {
      type: 'arrow',
      strokeDasharray: '1,3',
      startArrowhead: null,
      endArrowhead: null,
      strokeWidth: 2,
    },
  },
  arrowDashed: {
    label: '虚线箭头',
    icon: (isActive: boolean, isDark: boolean) => (
      <g>
        <line x1="4" y1="10" x2="20" y2="10" 
          stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
          strokeWidth={isActive ? 2 : 1.5}
          strokeDasharray="4,2"
          strokeLinecap="round"
        />
        <polygon points="20,10 14,6 14,14" 
          fill={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
          stroke="none"
        />
      </g>
    ),
    toolProps: {
      type: 'arrow',
      strokeDasharray: '4,2',
      startArrowhead: null,
      endArrowhead: 'arrow',
      strokeWidth: 2,
    },
  },
  curved: {
    label: '曲线',
    icon: (isActive: boolean, isDark: boolean) => (
      <path d="M4,10 Q14,2 24,10" 
        fill="none"
        stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
        strokeWidth={isActive ? 2 : 1.5}
        strokeLinecap="round"
      />
    ),
    toolProps: {
      type: 'arrow',
      strokeDasharray: null,
      startArrowhead: null,
      endArrowhead: null,
      strokeWidth: 2,
      isCurved: true,
    },
  },
  curvedArrow: {
    label: '曲线箭头',
    icon: (isActive: boolean, isDark: boolean) => (
      <g>
        <path d="M4,10 Q14,2 20,10" 
          fill="none"
          stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
          strokeWidth={isActive ? 2 : 1.5}
          strokeLinecap="round"
        />
        <polygon points="20,10 14,6 14,14" 
          fill={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
          stroke="none"
        />
      </g>
    ),
    toolProps: {
      type: 'arrow',
      strokeDasharray: null,
      startArrowhead: null,
      endArrowhead: 'arrow',
      strokeWidth: 2,
      isCurved: true,
    },
  },
  angled: {
    label: '折线',
    icon: (isActive: boolean, isDark: boolean) => (
      <g>
        <line x1="4" y1="10" x2="14" y2="10" 
          stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
          strokeWidth={isActive ? 2 : 1.5}
          strokeLinecap="round"
        />
        <line x1="14" y1="10" x2="14" y2="4" 
          stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
          strokeWidth={isActive ? 2 : 1.5}
          strokeLinecap="round"
        />
        <line x1="14" y1="4" x2="24" y2="4" 
          stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
          strokeWidth={isActive ? 2 : 1.5}
          strokeLinecap="round"
        />
      </g>
    ),
    toolProps: {
      type: 'arrow',
      strokeDasharray: null,
      startArrowhead: null,
      endArrowhead: null,
      strokeWidth: 2,
      isAngled: true,
    },
  },
  angledArrow: {
    label: '折线箭头',
    icon: (isActive: boolean, isDark: boolean) => (
      <g>
        <line x1="4" y1="10" x2="14" y2="10" 
          stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
          strokeWidth={isActive ? 2 : 1.5}
          strokeLinecap="round"
        />
        <line x1="14" y1="10" x2="14" y2="4" 
          stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
          strokeWidth={isActive ? 2 : 1.5}
          strokeLinecap="round"
        />
        <line x1="14" y1="4" x2="20" y2="4" 
          stroke={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
          strokeWidth={isActive ? 2 : 1.5}
          strokeLinecap="round"
        />
        <polygon points="20,4 14,0 14,8" 
          fill={isActive ? (isDark ? "#3b82f6" : "#2563eb") : (isDark ? "#94a3b8" : "#64748b")} 
          stroke="none"
        />
      </g>
    ),
    toolProps: {
      type: 'arrow',
      strokeDasharray: null,
      startArrowhead: null,
      endArrowhead: 'arrow',
      strokeWidth: 2,
      isAngled: true,
    },
  },
};

export const LinePalette: React.FC<LinePaletteProps> = ({
  excalidrawAPI,
  isDark = false,
  isActiveLine,
  onLineSelect,
  lineTypes,
  className = "",
}) => {
  // 点击线条按钮 - 进入该线条的绘制模式
  const handleLineClick = (lineType: LineType) => {
    if (!excalidrawAPI) {
      console.warn("Excalidraw API 尚未初始化");
      return;
    }

    const config = LINE_CONFIGS[lineType];
    if (!config) return;

    try {
      // 使用 setAppState 来切换到 arrow 工具
      excalidrawAPI.setAppState({
        activeTool: { type: 'arrow' },
        currentItemStrokeWidth: config.toolProps.strokeWidth || 2,
        currentItemStrokeDasharray: config.toolProps.strokeDasharray,
        currentItemStartArrowhead: config.toolProps.startArrowhead,
        currentItemEndArrowhead: config.toolProps.endArrowhead,
        currentItemIsCurved: config.toolProps.isCurved,
        currentItemIsAngled: config.toolProps.isAngled,
      }, false);

      console.log(`[LinePalette] 已切换到${config.label}工具（arrow），请在画布上拖动以绘制`);

      // 通知外部选中状态
      if (onLineSelect) {
        onLineSelect(lineType);
      }
    } catch (error) {
      console.error('[LinePalette] 切换工具失败:', error);
    }
  };

  // 确定面板标题
  const panelTitle = lineTypes.some(t => t.includes('arrow')) 
    ? '箭头工具' 
    : '线条工具';

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
        <h3 className="font-medium">{panelTitle}</h3>
      </div>
      
      <div className="p-4 grid grid-cols-2 gap-3">
        {lineTypes.map((lineKey) => {
          // 过滤掉未定义的线条类型
          if (!LINE_CONFIGS[lineKey as LineType]) return null;
          
          const line = LINE_CONFIGS[lineKey as LineType];
          const isActive = isActiveLine === lineKey;
          
          return (
            <button
              key={lineKey}
              onClick={() => handleLineClick(lineKey as LineType)}
              title={line.label}
              className={cn(
                'p-3 rounded-md flex flex-col items-center gap-2',
                'cursor-pointer transition-all duration-200',
                'hover:shadow-md active:scale-95',
                isActive 
                  ? (isDark ? 'bg-blue-900/50 border-2 border-blue-500' : 'bg-blue-100 border-2 border-blue-400')
                  : (isDark ? 'bg-slate-700 hover:bg-slate-600' : 'bg-slate-100 hover:bg-slate-200')
              )}
            >
              <svg width="28" height="20" viewBox="0 0 28 20" className="pointer-events-none">
                {line.icon(isActive, isDark)}
              </svg>
              <span className="text-xs">{line.label}</span>
            </button>
          );
        })}
      </div>
    </motion.div>
  );
};