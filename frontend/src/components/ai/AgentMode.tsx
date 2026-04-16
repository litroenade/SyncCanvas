import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types';
import { cn } from '../../lib/utils';
import {
  DIAGRAM_AGENT_COPY,
  DIAGRAM_ENTRY_COPY,
  getDiagramFamilyLabel,
  getDiagramQuickPrompts,
} from '../../lib/diagramRegistry';
import {
  Loader2,
  ChevronDown,
  ChevronRight,
  Bot,
  User,
  Clock,
  XCircle,
  Wrench,
  Sparkles,
  RefreshCw,
  AlertTriangle,
  GitPullRequestArrow,
  Archive,
  Scissors,
  WandSparkles,
  ShieldCheck,
} from 'lucide-react';
import { useAIStream } from '../../hooks/useAIStream';
import {
  getManagedDiagramStateLabel,
  getManagedDiagramStatusView,
} from '../../lib/managedDiagramStatus';
import { yjsManager, type BinaryFiles, type ExcalidrawElement } from '../../lib/yjs';
import { applyManagedPreviewToCanvas } from '../../lib/managedPreviewApply';
import {
  MANAGED_PREVIEW_APPLIED_EVENT,
  type ManagedPreviewDragPayload,
} from '../../lib/managedPreviewDrag';
import { resolveDiagramRequestTarget } from '../../lib/diagramRequestTarget';
import { ToolProgress, type ToolStep } from './ToolProgress';
import { ChatInput, type ConversationMode } from './ChatInput';
import { VirtualCanvas } from './VirtualCanvas';
import { MermaidCodePreview } from './MermaidCodePreview';
import {
  getConversationSessionKey,
  restoreConversationSession,
  stashConversationSession,
} from './conversationSession';
import { hydrateConversationMessages } from './conversationHistory';
import { extractMermaidCode } from './extractMermaidCode';
import { getAIStreamStatusView } from './streamStatus';
import { aiApi, type DiagramGenerationMode } from '../../services/api/ai';
import { roomsApi } from '../../services/api/rooms';
import { useModal } from '../common/Modal';
import type { DiagramBundle, ManagedDiagramTarget } from '../../types';
import { useI18n } from '../../i18n';
import './AgentMode.css';

interface AgentModeProps {
  roomId: string;
  isDark: boolean;
  onElementsCreated?: (elementIds: string[]) => void;
  mode: ConversationMode;
  onModeChange: (mode: ConversationMode) => void;
  onFirstMessage?: (message: string) => void;
  conversationId?: number | null;
  excalidrawAPI?: ExcalidrawImperativeAPI | null;
  diagramTarget?: ManagedDiagramTarget | null;
}

interface ChatMessage {
  id: string;
  requestId?: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  status?: 'thinking' | 'working' | 'completed' | 'error';
  thinkingTime?: number;
  steps?: ToolStep[];
  virtualElements?: Record<string, unknown>[];
  usedMode?: ConversationMode;
  addedToCanvas?: boolean;
  diagramBundle?: DiagramBundle;
  diagramFamily?: string;
  generationMode?: DiagramGenerationMode;
  managedScope?: string[];
  patchSummary?: string | null;
  unmanagedWarnings?: string[];
  sources?: Array<{ type: string; provider?: string; model?: string; role?: string }>;
  changeReasoning?: Array<{ step: string; explanation: string }>;
  affectedNodeIds?: string[];
  riskNotes?: string[];
}

