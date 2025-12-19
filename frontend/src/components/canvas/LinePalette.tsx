import React from 'react';
import { motion } from 'framer-motion';
import { 
  Minus, MoreHorizontal, Circle, 
  ArrowRight, ArrowDownUp, ArrowLeftRight,
  ChevronRight
} from 'lucide-react';

interface LinePaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectLine: (lineType: string) => void;
  selectedLine: string | null;
  isDark: boolean;
}

const LinePalette: React.FC<LinePaletteProps> = ({
  isOpen,
  onClose,
  onSelectLine,
  selectedLine,
  isDark
}) => {
  // 线条/箭头分组配置
  const lineGroups = [
    {
      title: "基础线条",
      lines: [
        { id: "solid", name: "实线", icon: <Minus size={20} /> },
        { id: "dashed", name: "虚线", icon: <MoreHorizontal size={20} /> },
        { id: "dotted", name: "点线", icon: <Circle size={8} className="my-auto" /> },
        { id: "double", name: "双实线", icon: <div className="flex gap-1"><Minus size={20} /><Minus size={20} /></div> },
      ]
    },
    {
      title: "箭头样式",
      lines: [
        { id: "singleArrow", name: "单箭头", icon: <ArrowRight size={20} /> },
        { id: "arrowDownUp", name: "双箭头", icon: <ArrowDownUp size={20} /> },
        { id: "bidirectional", name: "双向箭头", icon: <ArrowLeftRight size={20} /> },
        { id: "燕尾箭头", name: "燕尾箭头", icon: <div className="relative"><Minus size={20} /><div className="absolute right-0 top-1/2 -translate-y-1/2 -translate-x-1/2 rotate-45 border-t-2 border-r-2 w-3 h-3" /></div> },
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
        top: '60px', // 避开右上角状态/素材库图标
        bottom: '80px', // 避开右下角bot图标
        width: '16rem',
        zIndex: 45, // 层级低于核心交互元素
        maxHeight: 'calc(100vh - 140px)' // 顶部60px + 底部80px = 垂直留白
      }}
      onMouseEnter={(e) => {
        // 鼠标在面板内时，滚轮仅控制面板滚动（不影响画布）
        e.currentTarget.addEventListener('wheel', (ev) => {
          ev.stopPropagation();
        }, { passive: true });
      }}
    >
      <div className="flex justify-between items-center mb-4">
        <h3 className={`font-medium text-lg ${isDark ? 'text-white' : 'text-slate-800'}`}>
          线条工具
        </h3>
        <button
          onClick={onClose}
          className={`p-1 rounded-full ${isDark ? 'hover:bg-slate-700' : 'hover:bg-gray-100'}`}
          aria-label="关闭线条面板"
        >
          <ChevronRight size={20} className={isDark ? 'text-white' : 'text-slate-800'} />
        </button>
      </div>

      {lineGroups.map((group, groupIndex) => (
        <div key={groupIndex} className="mb-6 last:mb-0">
          <h4 className={`text-sm font-medium mb-3 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
            {group.title}
          </h4>
          <div className="grid grid-cols-2 gap-6">
            {group.lines.map((line) => (
              <button
                key={line.id}
                onClick={() => onSelectLine(line.id)}
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
                aria-label={`选择${line.name}线条`}
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

export default LinePalette;