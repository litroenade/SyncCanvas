/**
 * 房间列表页面
 *
 * 模块名称: Rooms
 * 主要功能: 展示房间列表、创建房间、加入房间
 */

import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Plus,
  Users,
  Lock,
  Globe,
  ArrowRight,
  Loader2,
  Trash2,
  Link as LinkIcon,
  LogOut,
  Sun,
  Moon,
} from 'lucide-react'
import { roomsApi, Room, CreateRoomRequest } from '../services/api/rooms'
import { useThemeStore } from '../stores/useThemeStore'
import { cn } from '../lib/utils'
import { useModal } from '../components/common/Modal'

/**
 * 房间列表页面组件
 */
export const Rooms: React.FC = () => {
  const navigate = useNavigate()
  const { theme, toggleTheme } = useThemeStore()
  const [rooms, setRooms] = useState<Room[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showJoinModal, setShowJoinModal] = useState<Room | null>(null)

  // 自定义弹窗
  const { showAlert, showConfirm, showToast, ModalRenderer } = useModal()

  const isLoggedIn = !!localStorage.getItem('token')
  const isGuest = localStorage.getItem('isGuest') === 'true'
  const username = localStorage.getItem('username') || 'Guest'

  useEffect(() => {
    loadRooms()
  }, [])

  const loadRooms = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await roomsApi.list()
      setRooms(response.rooms)
    } catch (err: any) {
      setError(err.response?.data?.detail || '加载房间列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    navigate('/login')
  }

  const handleGuestLogin = () => {
    localStorage.removeItem('isGuest')
    localStorage.removeItem('username')
    navigate('/login')
  }

  const handleEnterRoom = (roomId: string) => {
    // 设置当前房间 ID 并跳转到画布
    localStorage.setItem('currentRoomId', roomId)
    navigate(`/room/${roomId}`)
  }

  const [showDeleteModal, setShowDeleteModal] = useState<Room | null>(null)

  const handleDeleteRoom = async (room: Room, password?: string) => {
    if (room.has_password && !password) {
      // 需要密码，显示删除密码弹窗
      setShowDeleteModal(room)
      return
    }

    showConfirm(
      '确定要删除这个房间吗？此操作不可撤销。',
      async () => {
        try {
          await roomsApi.delete(room.id, password)
          showToast('房间已删除', 'success')
          loadRooms()
        } catch (err: any) {
          showAlert(err.response?.data?.detail || '删除失败', { type: 'error', title: '删除失败' })
        }
      },
      { title: '删除房间', type: 'danger' }
    )
  }

  const handleCopyInvite = async (roomId: string) => {
    try {
      const { invite_url } = await roomsApi.getInviteLink(roomId)
      const fullUrl = `${window.location.origin}${invite_url}`
      await navigator.clipboard.writeText(fullUrl)
      showToast('邀请链接已复制到剪贴板', 'success')
    } catch (err) {
      showAlert('复制邀请链接失败', { type: 'error' })
    }
  }

  return (
    <div
      className={cn(
        'min-h-screen transition-colors',
        theme === 'dark' ? 'bg-slate-900 text-slate-100' : 'bg-gray-50 text-slate-800'
      )}
    >
      {/* 顶部导航栏 */}
      <header
        className={cn(
          'sticky top-0 z-10 border-b backdrop-blur-md',
          theme === 'dark' ? 'bg-slate-900/80 border-slate-700' : 'bg-white/80 border-slate-200'
        )}
      >
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-bold text-lg">
              S
            </div>
            <h1 className="text-xl font-bold">SyncCanvas</h1>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={toggleTheme}
              className={cn(
                'p-2 rounded-lg transition-colors',
                theme === 'dark' ? 'hover:bg-slate-800' : 'hover:bg-slate-100'
              )}
            >
              {theme === 'dark' ? <Moon size={20} /> : <Sun size={20} />}
            </button>

            {(isLoggedIn || isGuest) && (
              <>
                <span className={cn('text-sm', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
                  {isGuest ? 'Guest' : username}
                </span>
                <button
                  onClick={isGuest ? handleGuestLogin : handleLogout}
                  className={cn(
                    'p-2 rounded-lg transition-colors',
                    theme === 'dark' ? 'hover:bg-slate-800 text-slate-400' : 'hover:bg-slate-100 text-slate-500'
                  )}
                  title={isGuest ? "登录" : "退出登录"}
                >
                  <LogOut size={20} />
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* 标题和操作栏 */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold mb-1">协作房间</h2>
            <p className={cn('text-sm', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
              选择一个房间开始协作，或创建新房间
            </p>
          </div>

          {isLoggedIn && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-lg hover:from-blue-600 hover:to-indigo-700 transition-all shadow-lg shadow-blue-500/25"
            >
              <Plus size={20} />
              创建房间
            </button>
          )}
        </div>

        {/* 加载状态 */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          </div>
        )}

        {/* 错误提示 */}
        {error && (
          <div className="bg-red-500/10 text-red-500 p-4 rounded-xl mb-6 text-center">{error}</div>
        )}

        {/* 空状态 */}
        {!loading && !error && rooms.length === 0 && (
          <div
            className={cn(
              'text-center py-20 rounded-2xl border-2 border-dashed',
              theme === 'dark' ? 'border-slate-700' : 'border-slate-200'
            )}
          >
            <Users className="w-16 h-16 mx-auto mb-4 text-slate-400" />
            <h3 className="text-lg font-medium mb-2">还没有房间</h3>
            <p className={cn('text-sm mb-6', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
              创建一个房间开始协作吧
            </p>
            {isLoggedIn && (
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
              >
                创建第一个房间
              </button>
            )}
          </div>
        )}

        {/* 房间列表 */}
        {!loading && !error && rooms.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {rooms.map((room) => (
              <RoomCard
                key={room.id}
                room={room}
                theme={theme}
                onEnter={() => {
                  if (room.has_password) {
                    setShowJoinModal(room)
                  } else {
                    handleEnterRoom(room.id)
                  }
                }}
                onDelete={() => handleDeleteRoom(room)}
                onCopyInvite={() => handleCopyInvite(room.id)}
                isOwner={isLoggedIn} // 简化处理，实际应检查 owner_id
              />
            ))}
          </div>
        )}
      </main>

      {/* 创建房间弹窗 */}
      {showCreateModal && (
        <CreateRoomModal
          theme={theme}
          onClose={() => setShowCreateModal(false)}
          onCreated={(room) => {
            setShowCreateModal(false)
            loadRooms()
            handleEnterRoom(room.id)
          }}
        />
      )}

      {/* 加入房间弹窗 (需要密码) */}
      {showJoinModal && (
        <JoinRoomModal
          room={showJoinModal}
          theme={theme}
          onClose={() => setShowJoinModal(null)}
          onJoined={() => {
            setShowJoinModal(null)
            handleEnterRoom(showJoinModal.id)
          }}
        />
      )}

      {/* 删除房间弹窗 (需要密码) */}
      {showDeleteModal && (
        <DeleteRoomModal
          room={showDeleteModal}
          theme={theme}
          onClose={() => setShowDeleteModal(null)}
          onDeleted={() => {
            setShowDeleteModal(null)
            loadRooms()
          }}
        />
      )}

      {/* Modal 渲染器 */}
      <ModalRenderer />
    </div>
  )
}

/**
 * 房间卡片组件
 */
interface RoomCardProps {
  room: Room
  theme: 'light' | 'dark'
  onEnter: () => void
  onDelete: () => void
  onCopyInvite: () => void
  isOwner: boolean
}

const RoomCard: React.FC<RoomCardProps> = ({ room, theme, onEnter, onDelete, onCopyInvite, isOwner }) => {
  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div
      className={cn(
        'group relative p-5 rounded-2xl border transition-all hover:shadow-lg cursor-pointer',
        theme === 'dark'
          ? 'bg-slate-800/50 border-slate-700 hover:border-slate-600'
          : 'bg-white border-slate-200 hover:border-slate-300'
      )}
      onClick={onEnter}
    >
      {/* 房间图标 */}
      <div className="flex items-start justify-between mb-4">
        <div
          className={cn(
            'w-12 h-12 rounded-xl flex items-center justify-center text-lg font-bold',
            room.is_public
              ? 'bg-green-500/10 text-green-500'
              : 'bg-amber-500/10 text-amber-500'
          )}
        >
          {room.is_public ? <Globe size={24} /> : <Lock size={24} />}
        </div>

        {/* 操作按钮 */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={(e) => {
              e.stopPropagation()
              onCopyInvite()
            }}
            className={cn(
              'p-2 rounded-lg transition-colors',
              theme === 'dark' ? 'hover:bg-slate-700' : 'hover:bg-slate-100'
            )}
            title="复制邀请链接"
          >
            <LinkIcon size={16} />
          </button>
          {isOwner && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDelete()
              }}
              className="p-2 rounded-lg hover:bg-red-500/10 text-red-500 transition-colors"
              title="删除房间"
            >
              <Trash2 size={16} />
            </button>
          )}
        </div>
      </div>

      {/* 房间名称 */}
      <h3 className="font-semibold text-lg mb-2 truncate">{room.name}</h3>

      {/* 房间信息 */}
      <div className={cn('flex items-center gap-4 text-sm', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
        <span className="flex items-center gap-1">
          <Users size={14} />
          {room.member_count}/{room.max_users}
        </span>
        {room.has_password && (
          <span className="flex items-center gap-1">
            <Lock size={14} />
            需要密码
          </span>
        )}
      </div>

      {/* 创建时间 */}
      <div className={cn('mt-3 text-xs', theme === 'dark' ? 'text-slate-500' : 'text-slate-400')}>
        创建于 {formatDate(room.created_at)}
      </div>

      {/* 进入箭头 */}
      <div className="absolute right-4 bottom-4 opacity-0 group-hover:opacity-100 transition-opacity">
        <ArrowRight size={20} className="text-blue-500" />
      </div>
    </div>
  )
}

/**
 * 创建房间弹窗
 */
interface CreateRoomModalProps {
  theme: 'light' | 'dark'
  onClose: () => void
  onCreated: (room: Room) => void
}

const CreateRoomModal: React.FC<CreateRoomModalProps> = ({ theme, onClose, onCreated }) => {
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [isPublic, setIsPublic] = useState(true)
  const [maxUsers, setMaxUsers] = useState(10)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return

    setLoading(true)
    setError(null)

    try {
      const data: CreateRoomRequest = {
        name: name.trim(),
        is_public: isPublic,
        max_users: maxUsers,
      }
      if (password) {
        data.password = password
      }

      const room = await roomsApi.create(data)
      onCreated(room)
    } catch (err: any) {
      setError(err.response?.data?.detail || '创建失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div
        className={cn(
          'w-full max-w-md p-6 rounded-2xl shadow-xl',
          theme === 'dark' ? 'bg-slate-800' : 'bg-white'
        )}
      >
        <h2 className="text-xl font-bold mb-6">创建新房间</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 房间名称 */}
          <div>
            <label className={cn('block text-sm font-medium mb-2', theme === 'dark' ? 'text-slate-300' : 'text-slate-700')}>
              房间名称
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="输入房间名称"
              className={cn(
                'w-full px-4 py-3 rounded-xl border outline-none transition-colors',
                theme === 'dark'
                  ? 'bg-slate-900 border-slate-700 focus:border-blue-500'
                  : 'bg-gray-50 border-slate-200 focus:border-blue-500'
              )}
              required
            />
          </div>

          {/* 房间密码 */}
          <div>
            <label className={cn('block text-sm font-medium mb-2', theme === 'dark' ? 'text-slate-300' : 'text-slate-700')}>
              房间密码 (可选)
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="留空表示无密码"
              className={cn(
                'w-full px-4 py-3 rounded-xl border outline-none transition-colors',
                theme === 'dark'
                  ? 'bg-slate-900 border-slate-700 focus:border-blue-500'
                  : 'bg-gray-50 border-slate-200 focus:border-blue-500'
              )}
            />
          </div>

          {/* 公开设置 */}
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="isPublic"
              checked={isPublic}
              onChange={(e) => setIsPublic(e.target.checked)}
              className="w-5 h-5 rounded"
            />
            <label htmlFor="isPublic" className="text-sm">
              公开房间 (所有人可见)
            </label>
          </div>

          {/* 最大人数 */}
          <div>
            <label className={cn('block text-sm font-medium mb-2', theme === 'dark' ? 'text-slate-300' : 'text-slate-700')}>
              最大人数: {maxUsers}
            </label>
            <input
              type="range"
              min="2"
              max="50"
              value={maxUsers}
              onChange={(e) => setMaxUsers(parseInt(e.target.value))}
              className="w-full"
            />
          </div>

          {/* 错误提示 */}
          {error && <div className="text-red-500 text-sm">{error}</div>}

          {/* 按钮 */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className={cn(
                'flex-1 py-3 rounded-xl font-medium transition-colors',
                theme === 'dark' ? 'bg-slate-700 hover:bg-slate-600' : 'bg-slate-100 hover:bg-slate-200'
              )}
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="flex-1 py-3 bg-blue-500 text-white rounded-xl font-medium hover:bg-blue-600 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              创建
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

/**
 * 加入房间弹窗 (需要密码)
 */
interface JoinRoomModalProps {
  room: Room
  theme: 'light' | 'dark'
  onClose: () => void
  onJoined: () => void
}

const JoinRoomModal: React.FC<JoinRoomModalProps> = ({ room, theme, onClose, onJoined }) => {
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    setLoading(true)
    setError(null)

    try {
      await roomsApi.join(room.id, password)
      onJoined()
    } catch (err: any) {
      setError(err.response?.data?.detail || '加入失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div
        className={cn(
          'w-full max-w-md p-6 rounded-2xl shadow-xl',
          theme === 'dark' ? 'bg-slate-800' : 'bg-white'
        )}
      >
        <h2 className="text-xl font-bold mb-2">加入房间</h2>
        <p className={cn('text-sm mb-6', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
          房间 "{room.name}" 需要密码
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={cn('block text-sm font-medium mb-2', theme === 'dark' ? 'text-slate-300' : 'text-slate-700')}>
              房间密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="输入房间密码"
              className={cn(
                'w-full px-4 py-3 rounded-xl border outline-none transition-colors',
                theme === 'dark'
                  ? 'bg-slate-900 border-slate-700 focus:border-blue-500'
                  : 'bg-gray-50 border-slate-200 focus:border-blue-500'
              )}
              autoFocus
            />
          </div>

          {error && <div className="text-red-500 text-sm">{error}</div>}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className={cn(
                'flex-1 py-3 rounded-xl font-medium transition-colors',
                theme === 'dark' ? 'bg-slate-700 hover:bg-slate-600' : 'bg-slate-100 hover:bg-slate-200'
              )}
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-3 bg-blue-500 text-white rounded-xl font-medium hover:bg-blue-600 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              加入
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

/**
 * 删除房间弹窗 (需要密码)
 */
interface DeleteRoomModalProps {
  room: Room
  theme: 'light' | 'dark'
  onClose: () => void
  onDeleted: () => void
}

const DeleteRoomModal: React.FC<DeleteRoomModalProps> = ({ room, theme, onClose, onDeleted }) => {
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    setLoading(true)
    setError(null)

    try {
      await roomsApi.delete(room.id, password)
      onDeleted()
    } catch (err: any) {
      setError(err.response?.data?.detail || '删除失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div
        className={cn(
          'w-full max-w-md p-6 rounded-2xl shadow-xl',
          theme === 'dark' ? 'bg-slate-800' : 'bg-white'
        )}
      >
        <h2 className="text-xl font-bold mb-2 text-red-500">删除房间</h2>
        <p className={cn('text-sm mb-6', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
          房间 "{room.name}" 需要密码才能删除
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={cn('block text-sm font-medium mb-2', theme === 'dark' ? 'text-slate-300' : 'text-slate-700')}>
              房间密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="输入房间密码"
              className={cn(
                'w-full px-4 py-3 rounded-xl border outline-none transition-colors',
                theme === 'dark'
                  ? 'bg-slate-900 border-slate-700 focus:border-red-500'
                  : 'bg-gray-50 border-slate-200 focus:border-red-500'
              )}
              autoFocus
            />
          </div>

          {error && <div className="text-red-500 text-sm">{error}</div>}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className={cn(
                'flex-1 py-3 rounded-xl font-medium transition-colors',
                theme === 'dark' ? 'bg-slate-700 hover:bg-slate-600' : 'bg-slate-100 hover:bg-slate-200'
              )}
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-3 bg-red-500 text-white rounded-xl font-medium hover:bg-red-600 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              删除
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
