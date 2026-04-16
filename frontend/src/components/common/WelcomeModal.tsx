import { useEffect, useState } from 'react'
import { ArrowRight, Users } from 'lucide-react'

import { useI18n } from '../../i18n'
import { cn } from '../../lib/utils'

interface WelcomeModalProps {
  isOpen: boolean
  onJoin: (nickname: string) => void
}

export function WelcomeModal({ isOpen, onJoin }: WelcomeModalProps) {
  const { t } = useI18n()
  const [nickname, setNickname] = useState('')
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    const savedNickname = localStorage.getItem('sync_canvas_nickname')
    if (savedNickname) {
      setNickname(savedNickname)
    }
  }, [])

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    if (nickname.trim()) {
      localStorage.setItem('sync_canvas_nickname', nickname.trim())
      onJoin(nickname.trim())
    }
  }

  if (!isOpen) return null

  return (
    <div
      className={cn(
        'fixed inset-0 z-50 flex items-center justify-center p-4 transition-opacity duration-300',
        mounted ? 'opacity-100' : 'opacity-0',
      )}
    >
      <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" />

      <div className="relative w-full max-w-md overflow-hidden rounded-2xl border border-white/20 bg-white/90 shadow-2xl transition-all dark:border-zinc-700/60 dark:bg-zinc-900/95">
        <div className="p-8">
          <div className="mb-6 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/30 dark:shadow-indigo-950/40">
              <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                />
              </svg>
            </div>
          </div>

          <h2 className="mb-2 text-center text-2xl font-bold text-slate-800 dark:text-zinc-100">
            {t('welcomeModal.title')}
          </h2>
          <p className="mb-8 text-center text-slate-500 dark:text-zinc-400">
            {t('welcomeModal.subtitle')}
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="nickname" className="block text-sm font-medium text-slate-700 dark:text-zinc-200">
                {t('welcomeModal.nicknameLabel')}
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400 dark:text-zinc-500">
                  <Users size={18} />
                </div>
                <input
                  type="text"
                  id="nickname"
                  value={nickname}
                  onChange={(event) => setNickname(event.target.value)}
                  className="block w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-3 text-slate-900 transition-all focus:border-transparent focus:bg-white focus:ring-2 focus:ring-indigo-500 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:placeholder:text-zinc-500 dark:focus:bg-zinc-900"
                  placeholder={t('welcomeModal.nicknamePlaceholder')}
                  autoFocus
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={!nickname.trim()}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 font-medium text-white shadow-lg shadow-indigo-500/30 transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-indigo-500 dark:shadow-indigo-950/40 dark:hover:bg-indigo-400"
            >
              <span>{t('welcomeModal.enter')}</span>
              <ArrowRight size={18} />
            </button>
          </form>
        </div>

        <div className="border-t border-slate-100 bg-slate-50 px-8 py-4 text-center dark:border-zinc-800 dark:bg-zinc-950/70">
          <p className="text-xs text-slate-400 dark:text-zinc-500">
            {t('welcomeModal.footer')}
          </p>
        </div>
      </div>
    </div>
  )
}
