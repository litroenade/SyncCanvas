import React, { useCallback, useEffect, useState } from 'react';
import {
  Check,
  ChevronRight,
  Clock,
  Copy,
  GitBranch,
  MessageSquare,
  RefreshCw,
  RotateCcw,
  Save,
  Shapes,
  ScanSearch,
  GitCompare,
  User,
} from 'lucide-react';

import { cn } from '../../lib/utils';
import { getDiagramFamilyLabel } from '../../lib/diagramRegistry';
import { getManagedDiagramStateLabel } from '../../lib/managedDiagramStatus';
import { useI18n } from '../../i18n';
import { getRequestErrorMessage } from '../../services/api/axios';
import { useThemeStore } from '../../stores/useThemeStore';
import {
  roomsApi,
  type CommitDetailResponse,
  type CommitInfo,
  type CreateCommitRequest,
  type HistoryResponse,
  type CommitDiffResponse,
} from '../../services/api/rooms';
import { useModal } from '../common/Modal';
import { yjsManager } from '../../lib/yjs';
import { CollabEventsPanel } from './CollabEventsPanel';

interface HistoryPanelProps {
  roomId: string;
}

type HistoryView = 'versions' | 'events';

const formatSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const formatSignedSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  return `${bytes > 0 ? '+' : '-'}${formatSize(Math.abs(bytes))}`;
};

const summarizeDetail = (detail: CommitDetailResponse) => {
  const familySummary = Object.entries(detail.diagram_families)
    .map(([family, count]) => `${getDiagramFamilyLabel(family)}: ${count}`)
    .join(', ');
  const managedSummary = Object.entries(detail.managed_states)
    .map(([state, count]) => {
      const label = getManagedDiagramStateLabel(
        state as Parameters<typeof getManagedDiagramStateLabel>[0],
      ) || state;
      return `${label}: ${count}`;
    })
    .join(', ');

  return { familySummary, managedSummary };
};

