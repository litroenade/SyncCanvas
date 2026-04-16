import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  GripVertical,
  History,
  Languages,
  Loader2,
  Menu,
  Moon,
  Redo2,
  Sun,
  Trash2,
  Undo2,
  Users,
  Wifi,
  WifiOff,
  X,
} from 'lucide-react';

import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';
import type { AppLocale } from '../../i18n';

interface FabPosition {
  x: number;
  y: number;
}

interface MobileFABProps {
  isDark: boolean;
  isConnected: boolean;
  isSynced: boolean;
  collaboratorsCount: number;
  locale: AppLocale;
  onUndo: () => void;
  onRedo: () => void;
  onToggleLocale: () => void;
  onToggleTheme: () => void;
  onToggleHistory: () => void;
  onClearCanvas: () => void;
}

const FAB_SIZE = 52;
const FAB_STORAGE_KEY = 'mobile-fab-position';
const EDGE_MARGIN = 12;
const TOP_SAFE_ZONE = 80;

function getSafePosition(saved?: FabPosition | null): FabPosition {
  const windowWidth = typeof window !== 'undefined' ? window.innerWidth : 400;
  const windowHeight = typeof window !== 'undefined' ? window.innerHeight : 800;

  const defaultPos = {
    x: windowWidth - FAB_SIZE - EDGE_MARGIN,
    y: windowHeight - FAB_SIZE - 100,
  };

  if (!saved) {
    return defaultPos;
  }

  return {
    x: Math.min(Math.max(EDGE_MARGIN, saved.x), windowWidth - FAB_SIZE - EDGE_MARGIN),
    y: Math.min(Math.max(TOP_SAFE_ZONE, saved.y), windowHeight - FAB_SIZE - EDGE_MARGIN),
  };
}

function getStatusConfig(
  isConnected: boolean,
  isSynced: boolean,
  t: (key: string) => string,
) {
  if (!isConnected) {
    return {
      color: 'bg-red-500',
      textColor: 'text-red-500',
      icon: WifiOff,
      text: t('mobileFab.status.offline'),
      pulse: false,
      spin: false,
    };
  }
  if (!isSynced) {
    return {
      color: 'bg-amber-500',
      textColor: 'text-amber-500',
      icon: Loader2,
      text: t('mobileFab.status.syncing'),
      pulse: true,
      spin: true,
    };
  }
  return {
    color: 'bg-emerald-500',
    textColor: 'text-emerald-500',
    icon: Wifi,
    text: t('mobileFab.status.connected'),
    pulse: false,
    spin: false,
  };
}

