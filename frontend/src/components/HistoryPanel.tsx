/**
 * 模块名称: HistoryPanel
 * 主要功能: Git 风格的版本历史面板，支持提交、回滚、查看历史、查看 diff
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
  Check,
  GitCompare,
  Eye
} from 'lucide-react'
import { cn } from '../lib/utils'
import { useThemeStore } from '../stores/useThemeStore'
import { roomsApi, HistoryResponse, CommitInfo, CreateCommitRequest } from '../services/api/rooms'
import { CommitDiffPanel } from './CommitDiffPanel'
import { useModal } from './Modal'
import { ContextMenu } from './ContextMenu'
import { yjsManager } from '../lib/yjs'

interface HistoryPanelProps {
  /** 房间 ID */
  roomId: string
}

/**
 * 格式化文件大小
 */
const formatSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/**
 * 格式化时间戳为相对时间
 */
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

/**
 * 格式化完整时间
 */
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

/**
 * 版本历史面板组件
 */
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

  // 自定义弹窗
  const { showAlert, showConfirm, showToast, ModalRenderer } = useModal()

  // 监听本地更改 - 简化版：监听 shapesMap 变化
  useEffect(() => {
    if (!roomId || !yjsManager.isConnected) return

    const shapesMap = yjsManager.shapesMap
    if (!shapesMap) return

    const handleChange = () => setHasLocalChanges(true)
    shapesMap.observeDeep(handleChange)

    return () => shapesMap.unobserveDeep(handleChange)
  }, [roomId])


  /**
   * 加载历史数据
   */
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

  // 监听 Awareness 变更：当其他用户提交时刷新历史
  useEffect(() => {
    if (!roomId || !yjsManager.isConnected) return

    const awareness = yjsManager.getAwareness()
    if (!awareness) return

    const handleAwarenessChange = () => {
      // 检查是否有其他用户发送了 history_changed 信号
      const states = awareness.getStates()
      states.forEach((state: any) => {
        if (state?.historyChanged && state.historyChanged > Date.now() - 5000) {
          // 5秒内的历史变更通知，刷新历史
          loadHistory()
        }
      })
    }

    awareness.on('change', handleAwarenessChange)
    return () => awareness.off('change', handleAwarenessChange)
  }, [roomId, loadHistory])

  /**
   * 创建提交
   */
  const handleCommit = async () => {
    if (!roomId || committing) return

    setCommitting(true)
    try {
      // 获取用户信息：从 localStorage 中读取 username 或 temp_username
      let authorName = 'Anonymous';
      const storedUsername = localStorage.getItem('username');
      if (storedUsername) {
        authorName = storedUsername;
      } else {
        // 如果没有登录用户名，尝试从 localStorage 获取临时用户名
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
      setHasLocalChanges(false) // 重置本地更改状态

      // 通过 Awareness 广播历史变更通知，让其他协作者刷新历史
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

  /**
   * 回滚到指定提交
   */
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

  /**
   * 检出指定提交 (预览历史版本，不创建新提交)
   */
  const handleCheckout = (commitId: number, commitHash: string) => {
    if (!roomId) return

    showConfirm(
      '检出此版本将丢弃当前未保存的更改，确定继续吗？\n\n提示：检出后可以继续编辑，编辑内容会基于此版本。',
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

  /**
   * 预览提交 (按住时)
   */
  const handlePreviewStart = async (commitId: number) => {
    if (!roomId) return
    try {
      const data = await roomsApi.getCommitData(roomId, commitId)
      yjsManager.previewData(data)
    } catch (err) {
      console.error('预览失败:', err)
    }
  }

  const handlePreviewEnd = () => {
    yjsManager.exitPreview()
  }

  useEffect(() => {
    loadHistory()
    // 每10秒轮询刷新历史（之前是30秒，缩短以提高实时性）
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

      {/* Git Graph 样式的历史列表 */}
      <div className="flex-1 overflow-y-auto">
        {/* 未提交的更改 */}
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

        {/* 提交列表 */}
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
              onPreviewStart={() => handlePreviewStart(commit.id)}
              onPreviewEnd={handlePreviewEnd}
            />
          )
        })}

        {/* 空状态 */}
        {(!history || (history.commits.length === 0 && !hasUncommittedChanges)) && (
          <div className={cn('flex flex-col items-center justify-center py-8', theme === 'dark' ? 'text-slate-500' : 'text-slate-400')}>
            <Clock size={32} className="mb-3 opacity-40" />
            <span className="text-sm">暂无提交历史</span>
            <span className="text-xs mt-1 opacity-70">开始绘制后将自动记录</span>
          </div>
        )}
      </div>

      {/* 右键菜单 */}
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
            {
              label: '查看差异',
              disabled: !contextMenu.commit.parent_id,
              onClick: () => setDiffCommitId(contextMenu.commit.id)
            },
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

      {/* 底部状态栏 */}
      {history && (
        <div className={cn(
          'flex items-center justify-between px-3 py-1.5 border-t text-[10px]',
          theme === 'dark' ? 'border-slate-700 bg-slate-900/50 text-slate-500' : 'border-slate-200 bg-slate-50 text-slate-400'
        )}>
          <span>{history.commits.length} 个提交</span>
          <span>{formatSize(history.total_size)}</span>
        </div>
      )}

      {/* Modal 渲染器 */}
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

/**
 * 提交节点组件
 */
const CommitNode: React.FC<CommitNodeProps> = ({
  commit,
  roomId,
  isHead,
  isFirst,
  isLast,
  isExpanded,
  isReverting,
  showingDiff,
  theme,
  onToggle,
  onRevert,
  onShowDiff,
  onContextMenu,
  onPreviewStart,
  onPreviewEnd,
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
        {/* Graph 线条和节点 */}
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

        {/* 提交信息 */}
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

        {/* 操作按钮 */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {/* 查看 diff */}
          <button
            onClick={(e) => {
              e.stopPropagation()
              onShowDiff()
            }}
            className={cn(
              'p-1 rounded transition-colors',
              showingDiff
                ? theme === 'dark'
                  ? 'bg-blue-900/50 text-blue-400'
                  : 'bg-blue-100 text-blue-600'
                : theme === 'dark'
                  ? 'hover:bg-slate-700 text-slate-400'
                  : 'hover:bg-slate-200 text-slate-500'
            )}
            title={showingDiff ? '关闭差异视图' : '查看与上一版本的差异'}
          >
            <GitCompare size={12} />
          </button>
          {!isHead && (
            <>
              <button
                onMouseDown={(e) => {
                  e.stopPropagation()
                  onPreviewStart()
                }}
                onMouseUp={(e) => {
                  e.stopPropagation()
                  onPreviewEnd()
                }}
                onMouseLeave={(e) => {
                  e.stopPropagation()
                  onPreviewEnd()
                }}
                onTouchStart={(e) => {
                  e.stopPropagation()
                  onPreviewStart()
                }}
                onTouchEnd={(e) => {
                  e.stopPropagation()
                  onPreviewEnd()
                }}
                className={cn(
                  'p-1 rounded transition-colors',
                  theme === 'dark'
                    ? 'hover:bg-slate-700 text-cyan-400'
                    : 'hover:bg-slate-200 text-cyan-600'
                )}
                title="按住预览"
              >
                <Eye size={12} />
              </button>
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
            </>
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

      {/* 展开详情 */}
      {isExpanded && (
        <div className={cn(
          'ml-10 mr-2 mb-2 p-2 rounded text-xs',
          theme === 'dark' ? 'bg-slate-800/80' : 'bg-slate-100'
        )}>
          <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
            <span className={theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}>哈希:</span>
            <code className={cn('font-mono', theme === 'dark' ? 'text-slate-300' : 'text-slate-600')}>
              {commit.hash}
            </code>

            <span className={theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}>作者:</span>
            <span className={theme === 'dark' ? 'text-slate-300' : 'text-slate-600'}>
              {commit.author_name}
            </span>

            <span className={theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}>时间:</span>
            <span className={theme === 'dark' ? 'text-slate-300' : 'text-slate-600'}>
              {formatFullTime(commit.timestamp)}
            </span>

            <span className={theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}>大小:</span>
            <span className={theme === 'dark' ? 'text-slate-300' : 'text-slate-600'}>
              {formatSize(commit.size)}
            </span>

            {commit.parent_id && (
              <>
                <span className={theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}>父提交:</span>
                <span className={theme === 'dark' ? 'text-slate-300' : 'text-slate-600'}>
                  #{commit.parent_id}
                </span>
              </>
            )}
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

          {/* 在详情中显示 diff 按钮 */}
          <div className={cn(
            'mt-2 pt-2 border-t',
            theme === 'dark' ? 'border-slate-700' : 'border-slate-200'
          )}>
            <button
              onClick={onShowDiff}
              className={cn(
                'flex items-center gap-1.5 px-2 py-1 text-[10px] rounded transition-colors',
                showingDiff
                  ? theme === 'dark'
                    ? 'bg-blue-900/50 text-blue-400'
                    : 'bg-blue-100 text-blue-600'
                  : theme === 'dark'
                    ? 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                    : 'bg-slate-200 hover:bg-slate-300 text-slate-600'
              )}
            >
              <GitCompare size={10} />
              {showingDiff ? '隐藏差异' : '查看与上一版本的差异'}
            </button>
          </div>
        </div>
      )}

      {/* Diff 面板 */}
      {showingDiff && (
        <div className="ml-10 mr-2 mb-2">
          <CommitDiffPanel
            roomId={roomId}
            commit={commit}
            onClose={onShowDiff}
            inline
          />
        </div>
      )}
    </div>
  )
}
