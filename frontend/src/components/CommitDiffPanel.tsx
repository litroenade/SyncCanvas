/**
 * 模块名称: CommitDiffPanel
 * 主要功能: 显示两个提交之间的差异
 */

import React, { useEffect, useState } from 'react'
import {
  Plus,
  Minus,
  Edit3,
  ArrowRight,
  X,
  Loader2,
  FileText,
  Hash,
} from 'lucide-react'
import { cn } from '../lib/utils'
import { useThemeStore } from '../stores/useThemeStore'
import { roomsApi, CommitDiffResponse, CommitInfo, StrokeChange } from '../services/api/rooms'

interface CommitDiffPanelProps {
  /** 房间 ID */
  roomId: string
  /** 目标提交 */
  commit: CommitInfo
  /** 基准提交 ID (可选) */
  baseCommitId?: number
  /** 关闭回调 */
  onClose: () => void
  /** 是否内联显示 (默认模态框) */
  inline?: boolean
}

/**
 * 格式化文件大小
 */
const formatSize = (bytes: number): string => {
  const abs = Math.abs(bytes)
  if (abs < 1024) return `${bytes} B`
  if (abs < 1024 * 1024) return `${bytes > 0 ? '+' : ''}${(bytes / 1024).toFixed(1)} KB`
  return `${bytes > 0 ? '+' : ''}${(bytes / (1024 * 1024)).toFixed(1)} MB`
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
  })
}

/**
 * 变更图标组件
 */
const ChangeIcon: React.FC<{ action: StrokeChange['action']; theme: 'light' | 'dark' }> = ({ action, theme }) => {
  switch (action) {
    case 'added':
      return <Plus size={12} className={theme === 'dark' ? 'text-green-400' : 'text-green-600'} />
    case 'removed':
      return <Minus size={12} className={theme === 'dark' ? 'text-red-400' : 'text-red-600'} />
    case 'modified':
      return <Edit3 size={12} className={theme === 'dark' ? 'text-amber-400' : 'text-amber-600'} />
    default:
      return null
  }
}

/**
 * 提交差异面板组件
 */
