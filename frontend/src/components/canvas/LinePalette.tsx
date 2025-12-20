import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Minus, MoreHorizontal, Circle,
  ArrowRight, ArrowDownUp, ArrowLeftRight,
  ChevronRight,
} from 'lucide-react';

interface LinePaletteProps {
  excalidrawAPI: any;   // ✅ 新增
  isDark: boolean;
  lineTypes: string[];
}

const LinePalette: React.FC<LinePaletteProps> = ({
  excalidrawAPI,
  isDark,
}) => {
  const [selectedLine, setSelectedLine] = useState<string | null>(null);

  if (!excalidrawAPI) return null;

  const selectLine = (lineId: string) => {
    setSelectedLine(lineId);

    const lineConfig: Record<
      string,
      {
        toolType: 'line' | 'arrow';
        strokeStyle?: 'solid' | 'dashed' | 'dotted';
        startArrowhead?: 'arrow' | null;
        endArrowhead?: 'arrow' | null;
        strokeWidth?: number;
      }
    > = {
      solid: { toolType: 'line', strokeStyle: 'solid' },
      dashed: { toolType: 'line', strokeStyle: 'dashed' },
      dotted: { toolType: 'line', strokeStyle: 'dotted' },
      double: { toolType: 'line', strokeStyle: 'solid', strokeWidth: 2 },
      singleArrow: {
        toolType: 'arrow',
        strokeStyle: 'solid',
        endArrowhead: 'arrow',
      },
      arrowDownUp: {
        toolType: 'arrow',
        strokeStyle: 'solid',
        startArrowhead: 'arrow',
        endArrowhead: 'arrow',
      },
      bidirectional: {
        toolType: 'arrow',
        strokeStyle: 'solid',
        startArrowhead: 'arrow',
        endArrowhead: 'arrow',
      },
    };

    const config = lineConfig[lineId] ?? lineConfig.solid;

    // 先切换工具，保证 Excalidraw 知道当前绘制类型
    excalidrawAPI.setActiveTool({ type: config.toolType });

    excalidrawAPI.setAppState(
      {
        currentItemStrokeStyle: config.strokeStyle ?? 'solid',
        currentItemStartArrowhead: config.startArrowhead ?? null,
        currentItemEndArrowhead: config.endArrowhead ?? null,
        currentItemStrokeWidth: config.strokeWidth ?? 1,
      },
      false,
    );
  };

  const lineGroups = [
    {
      title: '基础线条',
      lines: [
        { id: 'solid', name: '实线', icon: <Minus size={20} /> },
        { id: 'dashed', name: '虚线', icon: <MoreHorizontal size={20} /> },
        { id: 'dotted', name: '点线', icon: <Circle size={8} className="my-auto" /> },
        { id: 'double', name: '双实线', icon: <div className="flex gap-1"><Minus size={20} /><Minus size={20} /></div> },
      ],
    },
    {
      title: '箭头样式',
      lines: [
        { id: 'singleArrow', name: '单箭头', icon: <ArrowRight size={20} /> },
        { id: 'arrowDownUp', name: '双箭头', icon: <ArrowDownUp size={20} /> },
        { id: 'bidirectional', name: '双向箭头', icon: <ArrowLeftRight size={20} /> },
      ],
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, x: 10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 10 }}
      transition={{ duration: 0.2 }}
      className={`
        fixed right-2 ${isDark ? 'bg-slate-900/95' : 'bg-white/95'}
        rounded-lg shadow-lg p-4 overflow-y-auto
        overscroll-contain border ${isDark ? 'border-slate-700' : 'border-gray-200'}
      `}
      style={{
        top: '60px',
        bottom: '80px',
        width: '16rem',
        zIndex: 45,
        maxHeight: 'calc(100vh - 140px)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.addEventListener(
          'wheel',
          (ev) => ev.stopPropagation(),
          { passive: true },
        );
      }}
    >
      <div className="flex justify-between items-center mb-4">
        <h3 className={`font-medium text-lg ${isDark ? 'text-white' : 'text-slate-800'}`}>
          线条工具
        </h3>
        <ChevronRight size={20} className={isDark ? 'text-white' : 'text-slate-800'} />
      </div>

      {lineGroups.map((group) => (
        <div key={group.title} className="mb-6 last:mb-0">
          <h4 className={`text-sm font-medium mb-3 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
            {group.title}
          </h4>
          <div className="grid grid-cols-2 gap-6">
            {group.lines.map((line) => (
              <button
                key={line.id}
                onClick={() => selectLine(line.id)}
                className={`
                  flex flex-col items-center justify-center
                  p-4 rounded-md transition-colors
                  ${selectedLine === line.id
                    ? isDark
                      ? 'bg-blue-900/30 border border-blue-500'
                      : 'bg-blue-100 border border-blue-300'
                    : isDark
                      ? 'hover:bg-slate-800'
                      : 'hover:bg-gray-100'
                  }
                `}
              >
                <div className={isDark ? 'text-white' : 'text-slate-800'}>
                  {line.icon}
                </div>
                <span className={`text-xs mt-2 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
                  {line.name}
                </span>
              </button>
            ))}
          </div>
        </div>
      ))}
    </motion.div>
  );
};

export { LinePalette };
export default LinePalette;
