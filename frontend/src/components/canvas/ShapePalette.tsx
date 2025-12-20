import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Square, Diamond, Circle, Triangle,
  ChevronRight, ArrowRight,
  GitBranch, Package, Zap
} from 'lucide-react';

interface ShapePaletteProps {
  excalidrawAPI: any;   // ✅ 新增：直接控制画布
  isDark: boolean;
}

const ShapePalette: React.FC<ShapePaletteProps> = ({
  excalidrawAPI,
  isDark,
}) => {
  const [selectedShape, setSelectedShape] = useState<string | null>(null);

  if (!excalidrawAPI) return null;

  /** draw.io 行为：点击 Palette 先选工具，拖拽画布再创建元素 */
  const selectShape = (shapeId: string) => {
    setSelectedShape(shapeId);

    const shapeConfig: Record<
      string,
      {
        toolType: 'rectangle' | 'diamond' | 'ellipse' | 'arrow' | 'line';
        roundness?: { type: number } | null;
        startArrowhead?: 'arrow' | null;
        endArrowhead?: 'arrow' | null;
      }
    > = {
      rectangle: { toolType: 'rectangle', roundness: null },
      diamond: { toolType: 'diamond', roundness: null },
      ellipse: { toolType: 'ellipse', roundness: null },
      /** Excalidraw 无原生三角形，退化为矩形工具，后续可自定义形状 */
      triangle: { toolType: 'rectangle', roundness: null },
      process: { toolType: 'rectangle', roundness: { type: 3 } },
      decision: { toolType: 'diamond', roundness: null },
      arrow: { toolType: 'arrow', roundness: null, endArrowhead: 'arrow' },
      branch: {
        toolType: 'arrow',
        roundness: null,
        startArrowhead: 'arrow',
        endArrowhead: 'arrow',
      },
      package: { toolType: 'rectangle', roundness: null },
      zap: { toolType: 'arrow', roundness: null, endArrowhead: 'arrow' },
    };

    const config = shapeConfig[shapeId] ?? shapeConfig.rectangle;

    // 先切换工具，保证 Excalidraw 知道当前绘制类型
    excalidrawAPI.setActiveTool({ type: config.toolType });

    excalidrawAPI.setAppState(
      {
        currentItemRoundness: config.roundness ?? null,
        currentItemStartArrowhead: config.startArrowhead ?? null,
        currentItemEndArrowhead: config.endArrowhead ?? null,
      },
      false,
    );
  };

  const shapeGroups = [
    {
      title: '基础形状',
      shapes: [
        { id: 'rectangle', name: '矩形', icon: <Square size={20} /> },
        { id: 'diamond', name: '菱形', icon: <Diamond size={20} /> },
        { id: 'ellipse', name: '椭圆', icon: <Circle size={20} /> },
        { id: 'triangle', name: '三角形', icon: <Triangle size={20} /> },
      ],
    },
    {
      title: '流程图形状',
      shapes: [
        { id: 'process', name: '流程', icon: <Square size={20} /> },
        { id: 'decision', name: '判断', icon: <ChevronRight size={20} /> },
        { id: 'arrow', name: '箭头', icon: <ArrowRight size={20} /> },
        { id: 'branch', name: '分支', icon: <GitBranch size={20} /> },
      ],
    },
    {
      title: '特殊形状',
      shapes: [
        { id: 'package', name: '包', icon: <Package size={20} /> },
        { id: 'zap', name: '闪电', icon: <Zap size={20} /> },
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
          形状工具
        </h3>
        <ChevronRight size={20} className={isDark ? 'text-white' : 'text-slate-800'} />
      </div>

      {shapeGroups.map((group) => (
        <div key={group.title} className="mb-6 last:mb-0">
          <h4 className={`text-sm font-medium mb-3 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
            {group.title}
          </h4>
          <div className="grid grid-cols-2 gap-6">
            {group.shapes.map((shape) => (
              <button
                key={shape.id}
                onClick={() => selectShape(shape.id)}
                className={`
                  flex flex-col items-center justify-center
                  p-4 rounded-md transition-colors
                  ${selectedShape === shape.id
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
                  {shape.icon}
                </div>
                <span className={`text-xs mt-2 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
                  {shape.name}
                </span>
              </button>
            ))}
          </div>
        </div>
      ))}
    </motion.div>
  );
};

export { ShapePalette };
export default ShapePalette;