export const CommitDiffPanel: React.FC<CommitDiffPanelProps> = ({
  roomId,
  commit,
  baseCommitId,
  onClose,
  inline = false,
}) => {
  const { theme } = useThemeStore()
  const [diff, setDiff] = useState<CommitDiffResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadDiff = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await roomsApi.getCommitDiff(roomId, commit.id, baseCommitId)
        setDiff(data)
      } catch (err: any) {
        console.error('加载差异失败:', err)
        setError(err.response?.data?.detail || '加载失败')
      } finally {
        setLoading(false)
      }
    }
    loadDiff()
  }, [roomId, commit.id, baseCommitId])

  if (loading) {
    if (inline) {
      return (
        <div className={cn(
          'p-3 rounded text-xs',
          theme === 'dark' ? 'bg-slate-800/80' : 'bg-slate-100'
        )}>
          <div className="flex items-center justify-center gap-2">
            <Loader2 className="animate-spin" size={14} />
            <span className={theme === 'dark' ? 'text-slate-400' : 'text-slate-500'}>
              加载中...
            </span>
          </div>
        </div>
      )
    }
    return (
      <div className={cn(
        'fixed inset-0 z-50 flex items-center justify-center bg-black/50'
      )}>
        <div className={cn(
          'w-96 p-6 rounded-lg shadow-xl',
          theme === 'dark' ? 'bg-slate-800' : 'bg-white'
        )}>
          <div className="flex items-center justify-center gap-2">
            <Loader2 className="animate-spin" size={20} />
            <span className={theme === 'dark' ? 'text-slate-300' : 'text-slate-600'}>
              加载中...
            </span>
          </div>
        </div>
      </div>
    )
  }

  if (error || !diff) {
    if (inline) {
      return (
        <div className={cn(
          'p-3 rounded text-xs',
          theme === 'dark' ? 'bg-slate-800/80' : 'bg-slate-100'
        )}>
          <div className="text-center">
            <p className={theme === 'dark' ? 'text-red-400' : 'text-red-500'}>
              {error || '加载失败'}
            </p>
            <button
              onClick={onClose}
              className={cn(
                'mt-2 px-2 py-1 rounded text-[10px]',
                theme === 'dark'
                  ? 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                  : 'bg-slate-200 hover:bg-slate-300 text-slate-600'
              )}
            >
              关闭
            </button>
          </div>
        </div>
      )
    }
    return (
      <div className={cn(
        'fixed inset-0 z-50 flex items-center justify-center bg-black/50'
      )}>
        <div className={cn(
          'w-96 p-6 rounded-lg shadow-xl',
          theme === 'dark' ? 'bg-slate-800' : 'bg-white'
        )}>
          <div className="text-center">
            <p className={theme === 'dark' ? 'text-red-400' : 'text-red-500'}>
              {error || '加载失败'}
            </p>
            <button
              onClick={onClose}
              className={cn(
                'mt-4 px-4 py-2 rounded text-sm',
                theme === 'dark'
                  ? 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                  : 'bg-slate-200 hover:bg-slate-300 text-slate-700'
              )}
            >
              关闭
            </button>
          </div>
        </div>
      </div>
    )
  }

  const totalChanges = diff.strokes_added + diff.strokes_removed + diff.strokes_modified

  // 内联模式的紧凑渲染
  if (inline) {
    return (
      <div className={cn(
        'rounded border text-xs',
        theme === 'dark' ? 'bg-slate-800/80 border-slate-700' : 'bg-slate-100 border-slate-200'
      )}>
        {/* 头部 - 紧凑 */}
        <div className={cn(
          'flex items-center justify-between px-2 py-1.5 border-b',
          theme === 'dark' ? 'border-slate-700' : 'border-slate-200'
        )}>
          <div className="flex items-center gap-1.5">
            <FileText size={12} className={theme === 'dark' ? 'text-blue-400' : 'text-blue-600'} />
            <span className={theme === 'dark' ? 'text-slate-300' : 'text-slate-600'}>
              差异详情
            </span>
          </div>
          <button
            onClick={onClose}
            className={cn(
              'p-0.5 rounded transition-colors',
              theme === 'dark' ? 'hover:bg-slate-700 text-slate-400' : 'hover:bg-slate-200 text-slate-500'
            )}
          >
            <X size={12} />
          </button>
        </div>

        {/* 提交对比 - 紧凑 */}
        <div className={cn(
          'flex items-center gap-2 px-2 py-1.5 border-b',
          theme === 'dark' ? 'border-slate-700' : 'border-slate-200'
        )}>
          <code className={cn('font-mono text-[10px]', theme === 'dark' ? 'text-blue-400' : 'text-blue-600')}>
            {diff.from_commit?.hash || '(初始)'}
          </code>
          <ArrowRight size={10} className={theme === 'dark' ? 'text-slate-500' : 'text-slate-400'} />
          <code className={cn('font-mono text-[10px]', theme === 'dark' ? 'text-blue-400' : 'text-blue-600')}>
            {diff.to_commit.hash}
          </code>
        </div>

        {/* 统计 - 紧凑 */}
        <div className={cn(
          'flex items-center gap-2 px-2 py-1 border-b text-[10px] flex-wrap',
          theme === 'dark' ? 'border-slate-700 bg-slate-900/30' : 'border-slate-200 bg-slate-50'
        )}>
          <span className={theme === 'dark' ? 'text-slate-400' : 'text-slate-500'}>
            {totalChanges} 变更
          </span>
          {diff.strokes_added > 0 && (
            <span className={theme === 'dark' ? 'text-green-400' : 'text-green-600'}>
              +{diff.strokes_added}
            </span>
          )}
          {diff.strokes_removed > 0 && (
            <span className={theme === 'dark' ? 'text-red-400' : 'text-red-600'}>
              -{diff.strokes_removed}
            </span>
          )}
          {diff.strokes_modified > 0 && (
            <span className={theme === 'dark' ? 'text-amber-400' : 'text-amber-600'}>
              ~{diff.strokes_modified}
            </span>
          )}
          <span className={cn(
            'ml-auto',
            diff.size_diff >= 0
              ? theme === 'dark' ? 'text-green-400' : 'text-green-600'
              : theme === 'dark' ? 'text-red-400' : 'text-red-600'
          )}>
            {formatSize(diff.size_diff)}
          </span>
        </div>

        {/* 变更列表 - 紧凑 */}
        <div className="max-h-32 overflow-y-auto">
          {diff.changes.length === 0 ? (
            <div className={cn(
              'py-2 text-center text-[10px]',
              theme === 'dark' ? 'text-slate-500' : 'text-slate-400'
            )}>
              无可检测的变更
            </div>
          ) : (
            <div className={cn('divide-y', theme === 'dark' ? 'divide-slate-700/50' : 'divide-slate-200/50')}>
              {diff.changes.slice(0, 10).map((change, index) => (
                <div
                  key={index}
                  className={cn(
                    'flex items-center gap-2 px-2 py-1 text-[10px]',
                    theme === 'dark' ? 'hover:bg-slate-700/30' : 'hover:bg-slate-50'
                  )}
                >
                  <ChangeIcon action={change.action} theme={theme} />
                  <code className={cn(
                    'font-mono truncate flex-1',
                    theme === 'dark' ? 'text-slate-400' : 'text-slate-500'
                  )}>
                    {change.shape_id.substring(0, 12)}...
                  </code>
                  {change.stroke_type && (
                    <span className={cn(
                      'px-1 py-0.5 rounded text-[9px]',
                      theme === 'dark' ? 'bg-slate-700 text-slate-400' : 'bg-slate-200 text-slate-500'
                    )}>
                      {change.stroke_type}
                    </span>
                  )}
                </div>
              ))}
              {diff.changes.length > 10 && (
                <div className={cn(
                  'px-2 py-1 text-center text-[10px]',
                  theme === 'dark' ? 'text-slate-500' : 'text-slate-400'
                )}>
                  还有 {diff.changes.length - 10} 项变更...
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    )
  }

  // 模态框模式
  return (
    <div className={cn(
      'fixed inset-0 z-50 flex items-center justify-center bg-black/50'
    )}>
      <div className={cn(
        'w-[600px] max-h-[80vh] rounded-lg shadow-xl overflow-hidden flex flex-col',
        theme === 'dark' ? 'bg-slate-800' : 'bg-white'
      )}>
        {/* 头部 */}
        <div className={cn(
          'flex items-center justify-between px-4 py-3 border-b',
          theme === 'dark' ? 'border-slate-700 bg-slate-900/50' : 'border-slate-200 bg-slate-50'
        )}>
          <div className="flex items-center gap-2">
            <FileText size={16} className={theme === 'dark' ? 'text-blue-400' : 'text-blue-600'} />
            <span className={cn('font-medium', theme === 'dark' ? 'text-slate-200' : 'text-slate-800')}>
              提交差异
            </span>
          </div>
          <button
            onClick={onClose}
            className={cn(
              'p-1 rounded hover:bg-opacity-80 transition-colors',
              theme === 'dark' ? 'hover:bg-slate-700 text-slate-400' : 'hover:bg-slate-200 text-slate-500'
            )}
          >
            <X size={18} />
          </button>
        </div>

        {/* 提交对比信息 */}
        <div className={cn(
          'px-4 py-3 border-b',
          theme === 'dark' ? 'border-slate-700' : 'border-slate-200'
        )}>
          <div className="flex items-center gap-3">
            {/* 基准提交 */}
            <div className={cn(
              'flex-1 p-2 rounded text-xs',
              theme === 'dark' ? 'bg-slate-900/50' : 'bg-slate-100'
            )}>
              {diff.from_commit ? (
                <>
                  <div className="flex items-center gap-1 mb-1">
                    <Hash size={10} className={theme === 'dark' ? 'text-slate-500' : 'text-slate-400'} />
                    <code className={cn('font-mono', theme === 'dark' ? 'text-blue-400' : 'text-blue-600')}>
                      {diff.from_commit.hash}
                    </code>
                  </div>
                  <div className={cn('truncate', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
                    {diff.from_commit.message}
                  </div>
                </>
              ) : (
                <span className={theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}>
                  (初始状态)
                </span>
              )}
            </div>

            <ArrowRight size={16} className={theme === 'dark' ? 'text-slate-500' : 'text-slate-400'} />

            {/* 目标提交 */}
            <div className={cn(
              'flex-1 p-2 rounded text-xs',
              theme === 'dark' ? 'bg-slate-900/50' : 'bg-slate-100'
            )}>
              <div className="flex items-center gap-1 mb-1">
                <Hash size={10} className={theme === 'dark' ? 'text-slate-500' : 'text-slate-400'} />
                <code className={cn('font-mono', theme === 'dark' ? 'text-blue-400' : 'text-blue-600')}>
                  {diff.to_commit.hash}
                </code>
              </div>
              <div className={cn('truncate', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
                {diff.to_commit.message}
              </div>
            </div>
          </div>
        </div>

        {/* 统计摘要 */}
        <div className={cn(
          'flex items-center gap-4 px-4 py-2 border-b text-xs',
          theme === 'dark' ? 'border-slate-700 bg-slate-900/30' : 'border-slate-200 bg-slate-50'
        )}>
          <span className={theme === 'dark' ? 'text-slate-400' : 'text-slate-500'}>
            {totalChanges} 处变更
          </span>
          {diff.strokes_added > 0 && (
            <span className={theme === 'dark' ? 'text-green-400' : 'text-green-600'}>
              +{diff.strokes_added} 新增
            </span>
          )}
          {diff.strokes_removed > 0 && (
            <span className={theme === 'dark' ? 'text-red-400' : 'text-red-600'}>
              -{diff.strokes_removed} 删除
            </span>
          )}
          {diff.strokes_modified > 0 && (
            <span className={theme === 'dark' ? 'text-amber-400' : 'text-amber-600'}>
              ~{diff.strokes_modified} 修改
            </span>
          )}
          <span className={cn(
            'ml-auto',
            diff.size_diff >= 0
              ? theme === 'dark' ? 'text-green-400' : 'text-green-600'
              : theme === 'dark' ? 'text-red-400' : 'text-red-600'
          )}>
            {formatSize(diff.size_diff)}
          </span>
        </div>

        {/* 变更列表 */}
        <div className="flex-1 overflow-y-auto">
          {diff.changes.length === 0 ? (
            <div className={cn(
              'flex items-center justify-center py-8',
              theme === 'dark' ? 'text-slate-500' : 'text-slate-400'
            )}>
              无可检测的变更
            </div>
          ) : (
            <div className={cn('divide-y', theme === 'dark' ? 'divide-slate-700/50' : 'divide-slate-200/50')}>
              {diff.changes.map((change, index) => (
                <div
                  key={index}
                  className={cn(
                    'flex items-center gap-3 px-4 py-2 text-xs',
                    theme === 'dark' ? 'hover:bg-slate-700/30' : 'hover:bg-slate-50'
                  )}
                >
                  <ChangeIcon action={change.action} theme={theme} />
                  <code className={cn(
                    'font-mono truncate flex-1',
                    theme === 'dark' ? 'text-slate-300' : 'text-slate-600'
                  )}>
                    {change.shape_id.substring(0, 16)}...
                  </code>
                  {change.stroke_type && (
                    <span className={cn(
                      'px-1.5 py-0.5 rounded text-[10px]',
                      theme === 'dark' ? 'bg-slate-700 text-slate-400' : 'bg-slate-200 text-slate-500'
                    )}>
                      {change.stroke_type}
                    </span>
                  )}
                  {change.points_count !== null && (
                    <span className={theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}>
                      {change.points_count} 点
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 底部 */}
        <div className={cn(
          'flex items-center justify-between px-4 py-2 border-t text-xs',
          theme === 'dark' ? 'border-slate-700 bg-slate-900/50' : 'border-slate-200 bg-slate-50'
        )}>
          <span className={theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}>
            {formatFullTime(commit.timestamp)}
          </span>
          <span className={theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}>
            {commit.author_name}
          </span>
        </div>
      </div>
    </div>
  )
}
