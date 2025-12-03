import React, { useEffect, useRef } from 'react';
import { cn } from '../lib/utils';
import { useThemeStore } from '../stores/useThemeStore';

export interface ContextMenuItem {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  danger?: boolean;
  separator?: boolean;
}

interface ContextMenuProps {
  x: number;
  y: number;
  items: ContextMenuItem[];
  onClose: () => void;
}

export const ContextMenu: React.FC<ContextMenuProps> = ({ x, y, items, onClose }) => {
  const { theme } = useThemeStore();
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    const handleScroll = () => {
      onClose();
    };

    document.addEventListener('mousedown', handleClickOutside);
    window.addEventListener('scroll', handleScroll, true);
    window.addEventListener('resize', handleScroll);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('scroll', handleScroll, true);
      window.removeEventListener('resize', handleScroll);
    };
  }, [onClose]);

  // 调整位置以防止溢出屏幕
  const style: React.CSSProperties = {
    top: y,
    left: x,
  };

  // 简单的位置调整逻辑 (实际应用中可能需要更复杂的计算)
  if (menuRef.current) {
    const rect = menuRef.current.getBoundingClientRect();
    if (x + rect.width > window.innerWidth) {
      style.left = x - rect.width;
    }
    if (y + rect.height > window.innerHeight) {
      style.top = y - rect.height;
    }
  }

  return (
    <div
      ref={menuRef}
      className={cn(
        'fixed z-50 min-w-[160px] py-1.5 rounded-lg shadow-xl border animate-in fade-in zoom-in-95 duration-100',
        theme === 'dark' 
          ? 'bg-slate-800 border-slate-700 text-slate-200' 
          : 'bg-white border-slate-200 text-slate-700'
      )}
      style={style}
      onContextMenu={(e) => e.preventDefault()}
    >
      {items.map((item, index) => {
        if (item.separator) {
          return (
            <div 
              key={index} 
              className={cn(
                'my-1 h-px',
                theme === 'dark' ? 'bg-slate-700' : 'bg-slate-100'
              )} 
            />
          );
        }

        return (
          <button
            key={index}
            onClick={(e) => {
              e.stopPropagation();
              if (!item.disabled) {
                item.onClick();
                onClose();
              }
            }}
            disabled={item.disabled}
            className={cn(
              'w-full flex items-center gap-2 px-3 py-1.5 text-sm transition-colors text-left',
              item.disabled 
                ? 'opacity-50 cursor-not-allowed' 
                : theme === 'dark'
                  ? 'hover:bg-slate-700'
                  : 'hover:bg-slate-100',
              item.danger && !item.disabled && 'text-red-500 hover:text-red-600'
            )}
          >
            {item.icon && <span className="w-4 h-4 flex items-center justify-center">{item.icon}</span>}
            <span>{item.label}</span>
          </button>
        );
      })}
    </div>
  );
};