export const MobileFAB: React.FC<MobileFABProps> = ({
  isDark,
  isConnected,
  isSynced,
  collaboratorsCount,
  locale,
  onUndo,
  onRedo,
  onToggleLocale,
  onToggleTheme,
  onToggleHistory,
  onClearCanvas,
}) => {
  const { t } = useI18n();
  const [isOpen, setIsOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [position, setPosition] = useState<FabPosition>(() => {
    try {
      const saved = localStorage.getItem(FAB_STORAGE_KEY);
      return getSafePosition(saved ? JSON.parse(saved) : null);
    } catch {
      return getSafePosition(null);
    }
  });
  const dragStartRef = useRef<{ x: number; y: number; posX: number; posY: number } | null>(null);

  useEffect(() => {
    const handleResize = () => {
      setPosition((previous) => getSafePosition(previous));
    };

    window.addEventListener('resize', handleResize);
    window.addEventListener('orientationchange', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('orientationchange', handleResize);
    };
  }, []);

  const handlePointerDown = useCallback((event: React.PointerEvent) => {
    event.preventDefault();
    event.stopPropagation();
    dragStartRef.current = {
      x: event.clientX,
      y: event.clientY,
      posX: position.x,
      posY: position.y,
    };
    setIsDragging(false);
    (event.target as HTMLElement).setPointerCapture(event.pointerId);
  }, [position]);

  const handlePointerMove = useCallback((event: React.PointerEvent) => {
    if (!dragStartRef.current) {
      return;
    }

    const deltaX = event.clientX - dragStartRef.current.x;
    const deltaY = event.clientY - dragStartRef.current.y;
    const distance = Math.sqrt(deltaX ** 2 + deltaY ** 2);
    if (distance <= 10) {
      return;
    }

    setIsDragging(true);
    setPosition({
      x: Math.min(
        Math.max(EDGE_MARGIN, dragStartRef.current.posX + deltaX),
        window.innerWidth - FAB_SIZE - EDGE_MARGIN,
      ),
      y: Math.min(
        Math.max(TOP_SAFE_ZONE, dragStartRef.current.posY + deltaY),
        window.innerHeight - FAB_SIZE - EDGE_MARGIN,
      ),
    });
  }, []);

  const handlePointerUp = useCallback((event: React.PointerEvent) => {
    (event.target as HTMLElement).releasePointerCapture(event.pointerId);
    if (isDragging) {
      localStorage.setItem(FAB_STORAGE_KEY, JSON.stringify(position));
      window.setTimeout(() => setIsDragging(false), 100);
    } else if (dragStartRef.current) {
      setIsOpen((previous) => !previous);
    }
    dragStartRef.current = null;
  }, [isDragging, position]);

  const statusConfig = useMemo(
    () => getStatusConfig(isConnected, isSynced, t),
    [isConnected, isSynced, t],
  );
  const StatusIcon = statusConfig.icon;

  const menuItems = useMemo(() => [
    { label: t('mobileFab.undo'), icon: Undo2, onClick: onUndo, closeOnClick: true },
    { label: t('mobileFab.redo'), icon: Redo2, onClick: onRedo, closeOnClick: true },
    {
      label: isDark ? t('mobileFab.lightMode') : t('mobileFab.darkMode'),
      icon: isDark ? Sun : Moon,
      onClick: onToggleTheme,
      closeOnClick: true,
    },
    {
      label: locale === 'zh-CN' ? t('locale.switchToEnglish') : t('locale.switchToChinese'),
      icon: Languages,
      onClick: onToggleLocale,
      closeOnClick: true,
    },
    { label: t('mobileFab.history'), icon: History, onClick: onToggleHistory, closeOnClick: true },
    {
      label: t('mobileFab.clear'),
      icon: Trash2,
      onClick: () => {
        if (window.confirm(t('mobileFab.clearConfirm'))) {
          onClearCanvas();
          setIsOpen(false);
        }
      },
      closeOnClick: false,
      danger: true,
    },
  ], [isDark, locale, onClearCanvas, onRedo, onToggleHistory, onToggleLocale, onToggleTheme, onUndo, t]);

  return (
    <>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[200] bg-black/30 backdrop-blur-sm"
            onClick={() => setIsOpen(false)}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 350, mass: 0.8 }}
            className={cn(
              'fixed bottom-0 left-0 right-0 z-[201] rounded-t-[20px] glass-panel',
              isDark ? 'bg-zinc-900/95' : 'bg-white/95',
            )}
            style={{
              paddingBottom: 'max(24px, env(safe-area-inset-bottom, 24px))',
              maxHeight: '80vh',
              overflowY: 'auto',
              overflowX: 'hidden',
            }}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex justify-center pb-2 pt-3">
              <div
                className={cn(
                  'h-1 w-9 rounded-full transition-colors',
                  isDark ? 'bg-zinc-600' : 'bg-zinc-300',
                )}
              />
            </div>

            <div
              className={cn(
                'mx-4 mb-4 flex items-center justify-between rounded-2xl px-4 py-3',
                isDark ? 'bg-zinc-800/60' : 'bg-zinc-100/80',
              )}
            >
              <div className="flex items-center gap-2.5">
                <div className="relative">
                  <div
                    className={cn(
                      'h-2.5 w-2.5 rounded-full',
                      statusConfig.color,
                      statusConfig.pulse && 'animate-pulse',
                    )}
                  />
                  {statusConfig.pulse && (
                    <div
                      className={cn(
                        'absolute inset-0 h-2.5 w-2.5 rounded-full animate-ping opacity-75',
                        statusConfig.color,
                      )}
                    />
                  )}
                </div>
                <StatusIcon
                  size={15}
                  className={cn(statusConfig.textColor, statusConfig.spin && 'animate-spin')}
                />
                <span className={cn('text-sm font-medium', isDark ? 'text-zinc-200' : 'text-zinc-700')}>
                  {statusConfig.text}
                </span>
              </div>

              {collaboratorsCount > 0 && (
                <div
                  className={cn(
                    'flex items-center gap-1.5 rounded-full border px-2.5 py-1',
                    'bg-gradient-to-r from-violet-500/20 to-purple-500/20',
                    isDark ? 'border-violet-500/30' : 'border-violet-300/50',
                  )}
                >
                  <Users size={13} className="text-violet-500" />
                  <span className={cn('text-xs font-semibold', isDark ? 'text-violet-300' : 'text-violet-600')}>
                    {t('mobileFab.onlineCount', { count: collaboratorsCount + 1 })}
                  </span>
                </div>
              )}
            </div>

            <div className="grid grid-cols-3 gap-2 px-4">
              {menuItems.map((item, index) => {
                const Icon = item.icon;
                return (
                  <motion.button
                    key={item.label}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    onClick={() => {
                      item.onClick();
                      if (item.closeOnClick) {
                        setIsOpen(false);
                      }
                    }}
                    className={cn(
                      'flex flex-col items-center gap-2 rounded-2xl py-4 transition-all duration-150 active:scale-95',
                      isDark
                        ? 'hover:bg-zinc-800/80 active:bg-zinc-700/80'
                        : 'hover:bg-zinc-100 active:bg-zinc-200',
                      item.danger && 'text-red-500',
                    )}
                  >
                    <div
                      className={cn(
                        'flex h-12 w-12 items-center justify-center rounded-2xl transition-colors',
                        item.danger
                          ? isDark ? 'bg-red-500/15' : 'bg-red-50'
                          : isDark ? 'bg-zinc-800' : 'bg-zinc-100',
                      )}
                    >
                      <Icon
                        size={22}
                        strokeWidth={1.8}
                        className={cn(
                          item.danger
                            ? 'text-red-500'
                            : isDark ? 'text-zinc-200' : 'text-zinc-700',
                        )}
                      />
                    </div>
                    <span
                      className={cn(
                        'text-xs font-medium',
                        item.danger
                          ? 'text-red-500'
                          : isDark ? 'text-zinc-400' : 'text-zinc-600',
                      )}
                    >
                      {item.label}
                    </span>
                  </motion.button>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        animate={{
          scale: isDragging ? 1.15 : 1,
          boxShadow: isDragging
            ? '0 20px 40px rgba(0,0,0,0.25)'
            : '0 8px 24px rgba(0,0,0,0.15)',
        }}
        transition={{ type: 'spring', stiffness: 400, damping: 25 }}
        className={cn(
          'fixed z-[202] flex touch-none select-none items-center justify-center rounded-2xl border transition-colors duration-200',
          isDark ? 'border-zinc-700/80 bg-zinc-800' : 'border-zinc-200/80 bg-white',
        )}
        style={{
          left: position.x,
          top: position.y,
          width: FAB_SIZE,
          height: FAB_SIZE,
          cursor: isDragging ? 'grabbing' : 'pointer',
        }}
      >
        <motion.div
          animate={{ rotate: isOpen ? 135 : 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        >
          {isOpen ? (
            <X size={24} strokeWidth={2} className={isDark ? 'text-zinc-200' : 'text-zinc-700'} />
          ) : (
            <Menu size={24} strokeWidth={2} className={isDark ? 'text-zinc-200' : 'text-zinc-700'} />
          )}
        </motion.div>

        {!isOpen && (
          <div className="absolute -right-1 -top-1">
            <div
              className={cn(
                'h-3.5 w-3.5 rounded-full border-2',
                isDark ? 'border-zinc-800' : 'border-white',
                statusConfig.color,
              )}
            >
              {statusConfig.pulse && (
                <div
                  className={cn(
                    'absolute inset-0 rounded-full animate-ping opacity-60',
                    statusConfig.color,
                  )}
                />
              )}
            </div>
          </div>
        )}

        {isDragging && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="absolute inset-0 flex items-center justify-center rounded-2xl bg-black/10"
          >
            <GripVertical size={20} className="text-white/80" />
          </motion.div>
        )}
      </motion.div>
    </>
  );
};
