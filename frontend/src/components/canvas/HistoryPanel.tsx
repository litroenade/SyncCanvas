/**
 * 模块名称: HistoryPanel
 * 主要功能: Git 风格的版本历史面板
 */

import React, { useEffect, useState, useCallback } from 'react'
import {
  GitBranch,
  Save,
  RefreshCw,
  Clock,
  ChevronRight,
  RotateCcw,
  User,
  MessageSquare,
  Check
} from 'lucide-react'
import { cn } from '../../lib/utils'
import { useThemeStore } from '../../stores/useThemeStore'
import { roomsApi, HistoryResponse, CommitInfo, CreateCommitRequest } from '../../services/api/rooms'
import { useModal } from '../common/Modal'
import { ContextMenu } from '../common/ContextMenu'
import { yjsManager } from '../../lib/yjs'

interface HistoryPanelProps {
  /** 房间 ID */
  roomId: string
}

const formatSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const formatRelativeTime = (timestamp: number): string => {
  const diff = Date.now() - timestamp
  const minutes = Math.floor(diff / (60 * 1000))
  const hours = Math.floor(diff / (60 * 60 * 1000))
  const days = Math.floor(diff / (24 * 60 * 60 * 1000))

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  if (hours < 24) return `${hours} 小时前`
  if (days < 7) return `${days} 天前`
  return new Date(timestamp).toLocaleDateString('zh-CN')
}

