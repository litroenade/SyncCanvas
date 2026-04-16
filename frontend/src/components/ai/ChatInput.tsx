import React, { useRef, useEffect, useCallback, useState, useMemo } from 'react';
import { cn } from '../../lib/utils';
import {
  Send,
  Loader2,
  Plus,
  ChevronUp,
  Check,
  Sparkles,
  Zap,
  Brain,
  FileCode2,
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AI_CONVERSATION_MODE_COPY, DIAGRAM_ENTRY_COPY } from '../../lib/diagramRegistry';
import { configApi, type ModelGroup } from '../../services/api/config';
import { useI18n } from '../../i18n';

export type ConversationMode = 'agent' | 'planning' | 'mermaid';

interface ChatInputProps {
  isDark: boolean;
  input: string;
  setInput: (value: string) => void;
  isLoading: boolean;
  onSend: () => void;
  placeholder?: string;
  mode: ConversationMode;
  onModeChange: (mode: ConversationMode) => void;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  isDark,
  input,
  setInput,
  isLoading,
  onSend,
  placeholder = DIAGRAM_ENTRY_COPY.inputPlaceholder,
  mode,
  onModeChange,
}) => {
  const { t } = useI18n();
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const queryClient = useQueryClient();
  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const [modeMenuOpen, setModeMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const modeMenuRef = useRef<HTMLDivElement>(null);

  const { data: modelGroups = {} } = useQuery<Record<string, ModelGroup>>({
    queryKey: ['model-groups'],
    queryFn: configApi.getModelGroups,
    staleTime: 60000,
  });

  const { data: currentModels } = useQuery({
    queryKey: ['current-models'],
    queryFn: configApi.getCurrentModels,
    staleTime: 30000,
  });

  const switchMutation = useMutation({
    mutationFn: (groupName: string) => configApi.switchModelGroup(groupName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['current-models'] });
      setModelMenuOpen(false);
    },
  });

  const modeOptions = useMemo(() => [
    {
      id: 'planning' as const,
      label: AI_CONVERSATION_MODE_COPY.planning.label,
      description: AI_CONVERSATION_MODE_COPY.planning.description,
      icon: Brain,
    },
    {
      id: 'agent' as const,
      label: AI_CONVERSATION_MODE_COPY.agent.label,
      description: AI_CONVERSATION_MODE_COPY.agent.description,
      icon: Zap,
    },
    {
      id: 'mermaid' as const,
      label: AI_CONVERSATION_MODE_COPY.mermaid.label,
      description: AI_CONVERSATION_MODE_COPY.mermaid.description,
      icon: FileCode2,
    },
  ], [t]);
  const groupNames = Object.keys(modelGroups);
  const currentGroupName = currentModels?.current || '';
  const currentGroup = currentGroupName ? modelGroups[currentGroupName] : null;
  const displayModelName = currentGroup?.chat_model?.model || t('chatInput.defaultModel');
  const currentMode = modeOptions.find((item) => item.id === mode) || modeOptions[0];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setModelMenuOpen(false);
      }
      if (modeMenuRef.current && !modeMenuRef.current.contains(event.target as Node)) {
        setModeMenuOpen(false);
      }
    };

    if (modelMenuOpen || modeMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }

    return undefined;
  }, [modelMenuOpen, modeMenuOpen]);

  useEffect(() => {
    const timer = window.setTimeout(() => inputRef.current?.focus(), 100);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    const textarea = inputRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  }, [input]);

  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  }, [onSend]);

  return (
    <div
      className={cn(
        'chat-input-container border-t p-3',
        isDark ? 'border-zinc-800 bg-zinc-900' : 'border-zinc-200 bg-white',
      )}
    >
      <div
        className={cn(
          'flex items-end gap-2 rounded-2xl border px-3 py-2.5 transition-colors',
          isDark
            ? 'border-zinc-700 bg-zinc-800 focus-within:border-zinc-600'
            : 'border-zinc-200 bg-zinc-50 focus-within:border-zinc-300',
        )}
      >
        <textarea
          ref={inputRef}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isLoading}
          rows={1}
          className={cn(
            'min-h-[24px] max-h-[120px] flex-1 resize-none bg-transparent text-sm leading-relaxed outline-none',
            isDark
              ? 'text-zinc-100 placeholder:text-zinc-500'
              : 'text-zinc-900 placeholder:text-zinc-400',
            isLoading && 'opacity-50',
          )}
        />

        <button
          onClick={onSend}
          disabled={!input.trim() || isLoading}
          className={cn(
            'flex-shrink-0 rounded-xl p-2 transition-all duration-200',
            input.trim() && !isLoading
              ? 'bg-violet-500 text-white hover:bg-violet-600'
              : isDark
                ? 'bg-zinc-700 text-zinc-500'
                : 'bg-zinc-200 text-zinc-400',
          )}
          title={t('chatInput.send')}
        >
          {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
        </button>
      </div>

      <div className="mt-2 flex items-center gap-2">
        <button
          className={cn(
            'rounded p-1 transition-colors',
            isDark ? 'text-zinc-500 hover:text-zinc-300' : 'text-zinc-400 hover:text-zinc-600',
          )}
          title={t('chatInput.attachmentsSoon')}
        >
          <Plus size={16} />
        </button>

        <div className="relative" ref={modeMenuRef}>
          <button
            onClick={() => setModeMenuOpen((prev) => !prev)}
            className={cn(
              'flex items-center gap-1 rounded-lg px-2 py-1 text-xs transition-colors',
              isDark
                ? 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200'
                : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700',
            )}
          >
            <ChevronUp size={12} className={cn('transition-transform', !modeMenuOpen && 'rotate-180')} />
            <span>{currentMode.label}</span>
          </button>

          {modeMenuOpen && (
            <div
              className={cn(
                'absolute bottom-full left-0 z-50 mb-1 w-72 overflow-hidden rounded-xl border shadow-xl',
                isDark ? 'border-zinc-700 bg-zinc-900' : 'border-zinc-200 bg-white',
              )}
            >
              <div
                className={cn(
                  'border-b px-3 py-2 text-xs font-medium',
                  isDark ? 'border-zinc-700 text-zinc-400' : 'border-zinc-200 text-zinc-500',
                )}
              >
                {t('chatInput.conversationMode')}
              </div>
              {modeOptions.map((modeItem) => (
                <button
                  key={modeItem.id}
                  onClick={() => {
                    onModeChange(modeItem.id);
                    setModeMenuOpen(false);
                  }}
                  className={cn(
                    'w-full px-3 py-2.5 text-left transition-colors',
                    mode === modeItem.id
                      ? isDark
                        ? 'bg-violet-500/20'
                        : 'bg-violet-50'
                      : isDark
                        ? 'hover:bg-zinc-800'
                        : 'hover:bg-zinc-50',
                  )}
                >
                  <div className="flex items-center gap-2">
                    <modeItem.icon
                      size={14}
                      className={cn(
                        mode === modeItem.id
                          ? 'text-violet-500'
                          : isDark
                            ? 'text-zinc-400'
                            : 'text-zinc-500',
                      )}
                    />
                    <span
                      className={cn(
                        'text-sm font-medium',
                        isDark ? 'text-zinc-200' : 'text-zinc-700',
                      )}
                    >
                      {modeItem.label}
                    </span>
                    {mode === modeItem.id && (
                      <Check size={14} className="ml-auto text-violet-500" />
                    )}
                  </div>
                  <div
                    className={cn(
                      'ml-5 mt-1 text-xs',
                      isDark ? 'text-zinc-500' : 'text-zinc-400',
                    )}
                  >
                    {modeItem.description}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setModelMenuOpen((prev) => !prev)}
            className={cn(
              'flex items-center gap-1 rounded-lg px-2 py-1 text-xs transition-colors',
              isDark
                ? 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200'
                : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700',
            )}
          >
            <ChevronUp size={12} className={cn('transition-transform', !modelMenuOpen && 'rotate-180')} />
            <span className="max-w-[180px] truncate">
              {currentGroupName || displayModelName}
            </span>
          </button>

          {modelMenuOpen && (
            <div
              className={cn(
                'absolute bottom-full left-0 z-50 mb-1 w-64 overflow-hidden rounded-xl border shadow-xl',
                isDark ? 'border-zinc-700 bg-zinc-900' : 'border-zinc-200 bg-white',
              )}
            >
              <div
                className={cn(
                  'border-b px-3 py-2 text-xs font-medium',
                  isDark ? 'border-zinc-700 text-zinc-400' : 'border-zinc-200 text-zinc-500',
                )}
              >
                {t('chatInput.modelGroup')}
              </div>
              <div className="max-h-48 overflow-y-auto py-1">
                {groupNames.length === 0 ? (
                  <div
                    className={cn(
                      'px-3 py-3 text-center text-xs',
                      isDark ? 'text-zinc-500' : 'text-zinc-400',
                    )}
                  >
                    {t('chatInput.noModelGroups')}
                  </div>
                ) : (
                  groupNames.map((name) => {
                    const group = modelGroups[name];
                    const isSelected = name === currentGroupName;

                    return (
                      <button
                        key={name}
                        onClick={() => switchMutation.mutate(name)}
                        className={cn(
                          'flex w-full items-center gap-2 px-3 py-2 text-left transition-colors',
                          isSelected
                            ? isDark
                              ? 'bg-violet-500/20'
                              : 'bg-violet-50'
                            : isDark
                              ? 'hover:bg-zinc-800'
                              : 'hover:bg-zinc-50',
                        )}
                      >
                        <Sparkles
                          size={12}
                          className={cn(
                            isSelected
                              ? 'text-violet-500'
                              : isDark
                                ? 'text-zinc-500'
                                : 'text-zinc-400',
                          )}
                        />
                        <div className="min-w-0 flex-1">
                          <div
                            className={cn(
                              'truncate text-sm font-medium',
                              isDark ? 'text-zinc-200' : 'text-zinc-700',
                            )}
                          >
                            {name}
                          </div>
                          <div
                            className={cn(
                              'truncate text-xs',
                              isDark ? 'text-zinc-500' : 'text-zinc-400',
                            )}
                          >
                            {group.chat_model?.model || t('chatInput.unconfigured')}
                          </div>
                        </div>
                        {isSelected && <Check size={14} className="flex-shrink-0 text-violet-500" />}
                      </button>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