export const HistoryPanel: React.FC<HistoryPanelProps> = ({ roomId }) => {
  const { theme } = useThemeStore();
  const { t } = useI18n();
  const { showAlert, showConfirm, showToast, ModalRenderer } = useModal();

  const [activeView, setActiveView] = useState<HistoryView>('versions');
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [commitMessage, setCommitMessage] = useState('');
  const [showCommitDialog, setShowCommitDialog] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [revertingId, setRevertingId] = useState<number | null>(null);
  const [hasLocalChanges, setHasLocalChanges] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [compareBaseId, setCompareBaseId] = useState<number | null>(null);
  const [compareTargetId, setCompareTargetId] = useState<number | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);
  const [compareDiff, setCompareDiff] = useState<CommitDiffResponse | null>(null);

  const loadHistory = useCallback(async () => {
    if (!roomId) return;

    setLoading(true);
    setError(null);
    try {
      const data = await roomsApi.getHistory(roomId);
      setHistory(data);
    } catch (loadError) {
      const message = getRequestErrorMessage(loadError, t('history.loadFailed'));
      console.error('[HistoryPanel] load failed:', loadError);
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [roomId, t]);

  const clearCompareSelection = useCallback(() => {
    setCompareBaseId(null);
    setCompareTargetId(null);
    setCompareDiff(null);
    setCompareError(null);
  }, []);

  const setCompareBase = useCallback((commitId: number) => {
    setCompareBaseId((current) => {
      if (current === commitId) {
        return null;
      }
      return commitId;
    });
    setCompareError(null);
  }, []);

  const setCompareTarget = useCallback((commitId: number) => {
    setCompareTargetId((current) => {
      if (current === commitId) {
        return null;
      }
      return commitId;
    });
    setCompareError(null);
  }, []);

  const handleCompareCommits = useCallback(async () => {
    if (!roomId || compareTargetId == null) return;

    setCompareLoading(true);
    setCompareError(null);
    try {
      const diff = await roomsApi.getCommitDiff(
        roomId,
        compareTargetId,
        compareBaseId ?? undefined,
      );
      setCompareDiff(diff);
    } catch (compareErr) {
      const message = getRequestErrorMessage(compareErr, t('history.compareFailed'));
      console.error('[HistoryPanel] compare failed:', compareErr);
      setCompareError(message);
      setCompareDiff(null);
    } finally {
      setCompareLoading(false);
    }
  }, [compareBaseId, compareTargetId, roomId, t]);

  useEffect(() => {
    if (!roomId) return;

    const observedTargets = [
      yjsManager.elementsArray,
      yjsManager.diagramSpecsMap,
      yjsManager.diagramManifestsMap,
      yjsManager.diagramStateMap,
      yjsManager.diagramIndexMap,
    ].filter(Boolean);

    if (observedTargets.length === 0) return;

    const handleChange = () => setHasLocalChanges(true);
    observedTargets.forEach((target) => target!.observeDeep(handleChange));

    return () => {
      observedTargets.forEach((target) => target!.unobserveDeep(handleChange));
    };
  }, [roomId]);

  useEffect(() => {
    if (!roomId) return;

    const awareness = yjsManager.getAwareness();
    if (!awareness) return;

    const handleAwarenessChange = () => {
      const states = awareness.getStates();
      states.forEach((state: Record<string, unknown>) => {
        const historyChanged = state?.historyChanged;
        if (typeof historyChanged === 'number' && historyChanged > Date.now() - 5000) {
          loadHistory();
        }
      });
    };

    awareness.on('change', handleAwarenessChange);
    return () => awareness.off('change', handleAwarenessChange);
  }, [roomId, loadHistory]);

  useEffect(() => {
    loadHistory();
    const interval = window.setInterval(loadHistory, 10000);
    return () => window.clearInterval(interval);
  }, [loadHistory]);

  useEffect(() => {
    if (!history) return;
    const availableIds = new Set(history.commits.map((commit) => commit.id));

    if (compareTargetId !== null && !availableIds.has(compareTargetId)) {
      setCompareTargetId(null);
    }
    if (compareBaseId !== null && !availableIds.has(compareBaseId)) {
      setCompareBaseId(null);
    }
    if ((compareBaseId !== null && compareTargetId === compareBaseId)) {
      setCompareBaseId(null);
    }
    if (compareTargetId == null) {
      setCompareDiff(null);
    }
  }, [compareBaseId, compareTargetId, history]);

  const notifyHistoryChanged = useCallback(() => {
    const awareness = yjsManager.getAwareness();
    if (awareness) {
      awareness.setLocalStateField('historyChanged', Date.now());
    }
  }, []);

  const handleCommit = useCallback(async () => {
    if (!roomId || committing) return;

    setCommitting(true);
    try {
      const authorName = localStorage.getItem('username')
        || localStorage.getItem('temp_username')
        || t('history.authorAnonymous');
      const request: CreateCommitRequest = {
        message: commitMessage.trim() || t('history.manualSave'),
        author_name: authorName,
      };

      await roomsApi.createCommit(roomId, request);
      setCommitMessage('');
      setShowCommitDialog(false);
      setHasLocalChanges(false);
      notifyHistoryChanged();
      await loadHistory();
      showToast(t('history.savedNewCommit'), 'success');
    } catch (commitError) {
      const message = getRequestErrorMessage(commitError, t('history.createCommitFailed'));
      console.error('[HistoryPanel] commit failed:', commitError);
      setError(message);
      showAlert(message, { type: 'error', title: t('history.commitFailedTitle') });
    } finally {
      setCommitting(false);
    }
  }, [
    commitMessage,
    committing,
    loadHistory,
    notifyHistoryChanged,
    roomId,
    showAlert,
    showToast,
    t,
  ]);

  const handleCheckout = useCallback((commitId: number, commitHash: string) => {
    if (!roomId) return;

    showConfirm(
      t('history.checkoutConfirm'),
      async () => {
        await roomsApi.checkoutCommit(roomId, commitId);
        await loadHistory();
        showToast(t('history.checkoutSuccess', { hash: commitHash }), 'success');
        window.setTimeout(() => window.location.reload(), 1200);
      },
      { title: t('history.checkoutTitle'), type: 'warning' },
    );
  }, [loadHistory, roomId, showConfirm, showToast, t]);

  const handleRevert = useCallback((commitId: number) => {
    if (!roomId || revertingId !== null) return;

    showConfirm(
      t('history.revertConfirm'),
      async () => {
        setRevertingId(commitId);
        try {
          await roomsApi.revertToCommit(roomId, commitId);
          await loadHistory();
          showToast(t('history.revertSuccess'), 'success');
          window.setTimeout(() => window.location.reload(), 1200);
        } finally {
          setRevertingId(null);
        }
      },
      { title: t('history.revertTitle'), type: 'danger' },
    );
  }, [loadHistory, revertingId, roomId, showConfirm, showToast, t]);

  const handleCopyHash = useCallback(async (hash: string) => {
    try {
      await navigator.clipboard.writeText(hash);
      showToast(t('history.copiedHash'), 'success');
    } catch {
      showToast(t('history.copyHashFailed'), 'error');
    }
  }, [showToast, t]);

  const hasUncommittedChanges = Boolean((history?.pending_changes ?? 0) > 0 || hasLocalChanges);

  const renderComparePanel = () => {
    if (!history) {
      return null;
    }

    return (
      <div className={cn('border-b px-3 py-3', theme === 'dark' ? 'border-slate-800 bg-slate-800/50' : 'border-slate-100 bg-white')}>
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitCompare size={14} className={theme === 'dark' ? 'text-slate-400' : 'text-slate-500'} />
            <span className={cn('text-xs font-medium', theme === 'dark' ? 'text-slate-200' : 'text-slate-700')}>
              {t('history.compareVersions')}
            </span>
          </div>
          <button
            onClick={clearCompareSelection}
            className={cn(
              'rounded px-2 py-1 text-[11px]',
              theme === 'dark'
                ? 'bg-slate-700 text-slate-200 hover:bg-slate-600'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200',
            )}
          >
            {t('history.clear')}
          </button>
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-xs">
            <span className={theme === 'dark' ? 'text-slate-400' : 'text-slate-500'}>{t('history.baseOptional')}</span>
            <select
              value={compareBaseId ?? ''}
              onChange={(event) => {
                const value = event.target.value ? Number(event.target.value) : null;
                setCompareBaseId(value);
              }}
              className={cn(
                'rounded border px-2 py-1.5 text-xs outline-none',
                theme === 'dark'
                  ? 'border-slate-600 bg-slate-900 text-slate-200'
                  : 'border-slate-300 bg-white text-slate-700',
              )}
            >
              <option value="">{t('history.headDefault')}</option>
              {history.commits.map((commit) => (
                <option key={`base-${commit.id}`} value={commit.id}>
                  {commit.hash.slice(0, 8)} - {commit.message}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs">
            <span className={theme === 'dark' ? 'text-slate-400' : 'text-slate-500'}>{t('history.target')}</span>
            <select
              value={compareTargetId ?? ''}
              onChange={(event) => {
                const value = event.target.value ? Number(event.target.value) : null;
                setCompareTargetId(value);
              }}
              className={cn(
                'rounded border px-2 py-1.5 text-xs outline-none',
                theme === 'dark'
                  ? 'border-slate-600 bg-slate-900 text-slate-200'
                  : 'border-slate-300 bg-white text-slate-700',
              )}
            >
              <option value="">{t('history.selectTargetCommit')}</option>
              {history.commits.map((commit) => (
                <option key={`target-${commit.id}`} value={commit.id}>
                  {commit.hash.slice(0, 8)} - {commit.message}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="mt-2 flex items-center gap-2">
          <button
            onClick={handleCompareCommits}
            disabled={compareTargetId == null || compareLoading || compareTargetId === compareBaseId}
            className={cn(
              'inline-flex items-center gap-1 rounded px-2.5 py-1.5 text-xs',
              compareTargetId == null || compareLoading || compareTargetId === compareBaseId
                ? 'cursor-not-allowed opacity-50'
                : theme === 'dark'
                  ? 'bg-slate-700 text-slate-200 hover:bg-slate-600'
                  : 'bg-slate-800 text-white hover:bg-slate-900',
            )}
            >
              <ScanSearch size={12} />
              {compareLoading ? t('history.comparing') : t('history.compare')}
            </button>
            <button
              onClick={() => {
                if (compareTargetId == null) {
                  return;
                }
                if (compareTargetId === compareBaseId) {
                  showAlert(t('history.invalidCompareSelectionMessage'), {
                    type: 'warning',
                    title: t('history.invalidCompareSelectionTitle'),
                  });
                  return;
                }
                handleCheckout(compareTargetId, history.commits.find((commit) => commit.id === compareTargetId)?.hash || '');
              }}
              disabled={compareTargetId == null || compareTargetId === compareBaseId}
              className={cn(
                'inline-flex items-center gap-1 rounded px-2.5 py-1.5 text-xs',
                compareTargetId == null || compareTargetId === compareBaseId
                  ? 'cursor-not-allowed opacity-50'
                  : theme === 'dark'
                    ? 'border border-blue-800 bg-blue-900/20 text-blue-200 hover:bg-blue-900/40'
                    : 'border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100',
            )}
          >
            <GitBranch size={12} />
            {t('history.checkoutTarget')}
          </button>
          {compareBaseId !== null && compareTargetId !== null && (
            <button
              type="button"
              onClick={() => {
                const nextBase = compareTargetId;
                const nextTarget = compareBaseId;
                setCompareBaseId(nextBase);
                setCompareTargetId(nextTarget);
                setCompareDiff(null);
              }}
              className={cn(
                'rounded px-2.5 py-1.5 text-xs',
                theme === 'dark'
                  ? 'bg-slate-700 text-slate-200 hover:bg-slate-600'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200',
              )}
            >
              {t('history.swap')}
            </button>
          )}
        </div>
        {compareError && (
          <div className={cn('mt-2 text-xs text-red-500', theme === 'dark' ? 'text-red-300' : '')}>
            {compareError}
          </div>
        )}
      </div>
    );
  };

  const renderCommitDiff = () => {
    if (!compareDiff) return null;

    return (
      <div className={cn('border-b p-3', theme === 'dark' ? 'border-slate-800 bg-slate-900/50' : 'border-slate-100 bg-slate-50')}>
        <div className="mb-2 text-xs">
          <div className={cn('font-semibold', theme === 'dark' ? 'text-slate-200' : 'text-slate-700')}>
            {t('history.diffSummary')}
          </div>
          <div className="text-[11px] opacity-80">
            {t('history.from')}
            {' '}
            {compareDiff.from_commit?.hash
              ? compareDiff.from_commit.hash.slice(0, 8)
              : t('history.fromHead')}
            {' '}
            {t('history.to')}
            {' '}
            {compareDiff.to_commit.hash.slice(0, 8)}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div className={cn('rounded p-2 text-[11px]', theme === 'dark' ? 'bg-slate-800' : 'bg-slate-100')}>
            <div>{t('history.elements')}</div>
            <div className="font-semibold">+{compareDiff.elements_added} / -{compareDiff.elements_removed}</div>
          </div>
          <div className={cn('rounded p-2 text-[11px]', theme === 'dark' ? 'bg-slate-800' : 'bg-slate-100')}>
            <div>{t('history.modified')}</div>
            <div className="font-semibold">{compareDiff.elements_modified}</div>
          </div>
          <div className={cn('rounded p-2 text-[11px]', theme === 'dark' ? 'bg-slate-800' : 'bg-slate-100')}>
            <div>{t('history.diagrams')}</div>
            <div className="font-semibold">
              +{compareDiff.diagrams_added} / -{compareDiff.diagrams_removed} / ~{compareDiff.diagrams_modified}
            </div>
          </div>
          <div className={cn('rounded p-2 text-[11px]', theme === 'dark' ? 'bg-slate-800' : 'bg-slate-100')}>
            <div>{t('history.sizeDelta')}</div>
            <div className="font-semibold">{formatSignedSize(compareDiff.size_diff)}</div>
          </div>
        </div>
        {compareDiff.changes.length > 0 && (
          <div className="mt-3">
            <div className={cn('text-[11px] font-semibold', theme === 'dark' ? 'text-slate-300' : 'text-slate-600')}>
              {t('history.elementChanges')}
            </div>
            <div className={cn('mt-1 max-h-44 overflow-y-auto rounded border p-2 text-[11px]', theme === 'dark' ? 'bg-slate-900 border-slate-700' : 'bg-white border-slate-200')}>
              {compareDiff.changes.map((change, index) => (
                <div key={`${change.element_id}-${change.action}-${index}`}>
                  <span className="font-medium">{change.action}</span>
                  {' '}
                  {change.element_id}
                  {' '}
                  ({t('history.typeLabel')}: {change.element_type || t('history.unknownType')})
                  {change.text ? ` - ${change.text}` : ''}
                </div>
              ))}
            </div>
          </div>
        )}
        {compareDiff.diagram_changes.length > 0 && (
          <div className="mt-3">
            <div className={cn('text-[11px] font-semibold', theme === 'dark' ? 'text-slate-300' : 'text-slate-600')}>
              {t('history.diagramChanges')}
            </div>
            <div className={cn('mt-1 space-y-1 text-[11px]', theme === 'dark' ? 'text-slate-300' : 'text-slate-600')}>
            {compareDiff.diagram_changes.map((change, index) => (
              <div
                key={`${change.diagram_id}-${change.action}-${index}`}
                className="rounded border p-2"
                >
                  <div>{change.action}</div>
                  <div className="opacity-80">
                    {change.diagram_id} - {change.title} ({getDiagramFamilyLabel(change.family)})
                    {change.component_count !== null ? ` - ${t('history.componentsCount', { count: change.component_count })}` : ''}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div
        className={cn(
          'border-b px-3 py-2',
          theme === 'dark' ? 'border-slate-700 bg-slate-900/50' : 'border-slate-200 bg-slate-50',
        )}
      >
        <div className="flex items-center justify-between gap-3">
          <div
            className={cn(
              'inline-flex rounded-lg p-1',
              theme === 'dark' ? 'bg-slate-800' : 'bg-slate-200/70',
            )}
          >
            {(['versions', 'events'] as HistoryView[]).map((view) => {
              const active = activeView === view;
              return (
                <button
                  key={view}
                  type="button"
                  onClick={() => setActiveView(view)}
                  className={cn(
                    'rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                    active
                      ? theme === 'dark'
                        ? 'bg-slate-700 text-slate-100'
                        : 'bg-white text-slate-700 shadow-sm'
                      : theme === 'dark'
                        ? 'text-slate-400 hover:text-slate-200'
                        : 'text-slate-500 hover:text-slate-700',
                  )}
                >
                  {view === 'versions' ? t('history.view.versions') : t('history.view.activity')}
                </button>
              );
            })}
          </div>

          {activeView === 'versions' && (
            <div className="flex items-center gap-1">
              <button
                onClick={() => setShowCommitDialog(true)}
                disabled={committing || !hasUncommittedChanges}
                className={cn(
                  'rounded p-1.5 transition-colors',
                  committing || !hasUncommittedChanges
                    ? 'cursor-not-allowed opacity-40'
                    : theme === 'dark'
                      ? 'text-green-400 hover:bg-slate-700'
                      : 'text-green-600 hover:bg-slate-200',
                )}
                title={hasUncommittedChanges ? t('history.createCommit') : t('history.noLocalChanges')}
              >
                <Save size={14} />
              </button>
              <button
                onClick={loadHistory}
                disabled={loading}
                className={cn(
                  'rounded p-1.5 transition-colors',
                  theme === 'dark' ? 'text-slate-400 hover:bg-slate-700' : 'text-slate-500 hover:bg-slate-200',
                )}
                title={t('history.refreshHistory')}
              >
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              </button>
            </div>
          )}
        </div>

        {activeView === 'versions' && (
          <div className="mt-2 flex items-center gap-2">
            <GitBranch size={14} className={theme === 'dark' ? 'text-slate-400' : 'text-slate-500'} />
            <span className={cn('text-xs font-medium', theme === 'dark' ? 'text-slate-300' : 'text-slate-600')}>
              main
            </span>
            {history?.head_commit_id && (
              <code className={cn('text-[10px] font-mono', theme === 'dark' ? 'text-blue-400' : 'text-blue-600')}>
                HEAD
              </code>
            )}
          </div>
        )}
      </div>

      {activeView === 'versions' && showCommitDialog && (
        <div
          className={cn(
            'border-b p-3',
            theme === 'dark' ? 'border-slate-700 bg-slate-800/50' : 'border-slate-200 bg-slate-100',
          )}
        >
          <div className="mb-2 flex items-center gap-2">
            <MessageSquare size={12} className={theme === 'dark' ? 'text-slate-400' : 'text-slate-500'} />
            <span className={cn('text-xs', theme === 'dark' ? 'text-slate-300' : 'text-slate-600')}>
              {t('history.commitMessage')}
            </span>
          </div>
          <input
            type="text"
            value={commitMessage}
            onChange={(event) => setCommitMessage(event.target.value)}
            placeholder={t('history.describeChange')}
            className={cn(
              'w-full rounded border px-2 py-1.5 text-xs outline-none',
              theme === 'dark'
                ? 'border-slate-600 bg-slate-900 text-slate-200 placeholder-slate-500 focus:border-blue-500'
                : 'border-slate-300 bg-white text-slate-700 placeholder-slate-400 focus:border-blue-400',
            )}
            onKeyDown={(event) => {
              if (event.key === 'Enter') handleCommit();
              if (event.key === 'Escape') setShowCommitDialog(false);
            }}
            autoFocus
          />
          <div className="mt-2 flex gap-2">
            <button
              onClick={handleCommit}
              disabled={committing}
              className={cn(
                'flex flex-1 items-center justify-center gap-1 rounded px-2 py-1 text-xs transition-colors',
                committing
                  ? 'cursor-not-allowed opacity-50'
                  : theme === 'dark'
                    ? 'bg-green-600 text-white hover:bg-green-700'
                    : 'bg-green-500 text-white hover:bg-green-600',
              )}
            >
              <Check size={12} />
              {committing ? t('history.saving') : t('history.saveCommit')}
            </button>
            <button
              onClick={() => setShowCommitDialog(false)}
              className={cn(
                'rounded px-2 py-1 text-xs transition-colors',
                theme === 'dark'
                  ? 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                  : 'bg-slate-200 text-slate-600 hover:bg-slate-300',
              )}
            >
              {t('history.cancel')}
            </button>
          </div>
        </div>
      )}

      {activeView === 'events' ? (
        <div className="flex-1 min-h-0">
          <CollabEventsPanel />
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          {loading && !history ? (
            <div className={cn('p-4 text-center text-sm', theme === 'dark' ? 'text-slate-500' : 'text-slate-400')}>
              {t('history.loading')}
            </div>
          ) : error && !history ? (
            <div className={cn('p-4 text-center text-sm', theme === 'dark' ? 'text-red-400' : 'text-red-500')}>
              {error}
            </div>
          ) : (
            <>
              {hasUncommittedChanges && (
                <div
                  className={cn(
                    'border-b px-3 py-2',
                    theme === 'dark' ? 'border-slate-800 bg-amber-900/10' : 'border-slate-100 bg-amber-50',
                  )}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className={cn('text-xs font-medium', theme === 'dark' ? 'text-amber-300' : 'text-amber-700')}>
                        {t('history.localChangesPending')}
                      </div>
                      <div className={cn('mt-0.5 text-[10px]', theme === 'dark' ? 'text-slate-500' : 'text-slate-500')}>
                        {t('history.localChangesDescription')}
                      </div>
                    </div>
                    <span
                      className={cn(
                        'rounded px-1.5 py-0.5 text-[10px] font-medium',
                        theme === 'dark' ? 'bg-amber-900/30 text-amber-300' : 'bg-amber-100 text-amber-700',
                      )}
                    >
                      +{history?.pending_changes ?? 0}
                    </span>
                  </div>
                </div>
              )}

              {renderComparePanel()}
              {renderCommitDiff()}

              {history?.commits.map((commit, index) => (
                <CommitCard
                  key={commit.id}
                  roomId={roomId}
                  commit={commit}
                  isHead={commit.id === history.head_commit_id}
                  isExpanded={expandedId === commit.id}
                  isFirst={index === 0 && !hasUncommittedChanges}
                  isLast={index === history.commits.length - 1}
                  isReverting={revertingId === commit.id}
                  onToggle={() => setExpandedId((current) => (current === commit.id ? null : commit.id))}
                  onCheckout={handleCheckout}
                  onCopyHash={handleCopyHash}
                  onRevert={handleRevert}
                  onSetCompareBase={setCompareBase}
                  onSetCompareTarget={setCompareTarget}
                />
              ))}

              {(!history || (history.commits.length === 0 && !hasUncommittedChanges)) && (
                <div className={cn('flex flex-col items-center justify-center py-8', theme === 'dark' ? 'text-slate-500' : 'text-slate-400')}>
                  <Clock size={32} className="mb-3 opacity-40" />
                  <span className="text-sm">{t('history.noCommitsYet')}</span>
                  <span className="mt-1 text-xs opacity-70">{t('history.noCommitsDescription')}</span>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {activeView === 'versions' && history && (
        <div
          className={cn(
            'flex items-center justify-between border-t px-3 py-1.5 text-[10px]',
            theme === 'dark' ? 'border-slate-700 bg-slate-900/50 text-slate-500' : 'border-slate-200 bg-slate-50 text-slate-400',
          )}
        >
          <span>{t('history.commitsCount', { count: history.commits.length })}</span>
          <span>{formatSize(history.total_size)}</span>
        </div>
      )}

      <ModalRenderer />
    </div>
  );
};

interface CommitCardProps {
  roomId: string;
  commit: CommitInfo;
  isHead: boolean;
  isExpanded: boolean;
  isFirst: boolean;
  isLast: boolean;
  isReverting: boolean;
  onToggle: () => void;
  onCheckout: (commitId: number, commitHash: string) => void;
  onCopyHash: (hash: string) => Promise<void>;
  onRevert: (commitId: number) => void;
  onSetCompareBase: (commitId: number) => void;
  onSetCompareTarget: (commitId: number) => void;
}

const CommitCard: React.FC<CommitCardProps> = ({
  roomId,
  commit,
  isHead,
  isExpanded,
  isFirst,
  isLast,
  isReverting,
  onToggle,
  onCheckout,
  onCopyHash,
  onRevert,
  onSetCompareBase,
  onSetCompareTarget,
}) => {
  const { theme } = useThemeStore();
  const { t, formatRelativeTime, formatDateTime } = useI18n();
  const [detail, setDetail] = useState<CommitDetailResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    if (!isExpanded || detail || loadingDetail) return;

    setLoadingDetail(true);
    roomsApi.getCommitDetail(roomId, commit.id)
      .then(setDetail)
      .catch((error) => {
        console.error('[HistoryPanel] detail load failed:', error);
      })
      .finally(() => setLoadingDetail(false));
  }, [commit.id, detail, isExpanded, loadingDetail, roomId]);

  const detailSummary = detail ? summarizeDetail(detail) : null;

  return (
    <div
      className={cn(
        'group border-b transition-colors',
        theme === 'dark'
          ? 'border-slate-800 hover:bg-slate-800/50'
          : 'border-slate-100 hover:bg-slate-50',
      )}
    >
      <div className="flex cursor-pointer items-center px-3 py-2" onClick={onToggle}>
        <div className="mr-3 flex w-6 justify-center">
          <div className="relative flex flex-col items-center">
            <div className={cn('h-3 w-0.5', isFirst ? 'bg-transparent' : theme === 'dark' ? 'bg-slate-700' : 'bg-slate-300')} />
            <div
              className={cn(
                'h-2.5 w-2.5 rounded-full border-2',
                isHead
                  ? 'border-green-400 bg-green-500'
                  : theme === 'dark'
                    ? 'border-slate-500 bg-slate-700'
                    : 'border-slate-400 bg-white',
              )}
            />
            <div className={cn('h-3 w-0.5', isLast ? 'bg-transparent' : theme === 'dark' ? 'bg-slate-700' : 'bg-slate-300')} />
          </div>
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <code className={cn('text-[10px] font-mono', theme === 'dark' ? 'text-blue-400' : 'text-blue-600')}>
              {commit.hash}
            </code>
            {isHead && (
              <span className={cn(
                'rounded px-1.5 py-0.5 text-[10px] font-medium',
                theme === 'dark' ? 'bg-green-900/40 text-green-300' : 'bg-green-100 text-green-700',
              )}
              >
                HEAD
              </span>
            )}
          </div>
          <div className={cn('mt-1 truncate text-xs font-medium', theme === 'dark' ? 'text-slate-200' : 'text-slate-700')}>
            {commit.message}
          </div>
          <div className={cn('mt-1 flex items-center gap-3 text-[10px]', theme === 'dark' ? 'text-slate-500' : 'text-slate-500')}>
            <span className="inline-flex items-center gap-1"><User size={10} />{commit.author_name}</span>
            <span>{formatRelativeTime(commit.timestamp)}</span>
            <span>{formatSize(commit.size)}</span>
          </div>
        </div>

        <ChevronRight
          size={14}
          className={cn(
            'transition-transform',
            isExpanded && 'rotate-90',
            theme === 'dark' ? 'text-slate-500' : 'text-slate-400',
          )}
        />
      </div>

      {isExpanded && (
        <div className={cn('space-y-3 px-4 pb-4 pt-1 text-xs', theme === 'dark' ? 'text-slate-300' : 'text-slate-600')}>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <div>
              <div className="text-[10px] uppercase tracking-wide opacity-70">{t('history.timestamp')}</div>
              <div>{formatDateTime(commit.timestamp)}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wide opacity-70">{t('history.commitSize')}</div>
              <div>{formatSize(commit.size)}</div>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => onCopyHash(commit.hash)}
              className={cn(
                'inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] transition-colors',
                theme === 'dark' ? 'bg-slate-700 text-slate-200 hover:bg-slate-600' : 'bg-slate-100 text-slate-700 hover:bg-slate-200',
              )}
            >
              <Copy size={12} />
              {t('history.copyHash')}
            </button>
            <button
              onClick={() => onCheckout(commit.id, commit.hash)}
              disabled={isHead}
              className={cn(
                'inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] transition-colors',
                isHead
                  ? 'cursor-not-allowed opacity-50'
                  : theme === 'dark'
                    ? 'bg-blue-900/30 text-blue-300 hover:bg-blue-900/50'
                    : 'bg-blue-50 text-blue-700 hover:bg-blue-100',
              )}
            >
              <GitBranch size={12} />
              {t('history.checkout')}
            </button>
            <button
              onClick={() => onRevert(commit.id)}
              disabled={isHead || isReverting}
              className={cn(
                'inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] transition-colors',
                isHead || isReverting
                  ? 'cursor-not-allowed opacity-50'
                  : theme === 'dark'
                    ? 'bg-red-900/30 text-red-300 hover:bg-red-900/50'
                    : 'bg-red-50 text-red-700 hover:bg-red-100',
              )}
            >
              <RotateCcw size={12} />
              {isReverting ? t('history.reverting') : t('history.revert')}
            </button>
            <button
              onClick={() => onSetCompareBase(commit.id)}
              className={cn(
                'inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] transition-colors',
                theme === 'dark'
                  ? 'bg-slate-700 text-slate-200 hover:bg-slate-600'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200',
              )}
            >
              {t('history.setAsBase')}
            </button>
            <button
              onClick={() => onSetCompareTarget(commit.id)}
              className={cn(
                'inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] transition-colors',
                theme === 'dark'
                  ? 'bg-blue-900 text-blue-200 hover:bg-blue-800'
                  : 'bg-blue-50 text-blue-700 hover:bg-blue-100',
              )}
            >
              {t('history.setAsTarget')}
            </button>
          </div>

          {loadingDetail && (
            <div className={cn('rounded border px-3 py-2 text-[11px]', theme === 'dark' ? 'border-slate-700 bg-slate-800/60' : 'border-slate-200 bg-slate-50')}>
              {t('history.loadingCommitDetail')}
            </div>
          )}

          {detail && detailSummary && (
            <div className={cn('rounded border p-3', theme === 'dark' ? 'border-slate-700 bg-slate-800/60' : 'border-slate-200 bg-slate-50')}>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div>
                  <div className="text-[10px] uppercase tracking-wide opacity-70">{t('history.elements')}</div>
                  <div className="mt-1 font-medium">{detail.elements_count}</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-wide opacity-70">{t('history.diagrams')}</div>
                  <div className="mt-1 font-medium">{detail.diagrams_count}</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-wide opacity-70">{t('history.families')}</div>
                  <div className="mt-1 font-medium">{detailSummary.familySummary || t('history.none')}</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-wide opacity-70">{t('history.managedStates')}</div>
                  <div className="mt-1 font-medium">{detailSummary.managedSummary || t('history.none')}</div>
                </div>
              </div>

              {detail.diagrams.length > 0 && (
                <div className="mt-3">
                  <div className="mb-2 text-[10px] uppercase tracking-wide opacity-70">
                    {t('history.diagramSummary')}
                  </div>
                  <div className="space-y-2">
                    {detail.diagrams.map((diagram) => (
                      <div
                        key={diagram.diagram_id}
                        className={cn(
                          'rounded px-2 py-2',
                          theme === 'dark' ? 'bg-slate-900/60' : 'bg-white',
                        )}
                      >
                        <div className="flex items-center gap-2">
                          <Shapes size={12} className={theme === 'dark' ? 'text-violet-300' : 'text-violet-600'} />
                          <span className="font-medium">{diagram.title}</span>
                          <span className={cn(
                            'rounded px-1.5 py-0.5 text-[10px]',
                            theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-slate-100 text-slate-600',
                          )}
                          >
                            {getDiagramFamilyLabel(diagram.family)}
                          </span>
                        </div>
                        <div className="mt-1 text-[11px] opacity-80">
                          {t('history.componentsAndConnectors', {
                            components: diagram.component_count,
                            connectors: diagram.connector_count,
                            state: getManagedDiagramStateLabel(
                              diagram.managed_state as Parameters<typeof getManagedDiagramStateLabel>[0],
                            ) || diagram.managed_state,
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};