const formatFullTime = (timestamp: number): string => {
  return new Date(timestamp).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export const HistoryPanel: React.FC<HistoryPanelProps> = ({ roomId }) => {
  const { theme } = useThemeStore()
  const [history, setHistory] = useState<HistoryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [committing, setCommitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [showCommitDialog, setShowCommitDialog] = useState(false)
  const [commitMessage, setCommitMessage] = useState('')
  const [revertingId, setRevertingId] = useState<number | null>(null)
  const [diffCommitId, setDiffCommitId] = useState<number | null>(null)
  const [hasLocalChanges, setHasLocalChanges] = useState(false)
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; commit: CommitInfo } | null>(null)

  const { showAlert, showConfirm, showToast, ModalRenderer } = useModal()

  // 监听本地更改
  useEffect(() => {
    if (!roomId) return

    const elementsArray = yjsManager.elementsArray
    if (!elementsArray) return

    const handleChange = () => setHasLocalChanges(true)
    elementsArray.observeDeep(handleChange)

    return () => elementsArray.unobserveDeep(handleChange)
  }, [roomId])


  const loadHistory = useCallback(async () => {
    if (!roomId) return

    setLoading(true)
    setError(null)
    try {
      const data = await roomsApi.getHistory(roomId)
      setHistory(data)
    } catch (err: any) {
      console.error('加载历史失败:', err)
      setError(err.response?.data?.detail || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [roomId])

  // 监听 Awareness 变更
  useEffect(() => {
    if (!roomId) return

    const awareness = yjsManager.getAwareness()
    if (!awareness) return

    const handleAwarenessChange = () => {
      const states = awareness.getStates()
      states.forEach((state: any) => {
        if (state?.historyChanged && state.historyChanged > Date.now() - 5000) {
          loadHistory()
        }
      })
    }

    awareness.on('change', handleAwarenessChange)
    return () => awareness.off('change', handleAwarenessChange)
  }, [roomId, loadHistory])

  const handleCommit = async () => {
    if (!roomId || committing) return

    setCommitting(true)
    try {
      let authorName = 'Anonymous';
      const storedUsername = localStorage.getItem('username');
      if (storedUsername) {
        authorName = storedUsername;
      } else {
        const tempName = localStorage.getItem('temp_username');
        if (tempName) {
          authorName = tempName;
        }
      }

      const request: CreateCommitRequest = {
        message: commitMessage.trim() || '手动保存',
        author_name: authorName
      }
      await roomsApi.createCommit(roomId, request)
      setCommitMessage('')
      setShowCommitDialog(false)
      setHasLocalChanges(false)

      const awareness = yjsManager.getAwareness()
      if (awareness) {
        awareness.setLocalStateField('historyChanged', Date.now())
      }

      await loadHistory()
    } catch (err: any) {
      console.error('创建提交失败:', err)
      setError(err.response?.data?.detail || '提交失败')
    } finally {
      setCommitting(false)
    }
  }

  const handleRevert = (commitId: number) => {
    if (!roomId || revertingId !== null) return

    showConfirm(
      '确定要回滚到此版本吗？当前未保存的更改将丢失。',
      async () => {
        setRevertingId(commitId)
        try {
          await roomsApi.revertToCommit(roomId, commitId)
          await loadHistory()
          showToast('已回滚到指定版本，即将刷新页面...', 'success')
          setTimeout(() => window.location.reload(), 1500)
        } catch (err: any) {
          console.error('回滚失败:', err)
          setError(err.response?.data?.detail || '回滚失败')
          showAlert(err.response?.data?.detail || '回滚失败', { type: 'error', title: '回滚失败' })
        } finally {
          setRevertingId(null)
        }
      },
      { title: '确认回滚', type: 'danger' }
    )
  }

  const handleCheckout = (commitId: number, commitHash: string) => {
    if (!roomId) return

    showConfirm(
      '检出此版本将丢弃当前未保存的更改，确定继续吗？',
      async () => {
        try {
          await roomsApi.checkoutCommit(roomId, commitId)
          await loadHistory()
          showToast(`已检出到 ${commitHash}，即将刷新页面...`, 'success')
          setTimeout(() => window.location.reload(), 1500)
        } catch (err: any) {
          console.error('检出失败:', err)
          showAlert(err.response?.data?.detail || '检出失败', { type: 'error', title: '检出失败' })
        }
      },
      { title: '确认检出', type: 'warning' }
    )
  }

  // 预览暂不支持 - Excalidraw 全量数据恢复较复杂，需要重新设计预览接口
  const handlePreviewStart = async () => {
    console.log('Excalidraw 历史预览暂不支持');
  }

  const handlePreviewEnd = () => {
    // no-op
  }

  useEffect(() => {
    loadHistory()
    const interval = setInterval(loadHistory, 10000)
    return () => clearInterval(interval)
  }, [loadHistory])

  if (loading && !history) {
    return (
      <div className={cn('p-4 text-center text-sm', theme === 'dark' ? 'text-slate-500' : 'text-slate-400')}>
        加载中...
      </div>
    )
  }

  if (error && !history) {
    return (
      <div className={cn('p-4 text-center text-sm', theme === 'dark' ? 'text-red-400' : 'text-red-500')}>
        {error}
      </div>
    )
  }

  const hasUncommittedChanges = (history && history.pending_changes > 0) || hasLocalChanges

  const handleContextMenu = (e: React.MouseEvent, commit: CommitInfo) => {
    e.preventDefault()
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      commit
    })
  }

  const handleCopyHash = async (hash: string) => {
    try {
      await navigator.clipboard.writeText(hash)
      showToast('提交哈希已复制', 'success')
    } catch (err) {
      showToast('复制失败', 'error')
    }
  }

  return (
    <div className="flex flex-col h-full" onClick={() => setContextMenu(null)}>
      {/* 头部操作栏 */}
      <div className={cn(
        'flex items-center justify-between px-3 py-2 border-b',
        theme === 'dark' ? 'border-slate-700 bg-slate-900/50' : 'border-slate-200 bg-slate-50'
      )}>
        <div className="flex items-center gap-2">
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
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowCommitDialog(true)}
            disabled={committing || !hasUncommittedChanges}
            className={cn(
              'p-1.5 rounded transition-colors',
              committing || !hasUncommittedChanges
                ? 'opacity-40 cursor-not-allowed'
                : theme === 'dark'
                  ? 'hover:bg-slate-700 text-green-400'
                  : 'hover:bg-slate-200 text-green-600'
            )}
            title={hasUncommittedChanges ? '提交更改' : '没有待提交的更改'}
          >
            <Save size={14} />
          </button>
          <button
            onClick={loadHistory}
            disabled={loading}
            className={cn(
              'p-1.5 rounded transition-colors',
              theme === 'dark' ? 'hover:bg-slate-700 text-slate-400' : 'hover:bg-slate-200 text-slate-500'
            )}
            title="刷新"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* 提交对话框 */}
      {showCommitDialog && (
        <div className={cn(
          'p-3 border-b',
          theme === 'dark' ? 'border-slate-700 bg-slate-800/50' : 'border-slate-200 bg-slate-100'
        )}>
          <div className="flex items-center gap-2 mb-2">
            <MessageSquare size={12} className={theme === 'dark' ? 'text-slate-400' : 'text-slate-500'} />
            <span className={cn('text-xs', theme === 'dark' ? 'text-slate-300' : 'text-slate-600')}>
              提交消息
            </span>
          </div>
          <input
            type="text"
            value={commitMessage}
            onChange={(e) => setCommitMessage(e.target.value)}
            placeholder="描述你的更改..."
            className={cn(
              'w-full px-2 py-1.5 text-xs rounded border outline-none',
              theme === 'dark'
                ? 'bg-slate-900 border-slate-600 text-slate-200 placeholder-slate-500 focus:border-blue-500'
                : 'bg-white border-slate-300 text-slate-700 placeholder-slate-400 focus:border-blue-400'
            )}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCommit()
              if (e.key === 'Escape') setShowCommitDialog(false)
            }}
            autoFocus
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={handleCommit}
              disabled={committing}
              className={cn(
                'flex-1 flex items-center justify-center gap-1 px-2 py-1 text-xs rounded transition-colors',
                committing
                  ? 'opacity-50 cursor-not-allowed'
                  : theme === 'dark'
                    ? 'bg-green-600 hover:bg-green-700 text-white'
                    : 'bg-green-500 hover:bg-green-600 text-white'
              )}
            >
              <Check size={12} />
              {committing ? '提交中...' : '提交'}
            </button>
            <button
              onClick={() => setShowCommitDialog(false)}
              className={cn(
                'px-2 py-1 text-xs rounded transition-colors',
                theme === 'dark'
                  ? 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                  : 'bg-slate-200 hover:bg-slate-300 text-slate-600'
              )}
            >
              取消
            </button>
          </div>
        </div>
      )}

      {/* 历史列表 */}
      <div className="flex-1 overflow-y-auto">
        {hasUncommittedChanges && (
          <div className={cn(
            'flex items-center px-2 py-2 border-b',
            theme === 'dark' ? 'border-slate-800 bg-amber-900/10' : 'border-slate-100 bg-amber-50'
          )}>
            <div className="w-8 flex justify-center shrink-0">
              <div className="relative flex flex-col items-center">
                <div className={cn('w-0.5 h-3', theme === 'dark' ? 'bg-slate-700' : 'bg-slate-300')} />
                <div className="w-3 h-3 rounded-full bg-amber-500 ring-2 ring-amber-300/50 animate-pulse" />
                <div className={cn('w-0.5 h-3', theme === 'dark' ? 'bg-slate-700' : 'bg-slate-300')} />
              </div>
            </div>
            <div className="flex-1 min-w-0 pl-2">
              <div className="flex items-center gap-2">
                <span className={cn(
                  'text-xs font-medium',
                  theme === 'dark' ? 'text-amber-400' : 'text-amber-600'
                )}>
                  未提交的更改
                </span>
                <span className={cn(
                  'text-[10px] px-1.5 py-0.5 rounded font-medium',
                  theme === 'dark' ? 'bg-amber-900/30 text-amber-300' : 'bg-amber-100 text-amber-700'
                )}>
                  +{history?.pending_changes}
                </span>
              </div>
              <div className={cn('text-[10px] mt-0.5', theme === 'dark' ? 'text-slate-500' : 'text-slate-400')}>
                点击上方保存按钮提交更改
              </div>
            </div>
          </div>
        )}

        {history?.commits.map((commit, index) => {
          const isHead = commit.id === history.head_commit_id
          const isFirst = index === 0 && !hasUncommittedChanges
          const isLast = index === history.commits.length - 1
          const isExpanded = expandedId === commit.id
          const isReverting = revertingId === commit.id
          const showingDiff = diffCommitId === commit.id

          return (
            <CommitNode
              key={commit.id}
              commit={commit}
              roomId={roomId}
              isHead={isHead}
              isFirst={isFirst}
              isLast={isLast}
              isExpanded={isExpanded}
              isReverting={isReverting}
              showingDiff={showingDiff}
              theme={theme}
              onToggle={() => setExpandedId(isExpanded ? null : commit.id)}
              onRevert={() => handleRevert(commit.id)}
              onCheckout={() => handleCheckout(commit.id, commit.hash)}
              onShowDiff={() => setDiffCommitId(showingDiff ? null : commit.id)}
              onContextMenu={(e) => handleContextMenu(e, commit)}
              onPreviewStart={() => handlePreviewStart()}
              onPreviewEnd={handlePreviewEnd}
            />
          )
        })}

        {(!history || (history.commits.length === 0 && !hasUncommittedChanges)) && (
          <div className={cn('flex flex-col items-center justify-center py-8', theme === 'dark' ? 'text-slate-500' : 'text-slate-400')}>
            <Clock size={32} className="mb-3 opacity-40" />
            <span className="text-sm">暂无提交历史</span>
            <span className="text-xs mt-1 opacity-70">开始绘制后将自动记录</span>
          </div>
        )}
      </div>

      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={() => setContextMenu(null)}
          items={[
            {
              label: '复制哈希',
              onClick: () => handleCopyHash(contextMenu.commit.hash)
            },
            // 暂不启用差异查看，因为 diff 逻辑也是基于 Shape 的
            {
              separator: true,
              label: '',
              onClick: () => { }
            },
            {
              label: '检出此版本',
              disabled: contextMenu.commit.id === history?.head_commit_id,
              onClick: () => handleCheckout(contextMenu.commit.id, contextMenu.commit.hash)
            },
            {
              label: '回滚到此版本',
              danger: true,
              disabled: contextMenu.commit.id === history?.head_commit_id,
              onClick: () => handleRevert(contextMenu.commit.id)
            }
          ]}
        />
      )}

      {history && (
        <div className={cn(
          'flex items-center justify-between px-3 py-1.5 border-t text-[10px]',
          theme === 'dark' ? 'border-slate-700 bg-slate-900/50 text-slate-500' : 'border-slate-200 bg-slate-50 text-slate-400'
        )}>
          <span>{history.commits.length} 个提交</span>
          <span>{formatSize(history.total_size)}</span>
        </div>
      )}

      <ModalRenderer />
    </div>
  )
}