export const AgentMode: React.FC<AgentModeProps> = ({
  roomId,
  isDark,
  onElementsCreated,
  mode,
  onModeChange,
  onFirstMessage,
  conversationId,
  excalidrawAPI,
  diagramTarget,
}) => {
  const { t, locale } = useI18n();
  type UpdateSceneArgs = Parameters<ExcalidrawImperativeAPI['updateScene']>[0];
  type ScrollToContentTarget = Parameters<ExcalidrawImperativeAPI['scrollToContent']>[0];
  type AddFilesArgs = Parameters<ExcalidrawImperativeAPI['addFiles']>[0];
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set());
  const [thinkingStartTime, setThinkingStartTime] = useState<number | null>(null);
  const [conflictStashAvailable, setConflictStashAvailable] = useState(false);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesRef = useRef<ChatMessage[]>([]);
  const inputRef = useRef('');
  const conversationSessionsRef = useRef(new Map<string, {
    messages: ChatMessage[];
    expandedMessageIds: string[];
    input: string;
  }>());
  const conversationKey = getConversationSessionKey(conversationId);
  const previousConversationKeyRef = useRef(conversationKey);
  const conflictStashKey = `ai-conflict-stash-${roomId}`;
  const { showAlert, showConfirm, showToast, ModalRenderer } = useModal();

  const {
    isConnected,
    isLoading,
    steps,
    response,
    error,
    transportError,
    requestId: streamRequestId,
    sendRequest,
    reset,
    elementsCreated,
    virtualElements,
    diagramBundle,
    diagramFamily,
    generationMode,
    managedScope,
    patchSummary,
    unmanagedWarnings,
    sources,
    changeReasoning,
    affectedNodeIds,
    riskNotes,
    lastCloseInfo,
    closeInterruptedRequest,
    roomVersion: streamRoomVersion,
    snapshotRequired,
  } = useAIStream({ roomId, autoConnect: true });

  const toolSteps: ToolStep[] = useMemo(() => {
    return steps.map((step, index) => ({
      stepNumber: index + 1,
      thought: step.thought,
      action: step.action || undefined,
      actionInput: step.action_input ?? undefined,
      observation: step.observation ?? undefined,
      success: step.success,
      latencyMs: step.latency_ms,
      status:
        step.success === false
          ? 'error'
          : step.observation
            ? 'done'
            : step.action
              ? 'running'
              : 'pending',
    }));
  }, [steps]);

  const diagramStatus = useMemo(
    () => getManagedDiagramStatusView(diagramTarget),
    [diagramTarget],
  );
  const quickPrompts = useMemo(() => getDiagramQuickPrompts(), [locale]);

  const streamStatus = useMemo(
    () =>
      getAIStreamStatusView({
        transportError,
        isConnected,
        lastCloseInfo,
        closeInterruptedRequest,
        roomVersion: streamRoomVersion,
        snapshotRequired,
      }),
    [
      transportError,
      isConnected,
      lastCloseInfo,
      closeInterruptedRequest,
      snapshotRequired,
      streamRoomVersion,
    ],
  );

  const refreshConflictStashState = useCallback(() => {
    setConflictStashAvailable(Boolean(localStorage.getItem(conflictStashKey)));
  }, [conflictStashKey]);

  useEffect(() => {
    refreshConflictStashState();
  }, [refreshConflictStashState]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    inputRef.current = input;
  }, [input]);

  useEffect(() => {
    const previousConversationKey = previousConversationKeyRef.current;
    if (previousConversationKey === conversationKey) {
      return;
    }

    stashConversationSession(conversationSessionsRef.current, previousConversationKey, {
      messages,
      expandedMessageIds: [...expandedMessages],
      input,
    });

    const restoredSession = restoreConversationSession(
      conversationSessionsRef.current,
      conversationKey,
    );
    previousConversationKeyRef.current = conversationKey;

    setMessages(restoredSession.messages);
    setExpandedMessages(new Set(restoredSession.expandedMessageIds));
    setInput(restoredSession.input);
    setThinkingStartTime(null);
    setIsHistoryLoading(false);
    reset();
  }, [conversationKey, expandedMessages, input, messages, reset]);

  useEffect(() => {
    if (conversationId == null) {
      setIsHistoryLoading(false);
      return;
    }

    if (conversationSessionsRef.current.has(conversationKey)) {
      setIsHistoryLoading(false);
      return;
    }

    let cancelled = false;
    setIsHistoryLoading(true);

    void aiApi.getConversationMessages(roomId, conversationId)
      .then((history) => {
        if (cancelled || previousConversationKeyRef.current !== conversationKey) {
          return;
        }
        if (messagesRef.current.length > 0 || inputRef.current.trim().length > 0) {
          return;
        }

        const hydratedMessages = hydrateConversationMessages(history.messages) as ChatMessage[];
        stashConversationSession(conversationSessionsRef.current, conversationKey, {
          messages: hydratedMessages,
          expandedMessageIds: [],
          input: '',
        });
        setMessages(hydratedMessages);
        setExpandedMessages(new Set());
      })
      .catch((historyError) => {
        if (!cancelled) {
          console.error('[AgentMode] failed to load conversation history:', historyError);
          showToast(t('diagramAgent.historyLoadFailed'), 'error');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsHistoryLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [conversationId, conversationKey, roomId, showToast, t]);

  const handleStashConflictDraft = useCallback(() => {
    const elements = yjsManager.getElements();
    const payload = {
      savedAt: Date.now(),
      roomId,
      elements,
    };
    localStorage.setItem(conflictStashKey, JSON.stringify(payload));
    refreshConflictStashState();
    showToast(DIAGRAM_AGENT_COPY.stash.saved, 'success');
  }, [conflictStashKey, roomId, refreshConflictStashState, showToast]);

  const handleRestoreConflictDraft = useCallback(() => {
    if (!excalidrawAPI) {
      showToast(DIAGRAM_AGENT_COPY.stash.canvasUnavailable, 'warning');
      return;
    }

    const raw = localStorage.getItem(conflictStashKey);
    if (!raw) {
      showToast(DIAGRAM_AGENT_COPY.stash.missing, 'warning');
      return;
    }

    try {
      const parsed = JSON.parse(raw) as {
        roomId: string;
        elements: ExcalidrawElement[];
      };
      if (parsed.roomId !== roomId || !Array.isArray(parsed.elements)) {
        throw new Error(DIAGRAM_AGENT_COPY.stash.invalidFormat);
      }
      excalidrawAPI.updateScene({
        elements: parsed.elements as unknown as UpdateSceneArgs['elements'],
      });
      showToast(DIAGRAM_AGENT_COPY.stash.restored, 'success');
    } catch (error) {
      console.error('[AgentMode] restore stash failed:', error);
      showToast(DIAGRAM_AGENT_COPY.stash.restoreFailed, 'error');
    }
  }, [conflictStashKey, excalidrawAPI, roomId, showToast]);

  const handleReplayWithHead = useCallback(() => {
    if (!roomId) return;

    showConfirm(
      DIAGRAM_AGENT_COPY.replay.confirm,
      async () => {
        const roomHistory = await roomsApi.getHistory(roomId);
        if (!roomHistory.head_commit_id) {
          throw new Error(DIAGRAM_AGENT_COPY.replay.missingHead);
        }
        await roomsApi.checkoutCommit(roomId, roomHistory.head_commit_id);
        showToast(DIAGRAM_AGENT_COPY.replay.success, 'success');
        window.setTimeout(() => window.location.reload(), 900);
      },
      { title: DIAGRAM_AGENT_COPY.replay.title, type: 'warning' },
    );
  }, [roomId, showConfirm, showToast]);

  const handleManualMergeGuide = useCallback(() => {
    showAlert(
      DIAGRAM_AGENT_COPY.conflictPanel.manualMergeGuideMessage,
      { title: DIAGRAM_AGENT_COPY.conflictPanel.manualMergeGuideTitle, type: 'info' },
    );
  }, [showAlert]);

    const handleRebuildDiagram = useCallback(async () => {
    if (!diagramTarget?.diagramId) return;

    try {
      const rebuilt = await roomsApi.rebuildDiagram(roomId, diagramTarget.diagramId);
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-rebuild-${Date.now()}`,
          role: 'assistant',
          content: DIAGRAM_AGENT_COPY.rebuild.success,
          timestamp: Date.now(),
          status: 'completed',
          diagramBundle: rebuilt,
          diagramFamily: rebuilt.summary.family,
          managedScope: rebuilt.state.managedScope,
          patchSummary: rebuilt.state.lastPatchSummary,
          unmanagedWarnings: rebuilt.state.warnings,
        },
      ]);
    } catch (rebuildError) {
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-rebuild-${Date.now()}`,
          role: 'assistant',
          content:
            rebuildError instanceof Error
              ? rebuildError.message
              : DIAGRAM_AGENT_COPY.rebuild.failure,
          timestamp: Date.now(),
          status: 'error',
        },
      ]);
    }
  }, [diagramTarget?.diagramId, roomId]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const toggleMessage = useCallback((messageId: string) => {
    setExpandedMessages((prev) => {
      const next = new Set(prev);
      if (next.has(messageId)) {
        next.delete(messageId);
      } else {
        next.add(messageId);
      }
      return next;
    });
  }, []);

  const updateAssistantMessageByRequest = useCallback((
    requestId: string | null,
    updater: (message: ChatMessage) => ChatMessage,
  ) => {
    if (!requestId) {
      return;
    }
    setMessages((prev) =>
      prev.map((message) =>
        message.role === 'assistant' && message.requestId === requestId
          ? updater(message)
          : message,
      ),
    );
  }, []);

  useEffect(() => {
    if (isLoading && steps.length > 0 && streamRequestId) {
      updateAssistantMessageByRequest(streamRequestId, (message) => (
        message.status === 'completed'
          ? message
          : { ...message, steps: toolSteps, status: 'working' as const }
      ));
    }
  }, [steps, toolSteps, isLoading, streamRequestId, updateAssistantMessageByRequest]);

  useEffect(() => {
    if (response && !isLoading && streamRequestId) {
      const thinkingTime = thinkingStartTime
        ? Math.floor((Date.now() - thinkingStartTime) / 1000)
        : 0;

      updateAssistantMessageByRequest(streamRequestId, (message) => ({
        ...message,
        status: 'completed' as const,
        content: response,
        thinkingTime,
        virtualElements:
          virtualElements && virtualElements.length > 0
            ? virtualElements
            : message.usedMode === 'planning' &&
                diagramBundle?.previewElements &&
                diagramBundle.previewElements.length > 0
              ? diagramBundle.previewElements
              : undefined,
        diagramBundle: diagramBundle || undefined,
        diagramFamily: diagramFamily || undefined,
        generationMode: generationMode || undefined,
        managedScope:
          managedScope && managedScope.length > 0 ? managedScope : undefined,
        patchSummary: patchSummary || undefined,
        unmanagedWarnings:
          unmanagedWarnings && unmanagedWarnings.length > 0
            ? unmanagedWarnings
            : undefined,
        sources: sources && sources.length > 0 ? sources : undefined,
        changeReasoning: changeReasoning && changeReasoning.length > 0 ? changeReasoning : undefined,
        affectedNodeIds: affectedNodeIds && affectedNodeIds.length > 0 ? affectedNodeIds : undefined,
        riskNotes: riskNotes && riskNotes.length > 0 ? riskNotes : undefined,
      }));
      setThinkingStartTime(null);
    }
  }, [
    response,
    isLoading,
    streamRequestId,
    thinkingStartTime,
    virtualElements,
    diagramBundle,
    diagramFamily,
    generationMode,
    managedScope,
    patchSummary,
    unmanagedWarnings,
    sources,
    changeReasoning,
    affectedNodeIds,
    riskNotes,
    updateAssistantMessageByRequest,
  ]);

  useEffect(() => {
    if (error && streamRequestId) {
      updateAssistantMessageByRequest(
        streamRequestId,
        (message) => ({ ...message, status: 'error' as const, content: error }),
      );
      setThinkingStartTime(null);
    }
  }, [error, streamRequestId, updateAssistantMessageByRequest]);

  useEffect(() => {
    if (elementsCreated?.length > 0 && onElementsCreated) {
      onElementsCreated(elementsCreated);
    }
  }, [elementsCreated, onElementsCreated]);

  const markMessageAddedToCanvas = useCallback((messageId: string) => {
    setMessages((prev) =>
      prev.map((item) =>
        item.id === messageId
          ? { ...item, addedToCanvas: true }
          : item,
      ),
    );
  }, []);

  useEffect(() => {
    const handleManagedPreviewApplied = (event: Event) => {
      const detail = (event as CustomEvent<{ messageId?: string }>).detail;
      if (typeof detail?.messageId !== 'string' || detail.messageId.length === 0) {
        return;
      }
      markMessageAddedToCanvas(detail.messageId);
    };

    window.addEventListener(
      MANAGED_PREVIEW_APPLIED_EVENT,
      handleManagedPreviewApplied as EventListener,
    );
    return () => {
      window.removeEventListener(
        MANAGED_PREVIEW_APPLIED_EVENT,
        handleManagedPreviewApplied as EventListener,
      );
    };
  }, [markMessageAddedToCanvas]);

  const applyMermaidToCanvas = useCallback((
    messageId: string,
    elements: ExcalidrawElement[],
    files: BinaryFiles = {},
  ) => {
    if (!excalidrawAPI) {
      console.warn('Excalidraw API is not available.');
      return;
    }

    if (Object.keys(files).length > 0) {
      excalidrawAPI.addFiles(Object.values(files) as AddFilesArgs);
    }

    const existingElements = excalidrawAPI.getSceneElements();
    excalidrawAPI.updateScene({
      elements: [...existingElements, ...elements] as UpdateSceneArgs['elements'],
    });
    excalidrawAPI.scrollToContent(elements as unknown as ScrollToContentTarget, {
      fitToViewport: true,
      animate: true,
      duration: 300,
    });
    markMessageAddedToCanvas(messageId);
  }, [excalidrawAPI, markMessageAddedToCanvas]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    if (diagramTarget?.mode === 'conflict' || diagramTarget?.canEdit === false) {
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-conflict-${Date.now()}`,
          role: 'assistant',
          content: diagramStatus.reason || DIAGRAM_AGENT_COPY.blockedAssistantFallback,
          timestamp: Date.now(),
          status: 'error',
        },
      ]);
      return;
    }

    if (messages.length === 0 && onFirstMessage) {
      onFirstMessage(text);
    }

    const directMermaidCode = extractMermaidCode(text);
    if (directMermaidCode) {
      const timestamp = Date.now();
      const userMessage: ChatMessage = {
        id: `user-${timestamp}`,
        role: 'user',
        content: text,
        timestamp,
        usedMode: mode,
      };

      const assistantMessage: ChatMessage = {
        id: `assistant-${timestamp}`,
        role: 'assistant',
        content: `\`\`\`mermaid\n${directMermaidCode}\n\`\`\``,
        timestamp,
        status: 'completed',
        usedMode: 'mermaid',
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setInput('');
      setThinkingStartTime(null);
      reset();
      return;
    }

    if (mode === 'mermaid') {
      const timestamp = Date.now();
      const userMessage: ChatMessage = {
        id: `user-${timestamp}`,
        role: 'user',
        content: text,
        timestamp,
        usedMode: mode,
      };
      const assistantMessageId = `assistant-${timestamp}`;
      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp,
        status: 'thinking',
        usedMode: mode,
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setExpandedMessages((prev) => new Set([...prev, assistantMessageId]));
      setInput('');
      setThinkingStartTime(timestamp);
      reset();

      try {
        const mermaidResult = await aiApi.generateMermaid(text, {
          roomId,
          conversationId,
        });
        const normalizedCode = extractMermaidCode(mermaidResult.code) ?? mermaidResult.code.trim();
        const thinkingTime = Math.floor((Date.now() - timestamp) / 1000);

        setMessages((prev) =>
          prev.map((item) =>
            item.id === assistantMessageId
              ? {
                ...item,
                status: 'completed' as const,
                content: `\`\`\`mermaid\n${normalizedCode}\n\`\`\``,
                thinkingTime,
                usedMode: 'mermaid',
              }
              : item,
          ),
        );
      } catch (mermaidError) {
        const message =
          mermaidError instanceof Error
            ? mermaidError.message
            : t('diagramAgent.mermaidGenerationFailed');
        setMessages((prev) =>
          prev.map((item) =>
            item.id === assistantMessageId
              ? { ...item, status: 'error' as const, content: message }
              : item,
          ),
        );
      } finally {
        setThinkingStartTime(null);
      }

      return;
    }

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: Date.now(),
      usedMode: mode,
    };

    const requestId = window?.crypto?.randomUUID
      ? window.crypto.randomUUID()
      : `agent-${Date.now()}-${Math.random().toString(16).slice(2)}`;

    const assistantMessage: ChatMessage = {
      id: `assistant-${Date.now()}`,
      requestId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      status: 'thinking',
      usedMode: mode,
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setExpandedMessages((prev) => new Set([...prev, assistantMessage.id]));
    setInput('');
    setThinkingStartTime(Date.now());
    reset();

    const requestTarget = resolveDiagramRequestTarget(mode, diagramTarget);

    await sendRequest(text, {
      theme: isDark ? 'dark' : 'light',
      mode,
      conversation_id: conversationId ?? undefined,
      target_diagram_id: requestTarget.targetDiagramId,
      target_semantic_id: requestTarget.targetSemanticId,
      edit_scope: requestTarget.editScope,
      request_id: requestId,
      idempotency_key: requestId,
      timeout_ms: 120000,
      explain: true,
    });
  }, [
    input,
    isLoading,
    diagramTarget,
    diagramStatus.reason,
    messages.length,
    onFirstMessage,
    reset,
    sendRequest,
    isDark,
    mode,
    conversationId,
    t,
  ]);

  const getGenerationModeLabel = (
    currentGenerationMode?: DiagramGenerationMode,
  ): string | null => {
    switch (currentGenerationMode) {
      case 'llm':
        return t('diagramAgent.generationMode.llm');
      case 'deterministic_seed':
        return t('diagramAgent.generationMode.deterministicSeed');
      case 'heuristic_patch':
        return t('diagramAgent.generationMode.heuristicPatch');
      default:
        return null;
    }
  };

  const getReadableModelLabel = (message: ChatMessage): string | null => {
    if (!message.sources || message.sources.length === 0) {
      return null;
    }

    const source = message.sources.find((item) => item.type === 'llm') ?? message.sources[0];
    const parts = [source.provider, source.model].filter(
      (value): value is string => typeof value === 'string' && value.trim().length > 0,
    );

    return parts.length > 0 ? parts.join(' / ') : null;
  };

  const getReadableDiffSummary = (
    message: ChatMessage,
  ): { summary: string | null; note: string | null } => {
    switch (message.generationMode) {
      case 'deterministic_seed':
        return {
          summary: t('diagramAgent.diffExplanation.summary.deterministicSeed'),
          note: t('diagramAgent.diffExplanation.note.deterministicSeed'),
        };
      case 'heuristic_patch':
        return {
          summary: t('diagramAgent.diffExplanation.summary.heuristicPatch'),
          note: t('diagramAgent.diffExplanation.note.heuristicPatch'),
        };
      case 'llm':
        return {
          summary: t('diagramAgent.diffExplanation.summary.llm'),
          note: null,
        };
      default:
        return {
          summary: null,
          note: null,
        };
    }
  };

const renderDiagramSummary = (message: ChatMessage) => {
  if (!message.diagramBundle) return null;

  const bundle = message.diagramBundle;
  const managedStateLabel = getManagedDiagramStateLabel(bundle.state.managedState)
    || bundle.state.managedState;
  const generationModeLabel = getGenerationModeLabel(message.generationMode);

  return (
    <div
      className={cn(
        'mt-2 rounded-xl border p-3 text-xs space-y-1.5',
        isDark
          ? 'border-zinc-700 bg-zinc-800/40 text-zinc-300'
          : 'border-zinc-200 bg-zinc-50 text-zinc-600',
      )}
    >
      <div className="font-semibold">
        {`${DIAGRAM_AGENT_COPY.summary.diagramLabel}: ${getDiagramFamilyLabel(message.diagramFamily || bundle.summary.family)}`}
        {' · '}
        {`${DIAGRAM_AGENT_COPY.summary.componentsLabel}: ${bundle.summary.componentCount}`}
        {' · '}
        {`${DIAGRAM_AGENT_COPY.summary.connectorsLabel}: ${bundle.summary.connectorCount}`}
      </div>
      <div>
        {`${DIAGRAM_AGENT_COPY.summary.titleLabel}: ${bundle.summary.title}`}
        {' · '}
        {`${DIAGRAM_AGENT_COPY.summary.managedLabel}: ${managedStateLabel}`}
      </div>
      {generationModeLabel && (
        <div>{`${DIAGRAM_AGENT_COPY.summary.generationModeLabel}: ${generationModeLabel}`}</div>
      )}
      {message.managedScope && message.managedScope.length > 0 && (
        <div>{`${DIAGRAM_AGENT_COPY.summary.scopeLabel}: ${message.managedScope.join(', ')}`}</div>
      )}
      {message.patchSummary && <div>{`${DIAGRAM_AGENT_COPY.summary.patchLabel}: ${message.patchSummary}`}</div>}
      {message.unmanagedWarnings && message.unmanagedWarnings.length > 0 && (
        <div className="flex items-start gap-1.5">
          <AlertTriangle size={12} className="mt-0.5 flex-shrink-0 text-amber-500" />
          <span>{`${DIAGRAM_AGENT_COPY.summary.warningsLabel}: ${message.unmanagedWarnings.join(' | ')}`}</span>
        </div>
      )}
    </div>
  );
  };

  const renderConflictAssistPanel = () => {
    if (diagramStatus.severity !== 'blocked') {
      return null;
    }

    return (
      <div
        className={cn(
          'mt-2 rounded-xl border p-3 text-xs space-y-2',
          isDark
            ? 'border-amber-500/30 bg-amber-900/20 text-amber-100'
            : 'border-amber-200 bg-amber-50 text-amber-900',
        )}
      >
        <div className="font-semibold">{DIAGRAM_AGENT_COPY.conflictPanel.headline}</div>
        <div className="text-xs">
          {diagramStatus.reason || DIAGRAM_AGENT_COPY.conflictPanel.descriptionFallback}
        </div>
        <div className="text-xs">{DIAGRAM_AGENT_COPY.conflictPanel.actionsLabel}</div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleStashConflictDraft}
            className={cn(
              'inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] transition-colors',
              isDark
                ? 'bg-zinc-800 text-zinc-200 hover:bg-zinc-700'
                : 'border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50',
            )}
          >
            <Archive size={12} />
            <span>{DIAGRAM_AGENT_COPY.conflictPanel.stashLabel}</span>
          </button>
          <button
            type="button"
            onClick={handleReplayWithHead}
            className={cn(
              'inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] transition-colors',
              isDark
                ? 'bg-sky-800 text-sky-100 hover:bg-sky-700'
                : 'bg-sky-50 text-sky-700 border border-sky-200 hover:bg-sky-100',
            )}
          >
            <GitPullRequestArrow size={12} />
            <span>{DIAGRAM_AGENT_COPY.conflictPanel.replayBaselineLabel}</span>
          </button>
          <button
            type="button"
            onClick={handleManualMergeGuide}
            className={cn(
              'inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] transition-colors',
              isDark
                ? 'bg-purple-800 text-purple-100 hover:bg-purple-700'
                : 'bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100',
            )}
          >
            <WandSparkles size={12} />
            <span>{DIAGRAM_AGENT_COPY.conflictPanel.manualMergeLabel}</span>
          </button>
        </div>
        {conflictStashAvailable && (
          <button
            type="button"
            onClick={handleRestoreConflictDraft}
            className={cn(
              'inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] transition-colors',
              isDark
                ? 'bg-green-800 text-green-100 hover:bg-green-700'
                : 'bg-green-50 text-green-700 border border-green-200 hover:bg-green-100',
            )}
          >
            <Scissors size={12} />
            <span>{DIAGRAM_AGENT_COPY.conflictPanel.restoreDraftLabel}</span>
          </button>
        )}
      </div>
    );
  };

  const renderAIDiffSummary = (message: ChatMessage) => {
    const generationModeLabel = getGenerationModeLabel(message.generationMode);
    const modelLabel = getReadableModelLabel(message);
    const { summary, note } = getReadableDiffSummary(message);
    if (
      !generationModeLabel
      && !modelLabel
      && !summary
      && !note
    ) {
      return null;
    }

    return (
      <div
        className={cn(
          'mt-3 rounded-xl border p-3 text-xs space-y-2',
          isDark ? 'border-violet-500/20 bg-violet-900/20 text-violet-100' : 'border-violet-200 bg-violet-50 text-violet-900',
        )}
      >
        <div className="flex items-center gap-2 font-semibold">
          <ShieldCheck size={12} />
          <span>{t('diagramAgent.diffExplanation.title')}</span>
        </div>

        {generationModeLabel && (
          <div className="space-y-1">
            <div>{t('diagramAgent.diffExplanation.generationMode')}</div>
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={cn(
                  'rounded-full px-2 py-0.5 text-[11px] font-medium',
                  message.generationMode === 'llm'
                    ? isDark
                      ? 'bg-emerald-500/15 text-emerald-100'
                      : 'bg-emerald-100 text-emerald-800'
                    : isDark
                      ? 'bg-amber-500/15 text-amber-100'
                      : 'bg-amber-100 text-amber-800',
                )}
              >
                {generationModeLabel}
              </span>
            </div>
          </div>
        )}

        {modelLabel && (
          <div className="space-y-1">
            <div>{t('diagramAgent.diffExplanation.model')}</div>
            <div>{modelLabel}</div>
          </div>
        )}

        {summary && (
          <div className="space-y-1">
            <div>{t('diagramAgent.diffExplanation.summary')}</div>
            <div>{summary}</div>
          </div>
        )}

        {note && (
          <div className="rounded border border-red-200 bg-red-50/70 p-2 text-red-700 dark:border-red-900/40 dark:bg-red-900/20 dark:text-red-100">
            <div>{note}</div>
          </div>
        )}
      </div>
    );
  };

  const renderMessage = (message: ChatMessage) => {
    const isUser = message.role === 'user';
    const isExpanded = expandedMessages.has(message.id);
    const hasSteps = !!message.steps && message.steps.length > 0;

    return (
      <div
        key={message.id}
        className={cn('mb-4 flex gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}
      >
        <div
          className={cn(
            'flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg',
            isUser
              ? 'bg-gradient-to-br from-blue-500 to-cyan-500'
              : 'bg-gradient-to-br from-violet-500 to-purple-600',
          )}
        >
          {isUser ? <User size={16} className="text-white" /> : <Bot size={16} className="text-white" />}
        </div>

        <div className={cn('min-w-0 flex-1', isUser ? 'text-right' : 'text-left')}>
          <div
            className={cn(
              'inline-block max-w-[85%] rounded-2xl px-4 py-3',
              isUser
                ? isDark
                  ? 'bg-blue-600 text-white'
                  : 'bg-blue-500 text-white'
                : isDark
                  ? 'bg-zinc-800 text-zinc-100'
                  : 'border border-zinc-200 bg-white text-zinc-800',
            )}
          >
            {!isUser && message.status && message.status !== 'completed' && (
              <div className="mb-2 flex items-center gap-2">
                {message.status === 'thinking' && (
                  <>
                    <Sparkles size={14} className="animate-pulse text-violet-400" />
                    <span className="text-xs text-violet-400">{t('diagramAgent.status.thinking')}</span>
                  </>
                )}
                {message.status === 'working' && (
                  <>
                    <Loader2 size={14} className="animate-spin text-blue-400" />
                    <span className="text-xs text-blue-400">{t('diagramAgent.status.working')}</span>
                  </>
                )}
                {message.status === 'error' && (
                  <>
                    <XCircle size={14} className="text-red-400" />
                    <span className="text-xs text-red-400">{t('diagramAgent.status.failed')}</span>
                  </>
                )}
              </div>
            )}

            <div
              className={cn(
                'whitespace-pre-wrap break-words text-sm leading-relaxed',
                !isUser && !message.content && 'min-h-[20px]',
              )}
            >
              {message.content || (message.status === 'thinking' ? '...' : '')}
            </div>

            {!isUser && message.thinkingTime && message.status === 'completed' && (
              <div
                className={cn(
                  'mt-2 flex items-center gap-1 text-xs',
                  isDark ? 'text-zinc-500' : 'text-zinc-400',
                )}
              >
                <Clock size={12} />
                <span>{message.thinkingTime}s</span>
              </div>
            )}
          </div>

          {!isUser && hasSteps && (
            <div className="mt-2">
              <button
                onClick={() => toggleMessage(message.id)}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs transition-colors',
                  isDark
                    ? 'bg-zinc-800/50 text-zinc-400 hover:bg-zinc-700/50'
                    : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200',
                )}
              >
                <Wrench size={12} />
                <span>{t('diagramAgent.toolCalls', { count: message.steps!.length })}</span>
                {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              </button>

              {isExpanded && (
                <div
                  className={cn(
                    'mt-2 rounded-xl p-3',
                    isDark ? 'bg-zinc-800/30' : 'bg-zinc-50',
                  )}
                >
                  <ToolProgress steps={message.steps!} className={isDark ? 'dark' : ''} />
                </div>
              )}
            </div>
          )}

          {renderDiagramSummary(message)}
          {renderAIDiffSummary(message)}

          {!isUser && message.virtualElements && message.virtualElements.length > 0 && (
            <div className="mt-3">
              {(() => {
                const previewFiles = (message.diagramBundle?.previewFiles ?? {}) as BinaryFiles;
                const dragPayload: ManagedPreviewDragPayload = {
                  messageId: message.id,
                  elements: JSON.parse(JSON.stringify(message.virtualElements)) as ExcalidrawElement[],
                  files: previewFiles,
                  diagramBundle: message.diagramBundle,
                };

                return (
                  <VirtualCanvas
                    key={`virtual-${message.id}`}
                    elements={message.virtualElements as ExcalidrawElement[]}
                    files={previewFiles}
                    isDark={isDark}
                    minHeight={150}
                    maxHeight={300}
                    addedToCanvas={message.addedToCanvas}
                    dragPayload={dragPayload}
                    onAddToCanvas={(elementsToAdd) => {
                      if (!excalidrawAPI) {
                        console.warn('Excalidraw API is not available.');
                        return;
                      }

                      void applyManagedPreviewToCanvas({
                        excalidrawAPI,
                        elementsToAdd,
                        diagramBundle: message.diagramBundle,
                        files: previewFiles,
                        placement: 'viewport-cascade',
                      });
                      markMessageAddedToCanvas(message.id);
                    }}
                  />
                );
              })()}
            </div>
          )}

          {!isUser && message.status === 'completed' && (() => {
            const mermaidCode = extractMermaidCode(message.content);
            if (!mermaidCode) return null;
            return (
              <MermaidCodePreview
                code={mermaidCode}
                isDark={isDark}
                addedToCanvas={message.addedToCanvas}
                onAddToCanvas={(elements, files) => applyMermaidToCanvas(message.id, elements, files)}
              />
            );
          })()}
        </div>
      </div>
    );
  };

  return (
    <div className="agent-mode flex h-full flex-col">
      <div
        className={cn(
          'border-b px-4 py-3',
          diagramStatus.severity === 'blocked'
            ? isDark
              ? 'border-amber-500/30 bg-amber-500/10 text-amber-100'
              : 'border-amber-200 bg-amber-50 text-amber-900'
            : diagramStatus.severity === 'warning'
              ? isDark
                ? 'border-orange-500/20 bg-orange-500/10 text-orange-100'
                : 'border-orange-200 bg-orange-50 text-orange-900'
              : isDark
                ? 'border-zinc-800 bg-zinc-900/80 text-zinc-100'
                : 'border-zinc-200 bg-zinc-50 text-zinc-800',
        )}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              {diagramStatus.severity !== 'normal' && <AlertTriangle size={14} className="flex-shrink-0" />}
              <div className="font-semibold">{diagramStatus.headline}</div>
              {diagramStatus.stateLabel && (
                <span
                  className={cn(
                    'rounded-full px-2 py-0.5 text-[11px] font-medium',
                    diagramStatus.severity === 'warning'
                      ? isDark
                        ? 'bg-orange-500/15 text-orange-200'
                        : 'bg-orange-100 text-orange-700'
                      : isDark
                        ? 'bg-violet-500/15 text-violet-200'
                        : 'bg-violet-100 text-violet-700',
                  )}
                >
                  {diagramStatus.stateLabel}
                </span>
              )}
            </div>
            <div className={cn('mt-1 text-xs', isDark ? 'text-zinc-400' : 'text-zinc-600')}>
              {diagramStatus.description}
            </div>
            {diagramStatus.metaItems.length > 0 && (
              <div
                className={cn(
                  'mt-2 flex flex-wrap gap-1.5 text-[11px]',
                  isDark ? 'text-zinc-300' : 'text-zinc-700',
                )}
              >
                {diagramStatus.metaItems.map((item) => (
                  <span
                    key={item}
                    className={cn(
                      'rounded-full px-2 py-0.5',
                      isDark ? 'bg-zinc-800/80 text-zinc-300' : 'bg-white text-zinc-700',
                    )}
                  >
                    {item}
                  </span>
                ))}
              </div>
            )}
            {diagramStatus.reason && (
              <div
                className={cn(
                  'mt-2 text-xs',
                  diagramStatus.severity === 'blocked'
                    ? isDark
                      ? 'text-red-300'
                      : 'text-red-700'
                    : isDark
                      ? 'text-zinc-400'
                      : 'text-zinc-600',
                )}
              >
                {diagramStatus.reason}
              </div>
            )}
            {diagramStatus.warningSummary && (
              <div
                className={cn(
                  'mt-2 text-xs font-medium',
                  isDark ? 'text-orange-200' : 'text-orange-700',
                )}
              >
                {diagramStatus.warningSummary}
              </div>
            )}
            {diagramStatus.warnings.length > 0 && (
              <div className="mt-1 space-y-1">
                {diagramStatus.warnings.slice(0, 2).map((warning) => (
                  <div
                    key={warning}
                    className={cn(
                      'text-xs',
                      isDark ? 'text-orange-200/90' : 'text-orange-800',
                    )}
                  >
                    {warning}
                  </div>
                ))}
              </div>
            )}
            {renderConflictAssistPanel()}
          </div>
          {diagramStatus.showRebuild && diagramTarget?.diagramId && (
            <button
              type="button"
              onClick={handleRebuildDiagram}
              className={cn(
                'inline-flex flex-shrink-0 items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs transition-colors',
                isDark
                  ? 'bg-zinc-800 text-zinc-200 hover:bg-zinc-700'
                  : 'border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-100',
              )}
            >
              <RefreshCw size={12} />
              <span>
                {diagramStatus.severity === 'warning'
                  ? DIAGRAM_AGENT_COPY.rebuild.warningActionLabel
                  : DIAGRAM_AGENT_COPY.rebuild.normalActionLabel}
              </span>
            </button>
          )}
        </div>
      </div>

      <div
        className={cn(
          'border-b px-4 py-2.5',
          streamStatus.tone === 'warning'
            ? isDark
              ? 'border-amber-500/20 bg-amber-500/5 text-amber-100'
              : 'border-amber-200 bg-amber-50/70 text-amber-900'
            : streamStatus.tone === 'normal'
              ? isDark
                ? 'border-emerald-500/20 bg-emerald-500/5 text-emerald-100'
                : 'border-emerald-200 bg-emerald-50 text-emerald-900'
              : isDark
                ? 'border-zinc-800 bg-zinc-950/80 text-zinc-300'
                : 'border-zinc-200 bg-white text-zinc-700',
        )}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              {streamStatus.tone === 'warning' ? (
                <AlertTriangle size={14} className="flex-shrink-0" />
              ) : (
                <ShieldCheck size={14} className="flex-shrink-0" />
              )}
              <div className="text-sm font-medium">{streamStatus.headline}</div>
            </div>
            <div className={cn('mt-1 text-xs', isDark ? 'text-zinc-400' : 'text-zinc-600')}>
              {streamStatus.description}
            </div>
            {streamStatus.detail && (
              <div
                className={cn(
                  'mt-1 text-[11px]',
                  streamStatus.tone === 'warning'
                    ? isDark
                      ? 'text-amber-200'
                      : 'text-amber-800'
                    : isDark
                      ? 'text-zinc-500'
                      : 'text-zinc-500',
                )}
              >
                {streamStatus.detail}
              </div>
            )}
            {streamStatus.badges.length > 0 && (
              <div
                className={cn(
                  'mt-2 flex flex-wrap gap-1.5 text-[11px]',
                  isDark ? 'text-zinc-300' : 'text-zinc-700',
                )}
              >
                {streamStatus.badges.map((badge) => (
                  <span
                    key={badge}
                    className={cn(
                      'rounded-full px-2 py-0.5',
                      streamStatus.tone === 'warning'
                        ? isDark
                          ? 'bg-amber-500/10 text-amber-100'
                          : 'bg-amber-100 text-amber-800'
                        : streamStatus.tone === 'normal'
                          ? isDark
                            ? 'bg-emerald-500/10 text-emerald-100'
                            : 'bg-emerald-100 text-emerald-800'
                          : isDark
                            ? 'bg-zinc-800 text-zinc-300'
                            : 'bg-zinc-100 text-zinc-700',
                    )}
                  >
                    {badge}
                  </span>
                ))}
              </div>
            )}
          </div>
          {streamStatus.showReplay && (
            <button
              type="button"
              onClick={handleReplayWithHead}
              className={cn(
                'inline-flex flex-shrink-0 items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs transition-colors',
                isDark
                  ? 'bg-zinc-800 text-zinc-200 hover:bg-zinc-700'
                  : 'border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-100',
              )}
            >
              <RefreshCw size={12} />
              <span>{DIAGRAM_AGENT_COPY.replay.buttonLabel}</span>
            </button>
          )}
        </div>
      </div>

      <div
        className={cn(
          'flex-1 overflow-y-auto p-4',
          messages.length === 0 && !isHistoryLoading && 'flex items-center justify-center',
        )}
      >
        {isHistoryLoading ? (
          <div className="flex h-full items-center justify-center">
            <div className="flex items-center gap-2 text-sm text-zinc-500">
              <Loader2 size={16} className="animate-spin" />
              <span>{t('diagramAgent.loadingConversation')}</span>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="max-w-sm px-4 py-8 text-center">
            <div
              className={cn(
                'mb-4 inline-flex h-16 w-16 items-center justify-center rounded-2xl border',
                'bg-gradient-to-br from-violet-500/20 to-purple-600/20',
                isDark ? 'border-violet-500/20' : 'border-violet-200',
              )}
            >
              <Sparkles size={32} className="text-violet-500" />
            </div>
            <h2
              className={cn(
                'mb-2 text-lg font-semibold',
                isDark ? 'text-zinc-100' : 'text-zinc-900',
              )}
            >
              {DIAGRAM_ENTRY_COPY.emptyStateTitle}
            </h2>
            <p className={cn('text-sm', isDark ? 'text-zinc-400' : 'text-zinc-500')}>
              {DIAGRAM_ENTRY_COPY.emptyStateDescription}
            </p>

            <div className="mt-6 space-y-2">
              {quickPrompts.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => setInput(prompt)}
                  disabled={isLoading}
                  className={cn(
                    'w-full rounded-xl border px-4 py-2.5 text-left text-sm transition-all',
                    isDark
                      ? 'border-zinc-700 bg-zinc-800/50 text-zinc-300 hover:bg-zinc-700/50'
                      : 'border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50',
                    isLoading && 'cursor-not-allowed opacity-50',
                  )}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map(renderMessage)}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      <ChatInput
        isDark={isDark}
        input={input}
        setInput={setInput}
        isLoading={isLoading}
        onSend={handleSend}
        mode={mode}
        onModeChange={onModeChange}
      />
      <ModalRenderer />
    </div>
  );
};




