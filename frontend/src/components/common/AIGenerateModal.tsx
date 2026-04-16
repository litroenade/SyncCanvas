import { useState } from 'react'
import { Loader2, Sparkles, X } from 'lucide-react'

import { useI18n } from '../../i18n'
import { cn } from '../../lib/utils'
import { aiApi } from '../../services/api/ai'
import { yjsManager } from '../../lib/yjs'

interface AIGenerateModalProps {
  isOpen: boolean
  onClose: () => void
}

export function AIGenerateModal({ isOpen, onClose }: AIGenerateModalProps) {
  const { t } = useI18n()
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!prompt.trim()) return

    setLoading(true)
    setError(null)

    try {
      const roomId = yjsManager.roomId
      if (!roomId) {
        setError(t('aiGenerateModal.roomUnavailable'))
        return
      }
      await aiApi.generateShapes(prompt, roomId)
      onClose()
      setPrompt('')
    } catch (err) {
      console.error(err)
      setError(t('aiGenerateModal.generateFailed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="m-4 w-full max-w-md animate-in zoom-in rounded-2xl border border-white/20 bg-white/90 p-6 shadow-2xl backdrop-blur-xl fade-in duration-200 dark:border-zinc-700/60 dark:bg-zinc-900/95">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-300">
            <Sparkles size={24} />
            <h2 className="text-xl font-bold text-slate-900 dark:text-zinc-100">
              {t('aiGenerateModal.title')}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:text-zinc-500 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-zinc-200">
              {t('aiGenerateModal.promptLabel')}
            </label>
            <textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder={t('aiGenerateModal.promptPlaceholder')}
              className="h-32 w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-700 transition-all focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:placeholder:text-zinc-500 dark:focus:bg-zinc-900"
              disabled={loading}
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-rose-50 p-3 text-sm text-rose-600 dark:bg-rose-950/40 dark:text-rose-200">
              <X size={14} />
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-4 py-2 font-medium text-slate-600 transition-colors hover:bg-slate-100 dark:text-zinc-300 dark:hover:bg-zinc-800"
              disabled={loading}
            >
              {t('aiGenerateModal.cancel')}
            </button>
            <button
              type="submit"
              disabled={loading || !prompt.trim()}
              className={cn(
                'flex items-center gap-2 rounded-lg bg-indigo-600 px-6 py-2 font-medium text-white shadow-lg shadow-indigo-500/30 transition-all dark:bg-indigo-500 dark:shadow-indigo-950/40',
                loading
                  ? 'cursor-not-allowed opacity-70'
                  : 'hover:scale-105 hover:bg-indigo-700 active:scale-95 dark:hover:bg-indigo-400',
                !prompt.trim()
                  && 'cursor-not-allowed opacity-50 hover:scale-100 hover:bg-indigo-600 dark:hover:bg-indigo-500',
              )}
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  {t('aiGenerateModal.generating')}
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  {t('aiGenerateModal.submit')}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
