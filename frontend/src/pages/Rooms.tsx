import React, { useEffect, useState } from 'react'
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
  Shapes,
  UserCheck,
  Radio,
} from 'lucide-react'

import { useI18n } from '../i18n'
import { cn } from '../lib/utils'
import { useModal } from '../components/common/Modal'
import { RoomListSkeleton } from '../components/common/Skeleton'
import { getRequestErrorMessage } from '../services/api/axios'
import { roomsApi, Room, CreateRoomRequest } from '../services/api/rooms'
import { useThemeStore } from '../stores/useThemeStore'

export const Rooms: React.FC = () => {
  const { t } = useI18n()
  const navigate = useNavigate()
  const { theme, toggleTheme } = useThemeStore()
  const [rooms, setRooms] = useState<Room[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showJoinModal, setShowJoinModal] = useState<Room | null>(null)
  const [showDeleteModal, setShowDeleteModal] = useState<Room | null>(null)
  const { showAlert, showConfirm, showToast, ModalRenderer } = useModal()

  const isLoggedIn = !!localStorage.getItem('token')
  const isGuest = localStorage.getItem('isGuest') === 'true'
  const username = localStorage.getItem('username') || t('rooms.guestName')

  useEffect(() => {
    loadRooms()
  }, [])

  const loadRooms = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await roomsApi.list()
      setRooms(response.rooms)
    } catch (err) {
      setError(getRequestErrorMessage(err, t('rooms.error.loadFailed')))
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
    localStorage.setItem('currentRoomId', roomId)
    navigate(`/room/${roomId}`)
  }

  const handleDeleteRoom = async (room: Room, password?: string) => {
    if (room.has_password && !password) {
      setShowDeleteModal(room)
      return
    }

    showConfirm(
      t('rooms.deleteConfirm'),
      async () => {
        try {
          await roomsApi.delete(room.id, password)
          showToast(t('rooms.deleted'), 'success')
          loadRooms()
        } catch (err) {
          showAlert(getRequestErrorMessage(err, t('rooms.error.deleteFailed')), {
            type: 'error',
            title: t('rooms.deleteTitle'),
          })
        }
      },
      { title: t('rooms.deleteTitle'), type: 'danger' },
    )
  }

  const handleCopyInvite = async (roomId: string) => {
    try {
      const { invite_url } = await roomsApi.getInviteLink(roomId)
      const fullUrl = `${window.location.origin}${invite_url}`
      await navigator.clipboard.writeText(fullUrl)
      showToast(t('rooms.inviteCopied'), 'success')
    } catch {
      showAlert(t('rooms.error.inviteCopyFailed'), { type: 'error' })
    }
  }

  return (
    <div
      className={cn(
        'min-h-screen transition-colors',
        theme === 'dark' ? 'bg-slate-900 text-slate-100' : 'bg-gray-50 text-slate-800',
      )}
    >
      <header
        className={cn(
          'sticky top-0 z-10 border-b backdrop-blur-md',
          theme === 'dark' ? 'border-slate-700 bg-slate-900/80' : 'border-slate-200 bg-white/80',
        )}
      >
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 text-lg font-bold text-white">
              S
            </div>
            <h1 className="text-xl font-bold">SyncCanvas</h1>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={toggleTheme}
              className={cn(
                'rounded-lg p-2 transition-colors',
                theme === 'dark' ? 'hover:bg-slate-800' : 'hover:bg-slate-100',
              )}
            >
              {theme === 'dark' ? <Moon size={20} /> : <Sun size={20} />}
            </button>

            {(isLoggedIn || isGuest) && (
              <>
                <span className={cn('text-sm', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
                  {isGuest ? t('rooms.guestName') : username}
                </span>
                <button
                  onClick={isGuest ? handleGuestLogin : handleLogout}
                  className={cn(
                    'rounded-lg p-2 transition-colors',
                    theme === 'dark'
                      ? 'text-slate-400 hover:bg-slate-800'
                      : 'text-slate-500 hover:bg-slate-100',
                  )}
                  title={isGuest ? t('rooms.login') : t('rooms.logout')}
                >
                  <LogOut size={20} />
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h2 className="mb-1 text-2xl font-bold">{t('rooms.pageTitle')}</h2>
            <p className={cn('text-sm', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
              {t('rooms.pageDescription')}
            </p>
          </div>

          {isLoggedIn && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-blue-500 to-indigo-600 px-4 py-2 text-white shadow-lg shadow-blue-500/25 transition-all hover:from-blue-600 hover:to-indigo-700"
            >
              <Plus size={20} />
              {t('rooms.createRoom')}
            </button>
          )}
        </div>

        {loading && <RoomListSkeleton count={6} isDark={theme === 'dark'} />}

        {error && (
          <div className="mb-6 rounded-xl bg-red-500/10 p-4 text-center text-red-500">{error}</div>
        )}

        {!loading && !error && rooms.length === 0 && (
          <div
            className={cn(
              'rounded-2xl border-2 border-dashed py-20 text-center',
              theme === 'dark' ? 'border-slate-700' : 'border-slate-200',
            )}
          >
            <Users className="mx-auto mb-4 h-16 w-16 text-slate-400" />
            <h3 className="mb-2 text-lg font-medium">{t('rooms.emptyTitle')}</h3>
            <p className={cn('mb-6 text-sm', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
              {t('rooms.emptyDescription')}
            </p>
            {isLoggedIn && (
              <button
                onClick={() => setShowCreateModal(true)}
                className="rounded-lg bg-blue-500 px-6 py-2 text-white transition-colors hover:bg-blue-600"
              >
                {t('rooms.createFirstRoom')}
              </button>
            )}
          </div>
        )}

        {!loading && !error && rooms.length > 0 && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
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
                isOwner={room.is_owner}
              />
            ))}
          </div>
        )}
      </main>

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

      <ModalRenderer />
    </div>
  )
}

interface RoomCardProps {
  room: Room
  theme: 'light' | 'dark'
  onEnter: () => void
  onDelete: () => void
  onCopyInvite: () => void
  isOwner: boolean
}

const RoomCard: React.FC<RoomCardProps> = ({ room, theme, onEnter, onDelete, onCopyInvite, isOwner }) => {
  const { t, locale } = useI18n()

  const formatDate = (timestamp: number) => {
    return new Intl.DateTimeFormat(locale, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(timestamp))
  }

  return (
    <div
      className={cn(
        'group relative cursor-pointer rounded-2xl border p-5 transition-all hover:shadow-lg',
        theme === 'dark'
          ? 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
          : 'border-slate-200 bg-white hover:border-slate-300',
      )}
      onClick={onEnter}
    >
      <div className="mb-4 flex items-start justify-between">
        <div
          className={cn(
            'flex h-12 w-12 items-center justify-center rounded-xl text-lg font-bold',
            room.is_public ? 'bg-green-500/10 text-green-500' : 'bg-amber-500/10 text-amber-500',
          )}
        >
          {room.is_public ? <Globe size={24} /> : <Lock size={24} />}
        </div>

        <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <button
            onClick={(event) => {
              event.stopPropagation()
              onCopyInvite()
            }}
            className={cn(
              'rounded-lg p-2 transition-colors',
              theme === 'dark' ? 'hover:bg-slate-700' : 'hover:bg-slate-100',
            )}
            title={t('rooms.card.copyInvite')}
          >
            <LinkIcon size={16} />
          </button>
          {isOwner && (
            <button
              onClick={(event) => {
                event.stopPropagation()
                onDelete()
              }}
              className="rounded-lg p-2 text-red-500 transition-colors hover:bg-red-500/10"
              title={t('rooms.card.delete')}
            >
              <Trash2 size={16} />
            </button>
          )}
        </div>
      </div>

      <h3 className="mb-2 truncate text-lg font-semibold">{room.name}</h3>

      <div className={cn('flex flex-wrap items-center gap-3 text-sm', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
        {room.online_count > 0 && (
          <span className="flex items-center gap-1 rounded-full bg-green-500/10 px-2 py-0.5 text-xs font-medium text-green-500">
            <Radio size={12} className="animate-pulse" />
            {t('rooms.card.onlineCount', { count: room.online_count })}
          </span>
        )}
        <span className="flex items-center gap-1">
          <Users size={14} />
          {room.member_count}/{room.max_users}
        </span>
        {room.has_password && (
          <span className="flex items-center gap-1">
            <Lock size={14} />
          </span>
        )}
      </div>

      <div className={cn('mt-2 flex items-center gap-3 text-xs', theme === 'dark' ? 'text-slate-500' : 'text-slate-400')}>
        {room.elements_count > 0 && (
          <span className="flex items-center gap-1" title={t('rooms.card.elementsTitle')}>
            <Shapes size={12} />
            {room.elements_count}
          </span>
        )}
        {room.total_contributors > 0 && (
          <span className="flex items-center gap-1" title={t('rooms.card.contributorsTitle')}>
            <UserCheck size={12} />
            {room.total_contributors}
          </span>
        )}
      </div>

      <div className={cn('mt-2 text-xs', theme === 'dark' ? 'text-slate-500' : 'text-slate-400')}>
        {t('rooms.card.createdAt', { date: formatDate(room.created_at) })}
      </div>

      <div className="absolute bottom-4 right-4 opacity-0 transition-opacity group-hover:opacity-100">
        <ArrowRight size={20} className="text-blue-500" />
      </div>
    </div>
  )
}

interface CreateRoomModalProps {
  theme: 'light' | 'dark'
  onClose: () => void
  onCreated: (room: Room) => void
}

const CreateRoomModal: React.FC<CreateRoomModalProps> = ({ theme, onClose, onCreated }) => {
  const { t } = useI18n()
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [isPublic, setIsPublic] = useState(true)
  const [maxUsers, setMaxUsers] = useState(10)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
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
    } catch (err) {
      setError(getRequestErrorMessage(err, t('rooms.createModal.error')))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div
        className={cn(
          'w-full max-w-md rounded-2xl p-6 shadow-xl',
          theme === 'dark' ? 'bg-slate-800' : 'bg-white',
        )}
      >
        <h2 className="mb-6 text-xl font-bold">{t('rooms.createModal.title')}</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={cn('mb-2 block text-sm font-medium', theme === 'dark' ? 'text-slate-300' : 'text-slate-700')}>
              {t('rooms.createModal.nameLabel')}
            </label>
            <input
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder={t('rooms.createModal.namePlaceholder')}
              className={cn(
                'w-full rounded-xl border px-4 py-3 outline-none transition-colors',
                theme === 'dark'
                  ? 'border-slate-700 bg-slate-900 focus:border-blue-500'
                  : 'border-slate-200 bg-gray-50 focus:border-blue-500',
              )}
              required
            />
          </div>

          <div>
            <label className={cn('mb-2 block text-sm font-medium', theme === 'dark' ? 'text-slate-300' : 'text-slate-700')}>
              {t('rooms.createModal.passwordLabel')}
            </label>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={t('rooms.createModal.passwordPlaceholder')}
              className={cn(
                'w-full rounded-xl border px-4 py-3 outline-none transition-colors',
                theme === 'dark'
                  ? 'border-slate-700 bg-slate-900 focus:border-blue-500'
                  : 'border-slate-200 bg-gray-50 focus:border-blue-500',
              )}
            />
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="isPublic"
              checked={isPublic}
              onChange={(event) => setIsPublic(event.target.checked)}
              className="h-5 w-5 rounded"
            />
            <label htmlFor="isPublic" className="text-sm">
              {t('rooms.createModal.publicLabel')}
            </label>
          </div>

          <div>
            <label className={cn('mb-2 block text-sm font-medium', theme === 'dark' ? 'text-slate-300' : 'text-slate-700')}>
              {t('rooms.createModal.maxUsersLabel', { count: maxUsers })}
            </label>
            <input
              type="range"
              min="2"
              max="50"
              value={maxUsers}
              onChange={(event) => setMaxUsers(parseInt(event.target.value, 10))}
              className="w-full"
            />
          </div>

          {error && <div className="text-sm text-red-500">{error}</div>}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className={cn(
                'flex-1 rounded-xl py-3 font-medium transition-colors',
                theme === 'dark' ? 'bg-slate-700 hover:bg-slate-600' : 'bg-slate-100 hover:bg-slate-200',
              )}
            >
              {t('modal.cancel')}
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-blue-500 py-3 font-medium text-white transition-colors hover:bg-blue-600 disabled:opacity-50"
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              {t('rooms.createModal.submit')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

interface JoinRoomModalProps {
  room: Room
  theme: 'light' | 'dark'
  onClose: () => void
  onJoined: () => void
}

const JoinRoomModal: React.FC<JoinRoomModalProps> = ({ room, theme, onClose, onJoined }) => {
  const { t } = useI18n()
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError(null)

    try {
      await roomsApi.join(room.id, password)
      onJoined()
    } catch (err) {
      setError(getRequestErrorMessage(err, t('rooms.joinModal.error')))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div
        className={cn(
          'w-full max-w-md rounded-2xl p-6 shadow-xl',
          theme === 'dark' ? 'bg-slate-800' : 'bg-white',
        )}
      >
        <h2 className="mb-2 text-xl font-bold">{t('rooms.joinModal.title')}</h2>
        <p className={cn('mb-6 text-sm', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
          {t('rooms.joinModal.description', { name: room.name })}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={cn('mb-2 block text-sm font-medium', theme === 'dark' ? 'text-slate-300' : 'text-slate-700')}>
              {t('rooms.joinModal.passwordLabel')}
            </label>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={t('rooms.joinModal.passwordPlaceholder')}
              className={cn(
                'w-full rounded-xl border px-4 py-3 outline-none transition-colors',
                theme === 'dark'
                  ? 'border-slate-700 bg-slate-900 focus:border-blue-500'
                  : 'border-slate-200 bg-gray-50 focus:border-blue-500',
              )}
              autoFocus
            />
          </div>

          {error && <div className="text-sm text-red-500">{error}</div>}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className={cn(
                'flex-1 rounded-xl py-3 font-medium transition-colors',
                theme === 'dark' ? 'bg-slate-700 hover:bg-slate-600' : 'bg-slate-100 hover:bg-slate-200',
              )}
            >
              {t('modal.cancel')}
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-blue-500 py-3 font-medium text-white transition-colors hover:bg-blue-600 disabled:opacity-50"
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              {t('rooms.joinModal.submit')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

interface DeleteRoomModalProps {
  room: Room
  theme: 'light' | 'dark'
  onClose: () => void
  onDeleted: () => void
}

const DeleteRoomModal: React.FC<DeleteRoomModalProps> = ({ room, theme, onClose, onDeleted }) => {
  const { t } = useI18n()
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError(null)

    try {
      await roomsApi.delete(room.id, password)
      onDeleted()
    } catch (err) {
      setError(getRequestErrorMessage(err, t('rooms.deleteModal.error')))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div
        className={cn(
          'w-full max-w-md rounded-2xl p-6 shadow-xl',
          theme === 'dark' ? 'bg-slate-800' : 'bg-white',
        )}
      >
        <h2 className="mb-2 text-xl font-bold text-red-500">{t('rooms.deleteModal.title')}</h2>
        <p className={cn('mb-6 text-sm', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
          {t('rooms.deleteModal.description', { name: room.name })}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={cn('mb-2 block text-sm font-medium', theme === 'dark' ? 'text-slate-300' : 'text-slate-700')}>
              {t('rooms.deleteModal.passwordLabel')}
            </label>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={t('rooms.deleteModal.passwordPlaceholder')}
              className={cn(
                'w-full rounded-xl border px-4 py-3 outline-none transition-colors',
                theme === 'dark'
                  ? 'border-slate-700 bg-slate-900 focus:border-red-500'
                  : 'border-slate-200 bg-gray-50 focus:border-red-500',
              )}
              autoFocus
            />
          </div>

          {error && <div className="text-sm text-red-500">{error}</div>}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className={cn(
                'flex-1 rounded-xl py-3 font-medium transition-colors',
                theme === 'dark' ? 'bg-slate-700 hover:bg-slate-600' : 'bg-slate-100 hover:bg-slate-200',
              )}
            >
              {t('modal.cancel')}
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-red-500 py-3 font-medium text-white transition-colors hover:bg-red-600 disabled:opacity-50"
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              {t('rooms.deleteModal.submit')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