interface CommitNodeProps {
  commit: CommitInfo
  roomId: string
  isHead: boolean
  isFirst: boolean
  isLast: boolean
  isExpanded: boolean
  isReverting: boolean
  showingDiff: boolean
  theme: 'light' | 'dark'
  onToggle: () => void
  onRevert: () => void
  onCheckout: () => void
  onShowDiff: () => void
  onContextMenu: (e: React.MouseEvent) => void
  onPreviewStart: () => void
  onPreviewEnd: () => void
}

const CommitNode: React.FC<CommitNodeProps> = ({
  commit,
  isHead,
  isFirst,
  isLast,
  isExpanded,
  isReverting,
  theme,
  onToggle,
  onRevert,
  onContextMenu,
}) => {
  return (
    <div
      className={cn(
        'group transition-colors',
        theme === 'dark' ? 'hover:bg-slate-800/50' : 'hover:bg-slate-50'
      )}
      onContextMenu={onContextMenu}
    >
      <div className="flex items-center px-2 py-2 cursor-pointer" onClick={onToggle}>
        <div className="w-8 flex justify-center shrink-0">
          <div className="relative flex flex-col items-center">
            <div className={cn(
              'w-0.5 h-3',
              isFirst ? 'bg-transparent' : theme === 'dark' ? 'bg-slate-700' : 'bg-slate-300'
            )} />
            <div className={cn(
              'w-2.5 h-2.5 rounded-full border-2',
              isHead
                ? 'bg-green-500 border-green-400'
                : theme === 'dark'
                  ? 'bg-slate-700 border-slate-500'
                  : 'bg-white border-slate-400'
            )} />
            <div className={cn(
              'w-0.5 h-3',
              isLast ? 'bg-transparent' : theme === 'dark' ? 'bg-slate-700' : 'bg-slate-300'
            )} />
          </div>
        </div>

        <div className="flex-1 min-w-0 pl-2">
          <div className="flex items-center gap-2">
            <code className={cn(
              'text-[10px] font-mono',
              theme === 'dark' ? 'text-blue-400' : 'text-blue-600'
            )}>
              {commit.hash}
            </code>
            {isHead && (
              <span className={cn(
                'text-[9px] px-1 py-0.5 rounded font-medium',
                theme === 'dark' ? 'bg-green-900/30 text-green-400' : 'bg-green-100 text-green-700'
              )}>
                HEAD
              </span>
            )}
            <span className={cn(
              'text-xs truncate flex-1',
              theme === 'dark' ? 'text-slate-300' : 'text-slate-700'
            )}>
              {commit.message}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <User size={10} className={theme === 'dark' ? 'text-slate-500' : 'text-slate-400'} />
            <span className={cn('text-[10px]', theme === 'dark' ? 'text-slate-500' : 'text-slate-400')}>
              {commit.author_name}
            </span>
            <span className={theme === 'dark' ? 'text-slate-600' : 'text-slate-300'}>•</span>
            <span className={cn('text-[10px]', theme === 'dark' ? 'text-slate-500' : 'text-slate-400')}>
              {formatRelativeTime(commit.timestamp)}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {!isHead && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onRevert()
              }}
              disabled={isReverting}
              className={cn(
                'p-1 rounded transition-colors',
                isReverting
                  ? 'opacity-50 cursor-not-allowed'
                  : theme === 'dark'
                    ? 'hover:bg-slate-700 text-orange-400'
                    : 'hover:bg-slate-200 text-orange-600'
              )}
              title="回滚到此版本"
            >
              <RotateCcw size={12} className={isReverting ? 'animate-spin' : ''} />
            </button>
          )}
          <ChevronRight
            size={12}
            className={cn(
              'transition-transform',
              isExpanded ? 'rotate-90' : '',
              theme === 'dark' ? 'text-slate-500' : 'text-slate-400'
            )}
          />
        </div>
      </div>

      {isExpanded && (
        <div className={cn(
          'ml-10 mr-2 mb-2 p-2 rounded text-xs',
          theme === 'dark' ? 'bg-slate-800/80' : 'bg-slate-100'
        )}>
          <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
            <span className={theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}>时间:</span>
            <span className={theme === 'dark' ? 'text-slate-300' : 'text-slate-600'}>
              {formatFullTime(commit.timestamp)}
            </span>
            <span className={theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}>大小:</span>
            <span className={theme === 'dark' ? 'text-slate-300' : 'text-slate-600'}>
              {formatSize(commit.size)}
            </span>
          </div>
          <div className={cn(
            'mt-2 pt-2 border-t',
            theme === 'dark' ? 'border-slate-700' : 'border-slate-200'
          )}>
            <span className={theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}>消息:</span>
            <p className={cn('mt-1', theme === 'dark' ? 'text-slate-300' : 'text-slate-600')}>
              {commit.message}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
