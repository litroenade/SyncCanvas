import React from 'react';
import { motion } from 'framer-motion';
import { 
  Square, Diamond, Circle, Triangle,
  ChevronRight, ArrowRight,
  GitBranch, Package, Zap
} from 'lucide-react';

interface ShapePaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectShape: (shapeType: string) => void;
  selectedShape: string | null;
  isDark: boolean;
}

const ShapePalette: React.FC<ShapePaletteProps> = ({
  isOpen,
  onClose,
  onSelectShape,
  selectedShape,
  isDark
}) => {
  // 形状列表配置
  const shapeGroups = [
    {
      title: "基础形状",
      shapes: [
        { id: "rectangle", name: "矩形", icon: <Square size={20} /> },
        { id: "diamond", name: "菱形", icon: <Diamond size={20} /> },
        { id: "ellipse", name: "椭圆", icon: <Circle size={20} /> },
        { id: "triangle", name: "三角形", icon: <Triangle size={20} /> },
      ]
    },
    {
      title: "流程图形状",
      shapes: [
        { id: "process", name: "流程", icon: <Square size={20} /> },
        { id: "decision", name: "判断", icon: <ChevronRight size={20} /> },
        { id: "arrow", name: "箭头", icon: <ArrowRight size={20} /> },
        { id: "branch", name: "分支", icon: <GitBranch size={20} /> },
      ]
    },
    {
      title: "特殊形状",
      shapes: [
        { id: "package", name: "包", icon: <Package size={20} /> },
        { id: "zap", name: "闪电", icon: <Zap size={20} /> },
      ]
    }
  ];

  return (
    <motion.div
      initial={{ opacity: 0, x: 10 }}
      animate={{ opacity: isOpen ? 1 : 0, x: isOpen ? 0 : 10 }}
      exit={{ opacity: 0, x: 10 }}
      transition={{ duration: 0.2 }}
      className={`
        fixed right-2 ${isDark ? 'bg-slate-900/95' : 'bg-white/95'} 
        rounded-lg shadow-lg p-4 overflow-y-auto
        overscroll-contain border ${isDark ? 'border-slate-700' : 'border-gray-200'}
      `}
      style={{
        top: '60px', // 避开右上角图标
        bottom: '80px', // 避开右下角bot图标
        width: '16rem',
        zIndex: 45, // 低于bot图标和MobileFAB
        maxHeight: 'calc(100vh - 140px)' // 顶部60px + 底部80px
      }}
      onMouseEnter={(e) => {
        // 鼠标进入面板时，阻止滚轮事件冒泡到画布
        e.currentTarget.addEventListener('wheel', (ev) => {
          ev.stopPropagation();
        }, { passive: true });
      }}
    >
      <div className="flex justify-between items-center mb-4">
        <h3 className={`font-medium text-lg ${isDark ? 'text-white' : 'text-slate-800'}`}>
          形状工具
        </h3>
        <button
          onClick={onClose}
          className={`p-1 rounded-full ${isDark ? 'hover:bg-slate-700' : 'hover:bg-gray-100'}`}
          aria-label="关闭形状面板"
        >
          <ChevronRight size={20} className={isDark ? 'text-white' : 'text-slate-800'} />
        </button>
      </div>

      {shapeGroups.map((group, groupIndex) => (
        <div key={groupIndex} className="mb-6 last:mb-0">
          <h4 className={`text-sm font-medium mb-3 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
            {group.title}
          </h4>
          <div className="grid grid-cols-2 gap-6">
            {group.shapes.map((shape) => (
              <button
                key={shape.id}
                onClick={() => onSelectShape(shape.id)}
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
                aria-label={`选择${shape.name}工具`}
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

export default ShapePalette;