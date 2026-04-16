import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types';
import { cn } from '../../lib/utils';
import { Bot, X, GripVertical, Plus, History, Trash2, MessageSquare } from 'lucide-react';
import { AgentMode } from './AgentMode';
import type { ConversationMode } from './ChatInput';
import { aiApi } from '../../services/api/ai';
import { useConversationStore, type ConversationInfo } from '../../stores/conversation_store';
import type { ManagedDiagramTarget } from '../../types';
import { useI18n } from '../../i18n';
import { translateWithLocale } from '../../i18n/core';

interface AISidebarProps {
  roomId: string;
  isDark: boolean;
  isOpen: boolean;
  onToggle: () => void;
  excalidrawAPI: ExcalidrawImperativeAPI | null;
  diagramTarget?: ManagedDiagramTarget | null;
}

type AIMode = ConversationMode;

const MIN_WIDTH = 360;
const MAX_WIDTH = 800;
const DEFAULT_WIDTH = 450;
const STORAGE_KEY = 'ai-sidebar-mode';

export const AISidebar: React.FC<AISidebarProps> = ({
  roomId,
  isDark,
  isOpen,
  onToggle,
  excalidrawAPI,
  diagramTarget,
}) => {
  const { t } = useI18n();
  const [mode, setMode] = useState<AIMode>(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as AIMode | null;
    return saved && ['agent', 'planning', 'mermaid'].includes(saved) ? saved : 'planning';
  });
  const [width, setWidth] = useState(DEFAULT_WIDTH);
  const [isResizing, setIsResizing] = useState(false);
  const sidebarRef = useRef<HTMLDivElement>(null);
  const previousActiveConversationIdRef = useRef<number | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  const {
    conversations,
    activeConversationId,
    isLoading: isHistoryLoading,
    setRoomId,
    fetchConversations,
    createConversation,
    selectConversation,
    deleteConversation,
    updateTitle,
  } = useConversationStore();

  const activeConversation = conversations.find(
    (conversation) => conversation.id === activeConversationId,
  );
  const defaultAssistantTitles = useMemo(
    () => new Set([
      translateWithLocale('en-US', 'aiSidebar.defaultTitle'),
      translateWithLocale('zh-CN', 'aiSidebar.defaultTitle'),
    ]),
    [],
  );
  const defaultNewConversationTitles = useMemo(
    () => new Set([
      translateWithLocale('en-US', 'aiSidebar.newConversationTitle'),
      translateWithLocale('zh-CN', 'aiSidebar.newConversationTitle'),
    ]),
    [],
  );
  const conversationTitle =
    activeConversation?.title
    && !defaultNewConversationTitles.has(activeConversation.title)
    && !defaultAssistantTitles.has(activeConversation.title)
      ? activeConversation.title
      : t('aiSidebar.defaultTitle');

  useEffect(() => {
    if (roomId) {
      setRoomId(roomId);
    }
  }, [roomId, setRoomId]);

  useEffect(() => {
    if (activeConversationId == null || !activeConversation) {
      previousActiveConversationIdRef.current = activeConversationId;
      return;
    }

    if (previousActiveConversationIdRef.current !== activeConversationId) {
      previousActiveConversationIdRef.current = activeConversationId;
      setMode(activeConversation.mode as AIMode);
    }
  }, [activeConversation, activeConversationId, setMode]);

  const handleFirstMessage = useCallback(async (message: string) => {
    if (
      message
      && (activeConversation?.title == null || defaultAssistantTitles.has(activeConversation.title))
    ) {
      const { title } = await aiApi.summarize(message);
      if (activeConversationId != null) {
        await updateTitle(activeConversationId, title);
      }
    }
  }, [activeConversation?.title, activeConversationId, defaultAssistantTitles, updateTitle]);

  const handleNewConversation = useCallback(async () => {
    const createdConversationId = await createConversation(t('aiSidebar.newConversationTitle'), mode);
    if (createdConversationId === null) {
      return;
    }

    setShowHistory(false);
  }, [createConversation, mode, t]);

  const handleSelectConversation = useCallback(async (conversation: ConversationInfo) => {
    setMode(conversation.mode as AIMode);
    await selectConversation(conversation.id);
    setShowHistory(false);
  }, [selectConversation, setMode]);

  const handleDeleteConversation = useCallback(async (id: number, event: React.MouseEvent) => {
    event.stopPropagation();
    await deleteConversation(id);
  }, [deleteConversation]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, mode);
  }, [mode]);

  const handleMouseDown = useCallback((event: React.MouseEvent) => {
    event.preventDefault();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (event: MouseEvent) => {
      const nextWidth = window.innerWidth - event.clientX;
      setWidth(Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, nextWidth)));
    };

    const handleMouseUp = () => setIsResizing(false);

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  return (
    <>
      {!isOpen && (
        <button
          onClick={onToggle}
          className={cn(
            'fixed z-[50] flex items-center gap-2 rounded-l-xl px-2 py-3 shadow-lg transition-all duration-300 hover:shadow-xl',
            isDark
              ? 'border border-r-0 border-zinc-700/50 bg-zinc-800/90 text-zinc-300 hover:bg-zinc-700'
              : 'border border-r-0 border-zinc-200 bg-white/90 text-zinc-700 hover:bg-zinc-50',
            'backdrop-blur-xl',
          )}
          style={{ right: 0, top: '50%', transform: 'translateY(-50%)' }}
          title={t('aiSidebar.open')}
        >
          <Bot size={20} className="text-violet-500" />
        </button>
      )}

      <AnimatePresence>
        {isOpen && (
          <motion.aside
            ref={sidebarRef}
            initial={{ width: 0, opacity: 0 }}
            animate={{ width, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className={cn(
              'ai-sidebar fixed right-0 top-0 bottom-0 z-[45] flex h-full flex-col border-l backdrop-blur-xl',
              isDark
                ? 'border-zinc-700/50 bg-zinc-900/95'
                : 'border-zinc-200/50 bg-white/95',
            )}
            style={{ '--sidebar-width': `${width}px` } as React.CSSProperties}
          >
            <div
              className={cn(
                'absolute left-0 top-0 bottom-0 flex w-1 cursor-ew-resize items-center justify-center transition-colors hover:bg-violet-500/50',
                isResizing && 'bg-violet-500/50',
              )}
              onMouseDown={handleMouseDown}
            >
              <GripVertical
                size={12}
                className={cn(
                  'opacity-0 transition-opacity hover:opacity-100',
                  isDark ? 'text-zinc-500' : 'text-zinc-400',
                )}
              />
            </div>

            <div
              className={cn(
                'flex items-center justify-between border-b px-3 py-2.5',
                isDark ? 'border-zinc-700/50' : 'border-zinc-200/50',
              )}
            >
              <div className="flex min-w-0 flex-1 items-center gap-2">
                <div className="rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 p-1.5">
                  <Bot size={14} className="text-white" />
                </div>
                <span
                  className={cn(
                    'truncate text-sm font-medium',
                    isDark ? 'text-zinc-200' : 'text-zinc-700',
                  )}
                  title={conversationTitle}
                >
                  {conversationTitle}
                </span>
              </div>

              <div className="flex items-center gap-0.5">
                <button
                  onClick={handleNewConversation}
                  className={cn(
                    'rounded-md p-1.5 transition-colors',
                    isDark
                      ? 'text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200'
                      : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700',
                  )}
                  title={t('aiSidebar.newConversation')}
                >
                  <Plus size={16} />
                </button>

                <button
                  onClick={() => {
                    setShowHistory((prev) => !prev);
                    if (!showHistory) {
                      fetchConversations();
                    }
                  }}
                  className={cn(
                    'rounded-md p-1.5 transition-colors',
                    showHistory
                      ? isDark
                        ? 'bg-violet-600 text-white'
                        : 'bg-violet-500 text-white'
                      : isDark
                        ? 'text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200'
                        : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700',
                  )}
                  title={t('aiSidebar.conversationHistory')}
                >
                  <History size={16} />
                </button>

                <button
                  onClick={onToggle}
                  className={cn(
                    'rounded-md p-1.5 transition-colors',
                    isDark
                      ? 'text-zinc-400 hover:bg-zinc-700 hover:text-red-400'
                      : 'text-zinc-500 hover:bg-zinc-100 hover:text-red-500',
                  )}
                  title={t('aiSidebar.close')}
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            <AnimatePresence>
              {showHistory && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className={cn(
                    'overflow-hidden border-b',
                    isDark
                      ? 'border-zinc-700/50 bg-zinc-800/50'
                      : 'border-zinc-200/50 bg-zinc-50/50',
                  )}
                >
                  <div className="max-h-64 space-y-1 overflow-y-auto p-2">
                    {isHistoryLoading ? (
                      <div className="py-4 text-center text-zinc-500">{t('aiSidebar.loading')}</div>
                    ) : conversations.length === 0 ? (
                      <div className="py-4 text-center text-zinc-500">{t('aiSidebar.emptyHistory')}</div>
                    ) : (
                      conversations.map((conversation) => (
                        <div
                          key={conversation.id}
                          onClick={() => {
                            void handleSelectConversation(conversation);
                          }}
                          className={cn(
                            'group flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 transition-colors',
                            conversation.is_active
                              ? isDark
                                ? 'bg-violet-600/20 text-violet-300'
                                : 'bg-violet-100 text-violet-700'
                              : isDark
                                ? 'hover:bg-zinc-700'
                                : 'hover:bg-zinc-100',
                          )}
                        >
                          <MessageSquare size={14} className="flex-shrink-0" />
                          <div className="min-w-0 flex-1">
                            <div
                              className={cn(
                                'truncate text-sm font-medium',
                                isDark ? 'text-zinc-200' : 'text-zinc-700',
                              )}
                            >
                              {conversation.title}
                            </div>
                            <div className="text-xs text-zinc-500">
                              {t('aiSidebar.messageCount', { count: conversation.message_count })}
                            </div>
                          </div>
                          <button
                            onClick={(event) => handleDeleteConversation(conversation.id, event)}
                            className={cn(
                              'rounded p-1 opacity-0 transition-opacity group-hover:opacity-100',
                              isDark
                                ? 'text-red-400 hover:bg-red-600/20'
                                : 'text-red-500 hover:bg-red-100',
                            )}
                            title={t('aiSidebar.deleteConversation')}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="flex-1 overflow-hidden">
              <AgentMode
                roomId={roomId}
                isDark={isDark}
                mode={mode}
                onModeChange={setMode}
                excalidrawAPI={excalidrawAPI}
                onFirstMessage={handleFirstMessage}
                conversationId={activeConversationId}
                diagramTarget={diagramTarget}
              />
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  );
};
